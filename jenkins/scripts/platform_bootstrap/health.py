"""有限超时的 HTTP 与 worker 心跳健康检查。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from .evidence import EvidenceStore
from .models import CommandSpec, Diagnostic, HttpRequest, RunContext, StageResult


INTERNAL_BACKEND_BASE_URL = "http://backend:8000"
INTERNAL_FRONTEND_BASE_URL = "http://frontend"


@dataclass(frozen=True)
class HealthProbe:
    name: str
    url: str


class HealthService:
    def __init__(
        self,
        runner,
        http_client,
        evidence: EvidenceStore,
        *,
        monotonic=time.monotonic,
        sleep=time.sleep,
    ):
        self.runner = runner
        self.http_client = http_client
        self.evidence = evidence
        self.monotonic = monotonic
        self.sleep = sleep
        self._evidence_errors: list[tuple[str, str]] = []

    def _diagnostic(self, code: str, target: str, reason: str, observed: str, evidence: str) -> Diagnostic:
        return Diagnostic(
            stage="health",
            code=code,
            target=target,
            reason=reason,
            observed=observed,
            evidence=(evidence,),
            suggestion="Inspect the application/Compose evidence, repair the reported service, then rebuild.",
            rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
        )

    def _write_probe_evidence(self, path, value: str, *, target: str) -> None:
        """单个健康日志无法写入时记录脱敏状态，继续形成最终 stage 诊断。"""
        try:
            path.write_text(value, encoding="utf-8")
        except OSError:
            self._evidence_errors.append((target, str(path)))

    def _poll(self, probe: HealthProbe, deadline: float, interval_seconds: int):
        last_status = 0
        last_body = ""
        evidence_path = self.evidence.path(f"health-{probe.name}.log")
        attempts: list[str] = []
        while True:
            remaining_seconds = deadline - self.monotonic()
            if remaining_seconds <= 0:
                self._write_probe_evidence(
                    evidence_path,
                    self.evidence.redactor.text(
                        f"url={probe.url}\nstatus=skipped\n"
                        "body=global health deadline elapsed before request\n"
                    ),
                    target=probe.name,
                )
                return False, last_status, last_body
            try:
                response = self.http_client.request(
                    HttpRequest(
                        method="GET",
                        url=probe.url,
                        headers={"Accept": "application/json,text/html"},
                        timeout_seconds=min(10, remaining_seconds),
                    )
                )
                last_status = response.status
                last_body = response.body.decode("utf-8", errors="replace")[:2_000]
                attempts.append(
                    self.evidence.redactor.text(
                        f"url={probe.url}\nstatus={response.status}\nbody={last_body}\n"
                    )
                )
                self._write_probe_evidence(
                    evidence_path,
                    "\n---\n".join(attempts),
                    target=probe.name,
                )
                if 200 <= response.status < 300:
                    return True, last_status, last_body
            except Exception as exc:  # HTTP adapter-specific failures remain diagnostic data.
                last_body = f"{type(exc).__name__}: HTTP probe did not return a response"
                attempts.append(
                    self.evidence.redactor.text(
                        f"url={probe.url}\nstatus=exception\nbody={last_body}\n"
                    )
                )
                self._write_probe_evidence(
                    evidence_path,
                    "\n---\n".join(attempts),
                    target=probe.name,
                )
            now = self.monotonic()
            if now >= deadline:
                return False, last_status, last_body
            self.sleep(min(interval_seconds, max(0, deadline - now)))

    def _poll_worker(self, context: RunContext, deadline: float, interval_seconds: int):
        """等待 worker 完成 Docker healthcheck 的启动窗口，避免刚创建即误判失败。"""
        evidence_path = self.evidence.path("health-worker.log")
        worker = None
        worker_output = "worker inspect skipped because the global health deadline elapsed"
        while True:
            remaining_seconds = deadline - self.monotonic()
            if remaining_seconds <= 0:
                if worker is None:
                    self._write_probe_evidence(
                        evidence_path,
                        worker_output,
                        target="jenkins-sync-worker",
                    )
                return worker, worker_output, False
            worker = self.runner.run(
                CommandSpec(
                    argv=(
                        "docker",
                        "inspect",
                        "--format",
                        "{{.State.Health.Status}}: {{range .State.Health.Log}}{{.Output}}{{end}}",
                        "aiapitest-jenkins-sync-worker",
                    ),
                    cwd=context.workspace,
                    timeout_seconds=min(30, remaining_seconds),
                    evidence_path=evidence_path,
                )
            )
            worker_output = worker.redacted_output_tail.lower()
            if worker.success and worker_output.strip().startswith("healthy"):
                return worker, worker_output, True
            now = self.monotonic()
            if now >= deadline:
                return worker, worker_output, False
            self.sleep(min(interval_seconds, max(0, deadline - now)))

    def run(
        self,
        context: RunContext,
        config: dict[str, str],
        *,
        timeout_seconds: int = 120,
        interval_seconds: int = 3,
    ) -> StageResult:
        self._evidence_errors = []
        prerequisite = self.evidence.read_stage_result("deploy")
        if not prerequisite or prerequisite.get("success") is not True:
            gate_evidence = self.evidence.write_text(
                "health-deploy-gate.log",
                "stage=health\ntarget=deploy\nstatus=missing-or-failed\naction=health probes not started",
            )
            result = StageResult(
                stage="health",
                success=False,
                diagnostics=(
                    self._diagnostic(
                        "HEALTH_DEPLOY_GATE_FAILED",
                        "deploy",
                        "deployment did not succeed",
                        "health probes were not started",
                        str(gate_evidence),
                    ),
                ),
            )
            self.evidence.write_stage_result("health", result)
            return result

        timeout_seconds = timeout_seconds if 1 <= timeout_seconds <= 900 else 120
        interval_seconds = interval_seconds if 1 <= interval_seconds <= 30 else 3
        probes = (
            HealthProbe("backend-live", f"{INTERNAL_BACKEND_BASE_URL}/api/v1/health/live/"),
            HealthProbe("backend-ready", f"{INTERNAL_BACKEND_BASE_URL}/api/v1/health/ready/"),
            HealthProbe("frontend-health", f"{INTERNAL_FRONTEND_BASE_URL}/health"),
            HealthProbe("frontend-spa", f"{INTERNAL_FRONTEND_BASE_URL}/login"),
            HealthProbe(
                "frontend-api-proxy",
                f"{INTERNAL_FRONTEND_BASE_URL}/api/v1/health/ready/",
            ),
        )
        deadline = self.monotonic() + timeout_seconds
        diagnostics: list[Diagnostic] = []
        probe_details: dict[str, object] = {}
        for probe in probes:
            ok, status, body = self._poll(probe, deadline, interval_seconds)
            probe_details[probe.name] = {"url": probe.url, "status": status, "success": ok}
            if not ok:
                reason = "HTTP probe did not become healthy before the finite deadline"
                code = "HEALTH_HTTP_PROBE_FAILED"
                if probe.name == "backend-ready":
                    try:
                        ready_reason = json.loads(body).get("reason", "unknown")
                    except (json.JSONDecodeError, AttributeError):
                        ready_reason = "unknown"
                    reason += f"; readiness_reason={ready_reason}"
                diagnostics.append(
                    self._diagnostic(
                        code,
                        probe.name,
                        reason,
                        f"status={status}; body={body}",
                        str(self.evidence.path(f"health-{probe.name}.log")),
                    )
                )

        worker, worker_output, worker_ok = self._poll_worker(
            context,
            deadline,
            interval_seconds,
        )
        probe_details["worker"] = {"success": worker_ok}
        if not worker_ok:
            stale = "stale" in worker_output or "missing" in worker_output
            diagnostics.append(
                self._diagnostic(
                    "HEALTH_WORKER_STALE" if stale else "HEALTH_WORKER_UNHEALTHY",
                    "jenkins-sync-worker",
                    "worker heartbeat is missing/stale" if stale else "worker container is unhealthy",
                    worker.redacted_output_tail if worker is not None else worker_output,
                    worker.evidence_path if worker is not None else str(self.evidence.path("health-worker.log")),
                )
            )

        for target, evidence_path in dict.fromkeys(self._evidence_errors):
            diagnostics.append(
                self._diagnostic(
                    "HEALTH_EVIDENCE_PERSISTENCE_FAILED",
                    target,
                    "health evidence could not be persisted",
                    "evidence write failed without exposing filesystem error details",
                    evidence_path,
                )
            )

        result = StageResult(
            stage="health",
            success=not diagnostics,
            details={"probes": probe_details, "timeout_seconds": timeout_seconds},
            diagnostics=tuple(diagnostics),
        )
        try:
            self.evidence.write_stage_result("health", result)
        except OSError:
            result = StageResult(
                stage="health",
                success=False,
                details=result.details,
                diagnostics=result.diagnostics
                + (
                    self._diagnostic(
                        "HEALTH_STAGE_RESULT_PERSISTENCE_FAILED",
                        "health",
                        "health stage result could not be persisted",
                        "stage result write failed without exposing filesystem error details",
                        str(self.evidence.root),
                    ),
                ),
            )
        return result
