"""固定无凭据冒烟和平台自身全量回归计划。"""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import EvidenceStore
from .models import CommandSpec, Diagnostic, HttpRequest, RunContext, StageResult


@dataclass(frozen=True)
class TestProbe:
    name: str
    endpoint: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "endpoint": self.endpoint}


@dataclass(frozen=True)
class TestCommand:
    name: str
    argv: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "argv": list(self.argv)}


@dataclass(frozen=True)
class TestPlan:
    mode: str
    http_probes: tuple[TestProbe, ...]
    commands: tuple[TestCommand, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "http_probes": [item.to_dict() for item in self.http_probes],
            "commands": [item.to_dict() for item in self.commands],
        }


SMOKE_PROBES = (
    TestProbe("backend-live", "BACKEND_SERVICE_URL:/api/v1/health/live/"),
    TestProbe("backend-ready", "BACKEND_SERVICE_URL:/api/v1/health/ready/"),
    TestProbe("frontend-health", "FRONTEND_SERVICE_URL:/health"),
    TestProbe("frontend-spa", "FRONTEND_SERVICE_URL:/login"),
    TestProbe("frontend-api-proxy", "FRONTEND_SERVICE_URL:/api/v1/health/ready/"),
    TestProbe("api-docs", "BACKEND_SERVICE_URL:/api/docs/"),
)


class TestService:
    __test__ = False

    def __init__(self, runner, http_client, evidence: EvidenceStore):
        self.runner = runner
        self.http_client = http_client
        self.evidence = evidence

    @staticmethod
    def build_plan(context: RunContext) -> TestPlan:
        if not context.run_full_tests:
            return TestPlan(mode="smoke", http_probes=SMOKE_PROBES, commands=())

        prefix = f"platform-bootstrap-{context.build_id}"
        commands = (
            TestCommand(
                "backend-pytest",
                (
                    "docker",
                    "create",
                    "--name",
                    f"{prefix}-backend",
                    "--network",
                    "aiapitest-platform",
                    "--env",
                    "DJANGO_SETTINGS_MODULE=config.settings.test",
                    "aiapitest-backend:local",
                    "sh",
                    "-c",
                    "mkdir -p /tmp/platform-bootstrap-evidence && "
                    "python -m pytest tests --junitxml=/tmp/platform-bootstrap-evidence/backend-junit.xml",
                ),
            ),
            TestCommand(
                "frontend-unit",
                (
                    "docker",
                    "create",
                    "--name",
                    f"{prefix}-frontend-unit",
                    "--network",
                    "aiapitest-platform",
                    "aiapitest-frontend-test:local",
                    "sh",
                    "-c",
                    "mkdir -p /tmp/platform-bootstrap-evidence && "
                    "npm run test:unit -- --reporter=junit "
                    "--outputFile=/tmp/platform-bootstrap-evidence/frontend-unit-junit.xml",
                ),
            ),
            TestCommand(
                "frontend-build",
                (
                    "docker",
                    "create",
                    "--name",
                    f"{prefix}-frontend-build",
                    "--network",
                    "aiapitest-platform",
                    "aiapitest-frontend-test:local",
                    "sh",
                    "-c",
                    "mkdir -p /tmp/platform-bootstrap-evidence && "
                    "npm run build > /tmp/platform-bootstrap-evidence/frontend-build.log 2>&1",
                ),
            ),
            TestCommand(
                "frontend-playwright",
                (
                    "docker",
                    "create",
                    "--name",
                    f"{prefix}-frontend-e2e",
                    "--network",
                    "aiapitest-platform",
                    "aiapitest-frontend-test:local",
                    "sh",
                    "-c",
                    "mkdir -p /tmp/platform-bootstrap-evidence && "
                    "PLAYWRIGHT_HTML_OUTPUT_DIR=/tmp/platform-bootstrap-evidence/playwright-report "
                    "npm run test:e2e -- --reporter=html",
                ),
            ),
            TestCommand(
                "api-runner-protocol-tests",
                (
                    "docker",
                    "create",
                    "--name",
                    f"{prefix}-api-runner",
                    "--network",
                    "aiapitest-platform",
                    "--workdir",
                    "/workspace/AiApiTest-DWP",
                    "aiapitest-api-runner:local",
                    "sh",
                    "-c",
                    "mkdir -p /tmp/platform-bootstrap-evidence && "
                    "python -m pytest api-test/tests jenkins/tests "
                    "--junitxml=/tmp/platform-bootstrap-evidence/tooling-junit.xml",
                ),
            ),
        )
        return TestPlan(mode="full", http_probes=SMOKE_PROBES, commands=commands)

    def _diagnostic(
        self,
        code: str,
        target: str,
        reason: str,
        observed: str,
        evidence: str,
        *,
        manual_export: bool = False,
    ) -> Diagnostic:
        suggestion = "Inspect the test evidence and repair the platform regression before rebuilding."
        if manual_export:
            suggestion = (
                "The test container was preserved; inspect/export evidence as needed, "
                "remove the named container manually, then rebuild."
            )
        return Diagnostic(
            stage="tests",
            code=code,
            target=target,
            reason=reason,
            observed=observed,
            evidence=(evidence,),
            suggestion=suggestion,
            rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
        )

    @staticmethod
    def _smoke_urls(config: dict[str, str]) -> tuple[tuple[str, str], ...]:
        # 环境 Job 位于 Compose 网络内，固定使用服务名；公开地址只用于 Summary。
        backend = "http://backend:8000"
        frontend = "http://frontend"
        return (
            ("backend-live", f"{backend}/api/v1/health/live/"),
            ("backend-ready", f"{backend}/api/v1/health/ready/"),
            ("frontend-health", f"{frontend}/health"),
            ("frontend-spa", f"{frontend}/login"),
            ("frontend-api-proxy", f"{frontend}/api/v1/health/ready/"),
            ("api-docs", f"{backend}/api/docs/"),
        )

    def _run_smoke(self, config: dict[str, str]) -> list[Diagnostic]:
        urls = self._smoke_urls(config)
        diagnostics: list[Diagnostic] = []
        for name, url in urls:
            evidence_path = self.evidence.path(f"test-smoke-{name}.log")
            try:
                response = self.http_client.request(
                    HttpRequest(
                        method="GET",
                        url=url,
                        headers={"Accept": "application/json,text/html"},
                        timeout_seconds=15,
                    )
                )
                if 200 <= response.status < 300:
                    evidence_path.write_text(
                        self.evidence.redactor.text(
                            f"url={url}\nstatus={response.status}\nbody={response.body.decode('utf-8', errors='replace')[:2000]}\n"
                        ),
                        encoding="utf-8",
                    )
                    continue
                body = response.body.decode("utf-8", errors="replace")[:2_000]
                observed = f"status={response.status}; body={body}"
            except Exception as exc:  # HTTP adapter-specific errors become structured diagnostics.
                observed = f"{type(exc).__name__}: {exc}"
            evidence_path.write_text(
                self.evidence.redactor.text(f"url={url}\n{observed}\n"),
                encoding="utf-8",
            )
            diagnostics.append(
                self._diagnostic(
                    "TEST_SMOKE_PROBE_FAILED",
                    name,
                    "credential-free smoke probe failed",
                    observed,
                    str(evidence_path),
                )
            )
        return diagnostics

    def _run_full(self, context: RunContext, plan: TestPlan) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for command in plan.commands:
            create = self.runner.run(
                CommandSpec(
                    argv=command.argv,
                    cwd=context.workspace,
                    timeout_seconds=60,
                    evidence_path=self.evidence.path(f"test-{command.name}-create.log"),
                )
            )
            container_name = command.argv[3]
            if not create.success:
                diagnostics.append(
                    self._diagnostic(
                        "TEST_CONTAINER_CREATE_FAILED",
                        command.name,
                        "test container could not be created",
                        f"exit={create.returncode}; {create.redacted_output_tail}",
                        create.evidence_path,
                    )
                )
                continue

            start = self.runner.run(
                CommandSpec(
                    argv=("docker", "start", "-a", container_name),
                    cwd=context.workspace,
                    timeout_seconds=3600,
                    evidence_path=self.evidence.path(f"test-{command.name}-run.log"),
                )
            )
            if not start.success:
                diagnostics.append(
                    self._diagnostic(
                        "TEST_PLATFORM_REGRESSION_FAILED",
                        command.name,
                        "platform regression command failed",
                        f"exit={start.returncode}; {start.redacted_output_tail}",
                        start.evidence_path,
                    )
                )

            export_dir = self.evidence.path(f"full/{command.name}")
            export_dir.mkdir(parents=True, exist_ok=True)
            export = self.runner.run(
                CommandSpec(
                    argv=(
                        "docker",
                        "cp",
                        f"{container_name}:/tmp/platform-bootstrap-evidence/.",
                        str(export_dir),
                    ),
                    cwd=context.workspace,
                    timeout_seconds=120,
                    evidence_path=self.evidence.path(f"test-{command.name}-export.log"),
                )
            )
            if not export.success:
                diagnostics.append(
                    self._diagnostic(
                        "TEST_EVIDENCE_EXPORT_FAILED",
                        command.name,
                        "test evidence could not be exported",
                        f"exit={export.returncode}; container={container_name}",
                        export.evidence_path,
                        manual_export=True,
                    )
                )
                continue

            cleanup = self.runner.run(
                CommandSpec(
                    argv=("docker", "rm", "-f", container_name),
                    cwd=context.workspace,
                    timeout_seconds=30,
                    evidence_path=self.evidence.path(f"test-{command.name}-cleanup.log"),
                )
            )
            if not cleanup.success:
                diagnostics.append(
                    self._diagnostic(
                        "TEST_CONTAINER_CLEANUP_FAILED",
                        command.name,
                        "test container cleanup failed after evidence export",
                        f"exit={cleanup.returncode}; container={container_name}; {cleanup.redacted_output_tail}",
                        cleanup.evidence_path,
                        manual_export=True,
                    )
                )
        return diagnostics

    def run(self, context: RunContext, config: dict[str, str]) -> StageResult:
        prerequisite = self.evidence.read_stage_result("health")
        if not prerequisite or prerequisite.get("success") is not True:
            gate_evidence = self.evidence.write_text(
                "test-health-gate.log",
                "stage=tests\ntarget=health\nstatus=missing-or-failed\naction=tests not started",
            )
            result = StageResult(
                stage="tests",
                success=False,
                diagnostics=(
                    self._diagnostic(
                        "TEST_HEALTH_GATE_FAILED",
                        "health",
                        "health stage did not succeed",
                        "tests were not started",
                        str(gate_evidence),
                    ),
                ),
            )
            self.evidence.write_stage_result("tests", result)
            return result

        plan = self.build_plan(context)
        diagnostics = self._run_smoke(config)
        if context.run_full_tests:
            diagnostics.extend(self._run_full(context, plan))
        result = StageResult(
            stage="tests",
            success=not diagnostics,
            details={"plan": plan.to_dict()},
            diagnostics=tuple(diagnostics),
        )
        self.evidence.write_stage_result("tests", result)
        return result
