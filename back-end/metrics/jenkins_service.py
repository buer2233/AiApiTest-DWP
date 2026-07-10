from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class JenkinsServiceError(RuntimeError):
    """Jenkins 调用失败时抛出，视图层统一转换为 503。"""


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
    except Exception as exc:  # pragma: no cover - 真实 Jenkins 网络异常由集成环境覆盖
        raise JenkinsServiceError(str(exc)) from exc


def _jenkins_crumb_headers(config: JenkinsConfig) -> dict[str, str]:
    if not config.username or not config.api_token:
        return {}
    url = f"{config.api_base_url}/crumbIssuer/api/json"
    try:
        with _request(config, "GET", url) as response:
            payload = json.loads(response.read().decode("utf-8"))
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
        return datetime.fromtimestamp(int(timestamp_ms) / 1000).date().isoformat() == date
    except (OSError, TypeError, ValueError):
        return False


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
            "?tree=builds[number,url,result,building,timestamp]{0,50}"
        )
        with _request(config, "GET", url) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for build in payload.get("builds") or []:
            build_number = build.get("number")
            if build_number is None or not _timestamp_matches_date(build.get("timestamp"), date):
                continue
            builds.append(
                {
                    "job_full_name": job_full_name,
                    "build_number": build_number,
                    "jenkins_build_url": _to_public_url(config, build.get("url", "")),
                    "jenkins_result": build.get("result") or "",
                    "building": bool(build.get("building")),
                    "run_id": _build_tag_run_id(job_full_name, int(build_number)),
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
    if not task.build_number:
        queue_url = f"{config.api_base_url}/queue/item/{urllib.parse.quote(str(task.queue_id))}/api/json"
        with _request(config, "GET", queue_url) as response:
            queue_payload = json.loads(response.read().decode("utf-8"))
        if queue_payload.get("cancelled") or queue_payload.get("canceled"):
            return {"canceled": True}
        executable = queue_payload.get("executable") or {}
        if not executable.get("number"):
            return {"queue_pending": True}
        return {
            "build_number": executable.get("number"),
            "jenkins_build_url": _to_public_url(config, executable.get("url", "")),
        }

    build_url = f"{config.api_base_url}/{_job_path(task.job_full_name)}/{task.build_number}"
    public_build_url = _to_public_url(config, build_url)
    with _request(config, "GET", f"{build_url}/api/json") as response:
        build_payload = json.loads(response.read().decode("utf-8"))

    if build_payload.get("building"):
        return {
            "build_number": task.build_number,
            "jenkins_result": None,
            "jenkins_build_url": public_build_url,
            "building": True,
            "started_at": None,
            "finished_at": None,
        }

    artifact_base = f"{build_url}/artifact/api-test/runtime/ci-runs/{task.run.run_key if task.run else ''}".rstrip("/")
    public_artifact_base = f"{public_build_url}/artifact/api-test/runtime/ci-runs/{task.run.run_key if task.run else ''}".rstrip("/")
    summary_url = f"{artifact_base}/summary.json"
    failed_url = f"{artifact_base}/failed_nodeids.json"
    try:
        with _request(config, "GET", summary_url) as response:
            summary = json.loads(response.read().decode("utf-8"))
        with _request(config, "GET", failed_url) as response:
            failed_nodeids = json.loads(response.read().decode("utf-8"))
    except JenkinsServiceError as exc:
        return {
            "jenkins_result": build_payload.get("result"),
            "summary": None,
            "failed_nodeids": [],
            "error_summary": f"Jenkins artifact missing or unreadable: {exc}",
        }

    return {
        "jenkins_result": build_payload.get("result"),
        "summary": summary,
        "failed_nodeids": failed_nodeids,
        "artifact_base_url": public_artifact_base,
        "summary_artifact_url": f"{public_artifact_base}/summary.json",
        "failed_nodeids_artifact_url": f"{public_artifact_base}/failed_nodeids.json",
        "allure_report_url": f"{public_artifact_base}/allure-report/index.html",
    }
