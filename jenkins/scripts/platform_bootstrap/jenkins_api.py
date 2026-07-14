"""通过 Jenkins API 触发并跟踪统一平台环境 Job。"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import quote, urlencode, urlsplit

from .configuration import ConfigError, DotEnvConfig, parse_bounded_int
from .models import Diagnostic, HttpRequest
from .security import Redactor


@dataclass(frozen=True)
class JenkinsTriggerConfig:
    base_url: str
    job_name: str
    username: str
    api_token: str
    request_timeout_seconds: int
    queue_poll_interval_seconds: int
    build_poll_interval_seconds: int
    total_timeout_seconds: int

    @classmethod
    def load(cls, path: Path) -> "JenkinsTriggerConfig":
        config = DotEnvConfig.load(path)
        required = config.require(
            (
                "JENKINS_API_BASE_URL",
                "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME",
                "JENKINS_USERNAME",
                "JENKINS_API_TOKEN",
            )
        )
        return cls(
            base_url=required["JENKINS_API_BASE_URL"].rstrip("/"),
            job_name=required["JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME"],
            username=required["JENKINS_USERNAME"],
            api_token=required["JENKINS_API_TOKEN"],
            request_timeout_seconds=parse_bounded_int(
                config.get("JENKINS_REQUEST_TIMEOUT_SECONDS"),
                default=15,
                minimum=1,
                maximum=120,
            ),
            queue_poll_interval_seconds=parse_bounded_int(
                config.get("JENKINS_QUEUE_POLL_INTERVAL_SECONDS"),
                default=5,
                minimum=1,
                maximum=60,
            ),
            build_poll_interval_seconds=parse_bounded_int(
                config.get("JENKINS_BUILD_POLL_INTERVAL_SECONDS"),
                default=10,
                minimum=1,
                maximum=300,
            ),
            total_timeout_seconds=parse_bounded_int(
                config.get("JENKINS_BUILD_POLL_TIMEOUT_SECONDS"),
                default=1800,
                minimum=1,
                maximum=86_400,
            ),
        )


@dataclass(frozen=True)
class TriggerOutcome:
    success: bool
    status: str
    build_url: str
    queue_url: str
    summary: Mapping[str, object]
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "status": self.status,
            "build_url": self.build_url,
            "queue_url": self.queue_url,
            "summary": dict(self.summary),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


class _RequestFailure(RuntimeError):
    def __init__(self, code: str, target: str, reason: str, observed: str):
        super().__init__(reason)
        self.code = code
        self.target = target
        self.reason = reason
        self.observed = observed


def encode_job_url(base_url: str, job_name: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("JENKINS_API_BASE_URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConfigError("JENKINS_API_BASE_URL must not contain credentials, query, or fragment")
    segments = job_name.split("/")
    if not segments or any(not segment.strip() for segment in segments):
        raise ConfigError("JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME contains an empty folder segment")
    suffix = "".join(f"/job/{quote(segment, safe='')}" for segment in segments)
    return base_url.rstrip("/") + suffix


class JenkinsApiClient:
    def __init__(self, config: JenkinsTriggerConfig, http_client, *, monotonic, sleep):
        self.config = config
        self.http_client = http_client
        self.monotonic = monotonic
        self.sleep = sleep
        self.redactor = Redactor(
            extra_secrets=(config.username, config.api_token),
        )
        self.job_url = encode_job_url(config.base_url, config.job_name)
        credential = base64.b64encode(
            f"{config.username}:{config.api_token}".encode("utf-8")
        ).decode("ascii")
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {credential}",
        }

    @staticmethod
    def _header(headers: Mapping[str, str], name: str) -> str:
        for key, value in headers.items():
            if key.lower() == name.lower():
                return value
        return ""

    def _request(self, method: str, url: str, *, body: bytes | None = None, context: str):
        headers = dict(self.headers)
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            response = self.http_client.request(
                HttpRequest(
                    method=method,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout_seconds=self.config.request_timeout_seconds,
                )
            )
        except Exception as exc:
            raise _RequestFailure(
                "JENKINS_UNREACHABLE",
                context,
                "Jenkins request failed",
                self.redactor.text(f"{type(exc).__name__}: {exc}"),
            ) from exc
        if response.status in {401, 403}:
            raise _RequestFailure(
                "JENKINS_AUTHENTICATION_FAILED",
                context,
                "Jenkins authentication or authorization failed",
                f"HTTP {response.status}",
            )
        if response.status == 404:
            if context == "job":
                code = "JENKINS_JOB_NOT_FOUND"
                reason = "Jenkins Job does not exist"
            elif context == "queue":
                code = "JENKINS_QUEUE_LOST"
                reason = "Jenkins queue item was removed before a build was assigned"
            else:
                code = "JENKINS_BUILD_NOT_FOUND"
                reason = "Jenkins build/status resource does not exist"
            raise _RequestFailure(code, context, reason, "HTTP 404")
        if response.status >= 500:
            raise _RequestFailure(
                "JENKINS_SERVER_ERROR",
                context,
                "Jenkins returned a server error",
                f"HTTP {response.status}",
            )
        if not 200 <= response.status < 400:
            raise _RequestFailure(
                "JENKINS_HTTP_ERROR",
                context,
                "Unexpected Jenkins HTTP response",
                f"HTTP {response.status}",
            )
        return response

    def _json(self, method: str, url: str, *, body: bytes | None = None, context: str):
        response = self._request(method, url, body=body, context=context)
        if not response.body:
            return {}, response
        try:
            value = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _RequestFailure(
                "JENKINS_RESPONSE_INVALID",
                context,
                "Jenkins returned invalid JSON",
                type(exc).__name__,
            ) from exc
        return value, response

    def _diagnostic(self, failure: _RequestFailure, *, evidence: str = "") -> Diagnostic:
        return Diagnostic(
            stage="trigger",
            code=failure.code,
            target=failure.target,
            reason=failure.reason,
            observed=self.redactor.text(failure.observed),
            evidence=(evidence,) if evidence else (),
            suggestion="Resolve the Jenkins/API condition shown above, then run the same trigger command again.",
            rerun="Run trigger-platform-bootstrap again with the same two boolean values.",
        )

    def _failure_outcome(
        self,
        failure: _RequestFailure,
        *,
        status: str = "FAILURE",
        build_url: str = "",
        queue_url: str = "",
        summary: Mapping[str, object] | None = None,
    ) -> TriggerOutcome:
        return TriggerOutcome(
            success=False,
            status=status,
            build_url=build_url,
            queue_url=queue_url,
            summary=summary or {},
            diagnostics=(self._diagnostic(failure, evidence=build_url or queue_url),),
        )

    def _deadline_reached(self, deadline: float) -> bool:
        return self.monotonic() >= deadline

    def _sleep_until(self, deadline: float, interval: int) -> None:
        remaining = max(0.0, deadline - self.monotonic())
        self.sleep(min(float(interval), remaining))

    def trigger(self, *, build_all: bool, run_full_tests: bool) -> TriggerOutcome:
        deadline = self.monotonic() + self.config.total_timeout_seconds
        queue_url = ""
        build_url = ""
        summary: Mapping[str, object] = {}
        try:
            job, _ = self._json("GET", f"{self.job_url}/api/json", context="job")
            last_build = job.get("lastBuild") or {}
            last_build_url = str(last_build.get("url") or "")
            if last_build_url and "building" not in last_build:
                if not last_build_url.endswith("/"):
                    last_build_url += "/"
                last_build_status, _ = self._json(
                    "GET",
                    f"{last_build_url}api/json",
                    context="last-build",
                )
                last_build = {**last_build, **last_build_status}
            if job.get("inQueue") or last_build.get("building"):
                return TriggerOutcome(
                    success=False,
                    status="BUSY",
                    build_url=str(last_build.get("url") or ""),
                    queue_url=str((job.get("queueItem") or {}).get("url") or ""),
                    summary={},
                    diagnostics=(
                        Diagnostic(
                            stage="trigger",
                            code="JENKINS_JOB_BUSY",
                            target=self.config.job_name,
                            reason="The platform bootstrap Job is already running or queued",
                            observed="No second build was submitted",
                            evidence=(),
                            suggestion="Wait for the current build/queue item to finish, then inspect its summary.",
                            rerun="Only rerun after the current environment build reaches a terminal state.",
                        ),
                    ),
                )

            body = urlencode(
                {
                    "build_all": str(build_all).lower(),
                    "run_full_tests": str(run_full_tests).lower(),
                }
            ).encode("ascii")
            trigger_response = self._request(
                "POST",
                f"{self.job_url}/buildWithParameters",
                body=body,
                context="trigger",
            )
            queue_url = self._header(trigger_response.headers, "Location")
            if not queue_url:
                raise _RequestFailure(
                    "JENKINS_QUEUE_LOCATION_MISSING",
                    "trigger",
                    "Jenkins accepted the request without a queue Location",
                    f"HTTP {trigger_response.status}",
                )
            if not queue_url.endswith("/"):
                queue_url += "/"

            while not self._deadline_reached(deadline):
                queue, _ = self._json(
                    "GET",
                    f"{queue_url}api/json",
                    context="queue",
                )
                if queue.get("cancelled"):
                    raise _RequestFailure(
                        "JENKINS_QUEUE_CANCELLED",
                        "queue",
                        "Jenkins queue item was cancelled",
                        queue_url,
                    )
                executable = queue.get("executable") or {}
                if executable.get("url"):
                    build_url = str(executable["url"])
                    if not build_url.endswith("/"):
                        build_url += "/"
                    break
                self._sleep_until(deadline, self.config.queue_poll_interval_seconds)
            else:
                raise _RequestFailure(
                    "JENKINS_TRIGGER_TIMEOUT",
                    "queue",
                    "Timed out waiting for Jenkins queue assignment",
                    f"timeout={self.config.total_timeout_seconds}s",
                )

            build_payload: Mapping[str, object] = {}
            while not self._deadline_reached(deadline):
                build_payload, _ = self._json(
                    "GET",
                    f"{build_url}api/json",
                    context="build",
                )
                if not build_payload.get("building", False):
                    break
                self._sleep_until(deadline, self.config.build_poll_interval_seconds)
            else:
                raise _RequestFailure(
                    "JENKINS_TRIGGER_TIMEOUT",
                    "build",
                    "Timed out waiting for Jenkins build completion",
                    f"timeout={self.config.total_timeout_seconds}s",
                )

            build_status = str(build_payload.get("result") or "UNKNOWN")
            artifacts = build_payload.get("artifacts") or []
            for artifact in artifacts:
                if not isinstance(artifact, Mapping):
                    continue
                if Path(str(artifact.get("fileName", ""))).name != "platform-bootstrap-summary.json":
                    continue
                relative_path = str(artifact.get("relativePath", ""))
                artifact_url = f"{build_url}artifact/{quote(relative_path, safe='/')}"
                artifact_payload, _ = self._json(
                    "GET",
                    artifact_url,
                    context="summary",
                )
                if isinstance(artifact_payload, Mapping):
                    summary = self.redactor.mapping(artifact_payload)
                break

            if build_status == "SUCCESS":
                if not summary:
                    raise _RequestFailure(
                        "JENKINS_SUMMARY_MISSING",
                        "summary",
                        "Jenkins build succeeded but the structured summary artifact is missing",
                        build_url,
                    )
                return TriggerOutcome(
                    success=True,
                    status=build_status,
                    build_url=build_url,
                    queue_url=queue_url,
                    summary=summary,
                    diagnostics=(),
                )
            code = "JENKINS_BUILD_ABORTED" if build_status == "ABORTED" else "JENKINS_BUILD_FAILED"
            raise _RequestFailure(
                code,
                "build",
                f"Jenkins build reached terminal state {build_status}",
                build_url,
            )
        except _RequestFailure as failure:
            status = "TIMEOUT" if failure.code == "JENKINS_TRIGGER_TIMEOUT" else (
                "ABORTED" if failure.code == "JENKINS_BUILD_ABORTED" else "FAILURE"
            )
            return self._failure_outcome(
                failure,
                status=status,
                build_url=build_url,
                queue_url=queue_url,
                summary=summary,
            )
