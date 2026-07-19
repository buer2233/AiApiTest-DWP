from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
from typing import Any

from django.utils import timezone as django_timezone


class JenkinsServiceError(RuntimeError):
    """Jenkins 调用或响应契约失败时抛出的基础异常。"""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class JenkinsBuildMatchError(JenkinsServiceError):
    """Jenkins 构建恢复出现多个精确匹配，必须由调用方人工诊断。"""

    def __init__(self, *, match_kind: str, match_value: str, match_count: int):
        self.match_kind = match_kind
        self.match_value = match_value
        self.match_count = match_count
        super().__init__(
            f"Multiple Jenkins builds matched {match_kind}={match_value}, matches={match_count}"
        )


@dataclass(frozen=True)
class JenkinsConfig:
    api_base_url: str
    public_base_url: str
    username: str = ""
    api_token: str = ""
    timeout_seconds: int = 15


def _read_config() -> JenkinsConfig:
    public_base_url = os.environ.get("JENKINS_PUBLIC_BASE_URL", "").rstrip("/")
    api_base_url = os.environ.get("JENKINS_API_BASE_URL", public_base_url).rstrip("/")
    if not public_base_url:
        public_base_url = api_base_url
    timeout = int(os.environ.get("JENKINS_REQUEST_TIMEOUT_SECONDS", "15") or "15")
    return JenkinsConfig(
        api_base_url=api_base_url,
        public_base_url=public_base_url,
        username=os.environ.get("JENKINS_USERNAME", ""),
        api_token=os.environ.get("JENKINS_API_TOKEN", ""),
        timeout_seconds=timeout,
    )


def _job_path(job_full_name: str) -> str:
    return "/".join(f"job/{urllib.parse.quote(part)}" for part in job_full_name.split("/") if part)


def _to_public_url(config: JenkinsConfig, url: str) -> str:
    if not url or not config.public_base_url or not config.api_base_url:
        return url
    if url.startswith(config.api_base_url):
        return f"{config.public_base_url}{url[len(config.api_base_url):]}"
    return url


def _request(
    config: JenkinsConfig,
    method: str,
    url: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> urllib.response.addinfourl:
    request_headers = {}
    if headers:
        request_headers.update(headers)
    if config.username and config.api_token:
        raw = f"{config.username}:{config.api_token}".encode("utf-8")
        request_headers["Authorization"] = f"Basic {base64.b64encode(raw).decode('ascii')}"
    request = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        return urllib.request.urlopen(request, timeout=config.timeout_seconds)
    except urllib.error.HTTPError as exc:
        raise JenkinsServiceError(str(exc), status_code=exc.code) from exc
    except Exception as exc:  # pragma: no cover - 真实 Jenkins 网络异常由集成环境覆盖
        raise JenkinsServiceError(str(exc)) from exc


def _read_json_response(response, *, expect_object: bool = False) -> Any:
    """统一封装 Jenkins 的 JSON 解码和顶层对象类型错误。"""
    try:
        payload = json.loads(response.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JenkinsServiceError("Jenkins returned invalid JSON") from exc
    if expect_object and not isinstance(payload, dict):
        raise JenkinsServiceError("Jenkins returned an invalid JSON object")
    return payload


def _parse_build_number(value: Any) -> int:
    if isinstance(value, bool):
        raise JenkinsServiceError("Jenkins build number is invalid")
    if isinstance(value, int):
        build_number = value
    elif isinstance(value, str) and value.strip().isdigit():
        build_number = int(value.strip())
    else:
        raise JenkinsServiceError("Jenkins build number is invalid")
    if build_number < 1:
        raise JenkinsServiceError("Jenkins build number is invalid")
    return build_number


def _read_builds(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_builds = payload.get("builds") or []
    if not isinstance(raw_builds, list) or any(not isinstance(build, dict) for build in raw_builds):
        raise JenkinsServiceError("Jenkins returned an invalid build list")
    return raw_builds


def _jenkins_crumb_headers(config: JenkinsConfig) -> dict[str, str]:
    if not config.username or not config.api_token:
        return {}
    url = f"{config.api_base_url}/crumbIssuer/api/json"
    try:
        with _request(config, "GET", url) as response:
            payload = _read_json_response(response, expect_object=True)
    except JenkinsServiceError:
        return {}
    field = payload.get("crumbRequestField") or "Jenkins-Crumb"
    crumb = payload.get("crumb")
    if not crumb:
        return {}
    # urllib 的 Request.headers 大小写不透明；保留 Jenkins 返回字段并补一个测试/调试友好的等价键。
    headers = {str(field): str(crumb)}
    if str(field).lower() == "jenkins-crumb":
        headers["Jenkins-crumb"] = str(crumb)
    return headers


def _post(config: JenkinsConfig, url: str, data: bytes | None = None) -> urllib.response.addinfourl:
    return _request(config, "POST", url, data=data, headers=_jenkins_crumb_headers(config))


def trigger_jenkins_build(*, job_full_name: str, parameters: dict[str, Any]) -> dict[str, str]:
    """触发 Jenkins 参数化构建，返回 queue 信息。"""
    config = _read_config()
    if not config.api_base_url:
        raise JenkinsServiceError("JENKINS_API_BASE_URL is not configured")
    encoded = urllib.parse.urlencode({key: str(value) for key, value in parameters.items()}).encode("utf-8")
    url = f"{config.api_base_url}/{_job_path(job_full_name)}/buildWithParameters"
    response = _post(config, url, encoded)
    queue_url = _to_public_url(config, response.headers.get("Location", ""))
    queue_id = queue_url.rstrip("/").split("/")[-1] if queue_url else ""
    return {"queue_id": queue_id, "queue_url": queue_url}


def cancel_jenkins_task(task) -> None:
    """取消 Jenkins queue/build；当前实现覆盖 build stop，queue 取消由后续集成增强。"""
    config = _read_config()
    if not config.api_base_url:
        raise JenkinsServiceError("JENKINS_API_BASE_URL is not configured")
    if task.build_number:
        url = f"{config.api_base_url}/{_job_path(task.job_full_name)}/{task.build_number}/stop"
    elif task.queue_id:
        url = f"{config.api_base_url}/queue/cancelItem?id={urllib.parse.quote(str(task.queue_id))}"
    else:
        raise JenkinsServiceError("Jenkins task has no build_number or queue_id")
    _post(config, url)


def _build_tag_run_id(job_full_name: str, build_number: int) -> str:
    # Jenkins 默认 BUILD_TAG 与 JOB_NAME/BUILD_NUMBER 绑定，目录名需要避开 folder 分隔符。
    return f"jenkins-{job_full_name.replace('/', '-')}-{build_number}"


def _timestamp_matches_date(timestamp_ms: int | None, date: str | None) -> bool:
    if not date or timestamp_ms is None:
        return True
    try:
        timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=datetime_timezone.utc)
        return django_timezone.localtime(timestamp).date().isoformat() == date
    except (OSError, TypeError, ValueError):
        return False


def _build_parameter(build: dict[str, Any], name: str) -> str:
    actions = build.get("actions") or []
    if not isinstance(actions, list):
        raise JenkinsServiceError("Jenkins returned an invalid JSON object")
    for action in actions:
        if not isinstance(action, dict):
            raise JenkinsServiceError("Jenkins returned an invalid JSON object")
        parameters = action.get("parameters") or []
        if not isinstance(parameters, list):
            raise JenkinsServiceError("Jenkins returned an invalid JSON object")
        for parameter in parameters:
            if not isinstance(parameter, dict):
                raise JenkinsServiceError("Jenkins returned an invalid JSON object")
            if parameter.get("name") == name:
                return str(parameter.get("value") or "")
    return ""


def _recover_build_from_expired_queue(config: JenkinsConfig, task) -> dict[str, Any] | None:
    """queue item 被 Jenkins 清理后，按 queueId 或 RUN_ID 精确恢复对应 build。"""
    url = (
        f"{config.api_base_url}/{_job_path(task.job_full_name)}/api/json"
        "?tree=builds[number,queueId,url,result,building,timestamp,duration,actions[parameters[name,value]]]{0,50}"
    )
    with _request(config, "GET", url) as response:
        payload = _read_json_response(response, expect_object=True)
    builds = _read_builds(payload)
    queue_id = str(task.queue_id or "")
    queue_matches = [build for build in builds if queue_id and str(build.get("queueId") or "") == queue_id]
    if len(queue_matches) > 1:
        raise JenkinsBuildMatchError(match_kind="queue_id", match_value=queue_id, match_count=len(queue_matches))
    if queue_matches:
        return queue_matches[0]

    run_key = str(task.run.run_key if task.run else "")
    run_matches = [build for build in builds if run_key and _build_parameter(build, "RUN_ID") == run_key]
    if len(run_matches) > 1:
        raise JenkinsBuildMatchError(match_kind="run_id", match_value=run_key, match_count=len(run_matches))
    return run_matches[0] if run_matches else None


def _build_times(build_payload: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    raw_timestamp = build_payload.get("timestamp")
    try:
        started_at = datetime.fromtimestamp(int(raw_timestamp) / 1000, tz=datetime_timezone.utc)
    except (OSError, TypeError, ValueError, OverflowError):
        return None, None
    if build_payload.get("building"):
        return started_at, None
    raw_duration = build_payload.get("duration")
    try:
        duration_ms = int(raw_duration)
    except (TypeError, ValueError, OverflowError):
        return started_at, None
    if duration_ms < 0:
        return started_at, None
    try:
        return started_at, started_at + timedelta(milliseconds=duration_ms)
    except OverflowError:
        return started_at, None


def discover_jenkins_builds(*, job_full_names: list[str], date: str | None = None) -> list[dict[str, Any]]:
    """按 Jenkins Job 发现构建列表。

    Daily cron 未由平台触发，默认 RUN_ID 来自 Jenkins BUILD_TAG；这里按同一规则生成 run_id，
    让后端同步 artifact 时能找到 runtime/ci-runs/<run_id>。
    """
    config = _read_config()
    if not config.api_base_url:
        raise JenkinsServiceError("JENKINS_API_BASE_URL is not configured")

    builds: list[dict[str, Any]] = []
    for job_full_name in job_full_names:
        url = (
            f"{config.api_base_url}/{_job_path(job_full_name)}/api/json"
            "?tree=builds[number,url,result,building,timestamp,actions[parameters[name,value]]]{0,50}"
        )
        with _request(config, "GET", url) as response:
            payload = _read_json_response(response, expect_object=True)
        for build in _read_builds(payload):
            build_number = build.get("number")
            if build_number is None or not _timestamp_matches_date(build.get("timestamp"), date):
                continue
            build_number = _parse_build_number(build_number)
            builds.append(
                {
                    "job_full_name": job_full_name,
                    "build_number": build_number,
                    "jenkins_build_url": _to_public_url(config, build.get("url", "")),
                    "jenkins_result": build.get("result") or "",
                    "building": bool(build.get("building")),
                    "run_id": _build_tag_run_id(job_full_name, build_number),
                    # 手工 Daily 的 URL 覆盖由 Jenkins 参数原样返回；空值仍不能让后端猜测私有默认环境。
                    "target_base_url": _build_parameter(build, "TARGET_BASE_URL"),
                }
            )
    return builds


def fetch_jenkins_task_result(task) -> dict[str, Any]:
    """读取 Jenkins build 与 artifact 摘要。

    单元测试会 mock 本函数；真实环境下读取 API 与 artifact URL。
    """
    config = _read_config()
    if not config.api_base_url:
        raise JenkinsServiceError("JENKINS_API_BASE_URL is not configured")
    build_number = task.build_number
    recovered_build_url = ""
    if not build_number:
        queue_url = f"{config.api_base_url}/queue/item/{urllib.parse.quote(str(task.queue_id))}/api/json"
        try:
            with _request(config, "GET", queue_url) as response:
                queue_payload = _read_json_response(response, expect_object=True)
        except JenkinsServiceError as exc:
            if exc.status_code != 404:
                raise
            recovered = _recover_build_from_expired_queue(config, task)
            if recovered is None:
                return {"queue_pending": True, "recovery_pending": True}
            build_number = _parse_build_number(recovered.get("number"))
            recovered_build_url = recovered.get("url", "")
        else:
            if queue_payload.get("cancelled") or queue_payload.get("canceled"):
                return {"canceled": True}
            executable = queue_payload.get("executable") or {}
            if not isinstance(executable, dict):
                raise JenkinsServiceError("Jenkins returned an invalid JSON object")
            if not executable.get("number"):
                return {"queue_pending": True}
            build_number = _parse_build_number(executable.get("number"))
            recovered_build_url = executable.get("url", "")

    build_url = f"{config.api_base_url}/{_job_path(task.job_full_name)}/{build_number}"
    public_build_url = _to_public_url(config, build_url)
    with _request(config, "GET", f"{build_url}/api/json") as response:
        build_payload = _read_json_response(response, expect_object=True)
    started_at, finished_at = _build_times(build_payload)
    public_build_url = _to_public_url(config, recovered_build_url) or public_build_url

    if build_payload.get("building"):
        return {
            "build_number": build_number,
            "jenkins_result": None,
            "jenkins_build_url": public_build_url,
            "building": True,
            "started_at": started_at,
            "finished_at": None,
        }

    artifact_base = f"{build_url}/artifact/api-test/runtime/ci-runs/{task.run.run_key if task.run else ''}".rstrip("/")
    public_artifact_base = f"{public_build_url}/artifact/api-test/runtime/ci-runs/{task.run.run_key if task.run else ''}".rstrip("/")
    summary_url = f"{artifact_base}/summary.json"
    failed_url = f"{artifact_base}/failed_nodeids.json"
    try:
        with _request(config, "GET", summary_url) as response:
            summary = _read_json_response(response)
        with _request(config, "GET", failed_url) as response:
            failed_nodeids = _read_json_response(response)
    except JenkinsServiceError as exc:
        return {
            "build_number": build_number,
            "jenkins_build_url": public_build_url,
            "jenkins_result": build_payload.get("result"),
            "summary": None,
            "failed_nodeids": [],
            "error_summary": f"Jenkins artifact missing or unreadable: {exc}",
            "started_at": started_at,
            "finished_at": finished_at,
        }

    return {
        "build_number": build_number,
        "jenkins_build_url": public_build_url,
        "jenkins_result": build_payload.get("result"),
        "summary": summary,
        "failed_nodeids": failed_nodeids,
        "artifact_base_url": public_artifact_base,
        "summary_artifact_url": f"{public_artifact_base}/summary.json",
        "failed_nodeids_artifact_url": f"{public_artifact_base}/failed_nodeids.json",
        "allure_report_url": f"{public_build_url.rstrip('/')}/allure/",
        "started_at": started_at,
        "finished_at": finished_at,
    }
