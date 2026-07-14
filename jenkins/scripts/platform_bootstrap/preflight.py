"""平台启动前的只读环境检查。"""

from __future__ import annotations

from pathlib import Path

from .configuration import ConfigError, DotEnvConfig
from .evidence import EvidenceStore
from .models import CommandSpec, Diagnostic, RunContext, StageResult


REQUIRED_ENV_KEYS = (
    "MYSQL_ROOT_PASSWORD",
    "DJANGO_SECRET_KEY",
    "AUTH_TOKEN_SECRET",
    "JENKINS_PUBLIC_BASE_URL",
    "JENKINS_API_BASE_URL",
    "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME",
    "MYSQL_HOST",
    "MYSQL_HOST_PORT",
    "FRONTEND_SERVICE_URL",
    "BACKEND_SERVICE_URL",
    "BACKEND_API_BASE_URL",
)
LIMITED_CONTAINER_FORMAT = "{{.Id}}|{{.State.Running}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}"
LIMITED_HEALTH_LOG_FORMAT = "{{range .State.Health.Log}}{{.ExitCode}}|{{.Output}}{{println}}{{end}}"


def _diagnostic(code: str, target: str, reason: str, observed: str, evidence: Path) -> Diagnostic:
    suggestions = {
        "CONFIG_ENV_MISSING": "Create the private root .env from .env.example, then rebuild the Jenkins job.",
        "CONFIG_REQUIRED_ENV_MISSING": "Add the listed configuration keys to the private root .env, then rebuild.",
        "DOCKER_SOCKET_PERMISSION_DENIED": (
            "Set DOCKER_GID to the Docker socket group, let the user rebuild Jenkins, then rebuild this job."
        ),
        "BOOTSTRAP_MYSQL_NOT_RUNNING": "Start the MySQL container, wait until it is healthy, then rebuild.",
        "BOOTSTRAP_MYSQL_UNHEALTHY": "Inspect the archived MySQL status/log, repair MySQL, then rebuild.",
    }
    return Diagnostic(
        stage="preflight",
        code=code,
        target=target,
        reason=reason,
        observed=observed,
        evidence=(str(evidence),),
        suggestion=suggestions.get(code, "Inspect the archived evidence, repair the environment, then rebuild."),
        rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
    )


class PreflightService:
    def __init__(self, runner, evidence: EvidenceStore):
        self.runner = runner
        self.evidence = evidence

    def _command(self, context: RunContext, name: str, argv: tuple[str, ...]):
        return self.runner.run(
            CommandSpec(
                argv=argv,
                cwd=context.workspace,
                timeout_seconds=60,
                evidence_path=self.evidence.path(f"preflight-{name}.log"),
            )
        )

    def _finish(self, result: StageResult) -> StageResult:
        self.evidence.write_stage_result("preflight", result)
        return result

    def run(self, context: RunContext) -> StageResult:
        if not context.env_file.is_file():
            evidence = self.evidence.write_text(
                "preflight-env.log",
                "config_file=.env\nstatus=missing\naction=no file was created",
            )
            return self._finish(
                StageResult(
                    stage="preflight",
                    success=False,
                    diagnostics=(
                        _diagnostic(
                            "CONFIG_ENV_MISSING",
                            ".env",
                            "private configuration file is missing",
                            ".env not found; no file was created",
                            evidence,
                        ),
                    ),
                )
            )
        if not context.compose_file.is_file():
            evidence = self.evidence.write_text(
                "preflight-compose.log",
                "config_file=docker-compose.yml\nstatus=missing\naction=no command was executed",
            )
            return self._finish(
                StageResult(
                    stage="preflight",
                    success=False,
                    diagnostics=(
                        _diagnostic(
                            "CONFIG_COMPOSE_MISSING",
                            "docker-compose.yml",
                            "Compose file is missing",
                            "docker-compose.yml not found",
                            evidence,
                        ),
                    ),
                )
            )

        try:
            config = DotEnvConfig.load(context.env_file)
            config.require(REQUIRED_ENV_KEYS)
        except ConfigError as exc:
            evidence = self.evidence.path("preflight-env.log")
            evidence.write_text(str(exc) + "\n", encoding="utf-8")
            return self._finish(
                StageResult(
                    stage="preflight",
                    success=False,
                    details={"environment_keys": config.key_status(REQUIRED_ENV_KEYS) if "config" in locals() else {}},
                    diagnostics=(
                        _diagnostic(
                            "CONFIG_REQUIRED_ENV_MISSING",
                            ".env",
                            "required configuration keys are missing",
                            str(exc),
                            evidence,
                        ),
                    ),
                )
            )

        checks = (
            ("docker-version", ("docker", "--version")),
            ("compose-version", ("docker", "compose", "version")),
            ("docker-info", ("docker", "info")),
        )
        for name, argv in checks:
            command_result = self._command(context, name, argv)
            if not command_result.success:
                permission_denied = "permission denied" in command_result.redacted_output_tail.lower()
                code = "DOCKER_SOCKET_PERMISSION_DENIED" if permission_denied else "BOOTSTRAP_DOCKER_UNAVAILABLE"
                return self._finish(
                    StageResult(
                        stage="preflight",
                        success=False,
                        diagnostics=(
                            _diagnostic(
                                code,
                                "Docker",
                                f"{name} failed",
                                f"exit={command_result.returncode}; {command_result.redacted_output_tail}",
                                Path(command_result.evidence_path),
                            ),
                        ),
                    )
                )

        compose_prefix = (
            "docker",
            "compose",
            "--project-name",
            "aiapitest-dwp",
            "--env-file",
            str(context.env_file),
            "-f",
            str(context.compose_file),
        )
        for name, suffix in (
            ("compose-config", ("config", "--quiet")),
            ("compose-config-source", ("config", "--no-interpolate")),
        ):
            command_result = self._command(context, name, compose_prefix + suffix)
            if not command_result.success:
                return self._finish(
                    StageResult(
                        stage="preflight",
                        success=False,
                        diagnostics=(
                            _diagnostic(
                                "BOOTSTRAP_COMPOSE_CONFIG_INVALID",
                                "docker-compose.yml",
                                "Compose configuration validation failed",
                                f"exit={command_result.returncode}; {command_result.redacted_output_tail}",
                                Path(command_result.evidence_path),
                            ),
                        ),
                    )
                )

        baselines: dict[str, str] = {}
        for name, container in (("jenkins", "aiapitest-jenkins"), ("mysql", "aiapitest-mysql")):
            command_result = self._command(
                context,
                f"{name}-inspect",
                ("docker", "inspect", "--format", LIMITED_CONTAINER_FORMAT, container),
            )
            if not command_result.success:
                code = "BOOTSTRAP_MYSQL_NOT_RUNNING" if name == "mysql" else "BOOTSTRAP_JENKINS_NOT_RUNNING"
                return self._finish(
                    StageResult(
                        stage="preflight",
                        success=False,
                        diagnostics=(
                            _diagnostic(
                                code,
                                container,
                                "required bootstrap container is unavailable",
                                f"exit={command_result.returncode}",
                                Path(command_result.evidence_path),
                            ),
                        ),
                    )
                )
            parts = command_result.redacted_output_tail.strip().split("|", 2)
            container_id = parts[0] if len(parts) == 3 else "unknown"
            running = len(parts) == 3 and parts[1].strip().lower() == "true"
            health = parts[2].strip() if len(parts) == 3 else "missing"
            baselines[name] = container_id
            if not running:
                code = "BOOTSTRAP_MYSQL_NOT_RUNNING" if name == "mysql" else "BOOTSTRAP_JENKINS_NOT_RUNNING"
                return self._finish(
                    StageResult(
                        stage="preflight",
                        success=False,
                        diagnostics=(
                            _diagnostic(
                                code,
                                container,
                                "container is not running",
                                "running=false",
                                Path(command_result.evidence_path),
                            ),
                        ),
                    )
                )
            if name == "mysql" and health != "healthy":
                health_result = self._command(
                    context,
                    "mysql-health-log",
                    (
                        "docker",
                        "inspect",
                        "--format",
                        LIMITED_HEALTH_LOG_FORMAT,
                        "aiapitest-mysql",
                    ),
                )
                logs_result = self._command(
                    context,
                    "mysql-tail-logs",
                    ("docker", "logs", "--tail", "200", "aiapitest-mysql"),
                )
                observed = self.evidence.redactor.text(
                    f"health={health}; health_tail={health_result.redacted_output_tail[-2000:]}; "
                    f"log_tail={logs_result.redacted_output_tail[-2000:]}"
                )
                diagnostic = Diagnostic(
                    stage="preflight",
                    code="BOOTSTRAP_MYSQL_UNHEALTHY",
                    target=container,
                    reason="MySQL health is not healthy",
                    observed=observed,
                    evidence=(
                        command_result.evidence_path,
                        health_result.evidence_path,
                        logs_result.evidence_path,
                    ),
                    suggestion="Inspect the limited health output and redacted MySQL log tail, repair MySQL, then rebuild.",
                    rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after MySQL is healthy.",
                )
                return self._finish(
                    StageResult(
                        stage="preflight",
                        success=False,
                        diagnostics=(diagnostic,),
                    )
                )

        return self._finish(
            StageResult(
                stage="preflight",
                success=True,
                details={
                    "environment_keys": config.key_status(REQUIRED_ENV_KEYS),
                    "baseline_container_ids": baselines,
                    "warnings": list(config.warnings),
                },
            )
        )
