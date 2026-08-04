"""平台启动前的只读环境检查。"""

from __future__ import annotations

from pathlib import Path

from .addressing import validate_deployment_config
from .configuration import ConfigError, DotEnvConfig
from .env_contract import validate_contract
from .evidence import EvidenceStore
from .models import CommandSpec, Diagnostic, RunContext, StageResult


REQUIRED_ENV_KEYS = (
    "MYSQL_ROOT_PASSWORD",
    "DB_USER",
    "DB_PASSWORD",
    "DJANGO_SECRET_KEY",
    "AUTH_TOKEN_SECRET",
    "PLATFORM_BIND_HOST",
    "PLATFORM_PUBLIC_HOST",
    "PLATFORM_PUBLIC_SCHEME",
    "MYSQL_HOST_PORT",
    "JENKINS_HTTP_PORT",
    "JENKINS_AGENT_PORT",
    "BACKEND_HOST_PORT",
    "FRONTEND_HOST_PORT",
    "PROJECT_WORKSPACE",
    "DOCKER_GID",
    "CI_RUN_RETENTION_DAYS",
    "FRONTEND_PLAYWRIGHT_BASE_IMAGE",
    "JENKINS_USERNAME",
    "JENKINS_API_TOKEN",
    "INITIAL_ADMIN_USERNAME",
    "INITIAL_ADMIN_DISPLAY_NAME",
    "INITIAL_ADMIN_PASSWORD",
)
LIMITED_CONTAINER_FORMAT = "{{.Id}}|{{.State.Running}}|unknown"
LIMITED_HEALTH_LOG_FORMAT = "{{range .State.Health.Log}}{{.ExitCode}}|{{.Output}}{{println}}{{end}}"


def _diagnostic(code: str, target: str, reason: str, observed: str, evidence: Path) -> Diagnostic:
    suggestions = {
        "CONFIG_ENV_MISSING": "Create the private root .env from .env.example, then rebuild the Jenkins job.",
        "CONFIG_ENV_CONTRACT_DRIFT": "Align the private .env public section with .env.example, then rebuild the Jenkins job.",
        "CONFIG_REQUIRED_ENV_MISSING": "Add the listed configuration keys to the private root .env, then rebuild.",
        "CONFIG_ENV_VALUE_INVALID": "Correct the listed configuration key format in the private root .env, then rebuild.",
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

        contract_errors = validate_contract(context.env_file, context.workspace / ".env.example")
        if contract_errors:
            evidence = self.evidence.write_text(
                "preflight-env-contract.log",
                "config_file=.env\nstatus=drift\nissues=" + ",".join(contract_errors),
            )
            return self._finish(
                StageResult(
                    stage="preflight",
                    success=False,
                    details={"contract_issues": list(contract_errors)},
                    diagnostics=(
                        _diagnostic(
                            "CONFIG_ENV_CONTRACT_DRIFT",
                            ".env",
                            "root environment files do not satisfy the frozen Stage15 contract",
                            "configuration key/structure drift detected",
                            evidence,
                        ),
                    ),
                )
            )

        try:
            config = DotEnvConfig.load(context.env_file)
            config.require(REQUIRED_ENV_KEYS)
            validate_deployment_config(config.values)
            if config.get("JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL"):
                config.require(
                    (
                        "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH",
                        "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID",
                        "JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID",
                        "JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID",
                        "ENVIRONMENT_CATALOG_SERVICE_TOKEN",
                    )
                )
        except ConfigError as exc:
            missing = str(exc).startswith("required configuration")
            code = "CONFIG_REQUIRED_ENV_MISSING" if missing else "CONFIG_ENV_VALUE_INVALID"
            reason = (
                "required configuration keys are missing"
                if missing
                else "configuration key value is invalid"
            )
            evidence = self.evidence.path("preflight-env.log")
            evidence.write_text(str(exc) + "\n", encoding="utf-8")
            return self._finish(
                StageResult(
                    stage="preflight",
                    success=False,
                    details={"environment_keys": config.key_status(REQUIRED_ENV_KEYS) if "config" in locals() else {}},
                    diagnostics=(
                        _diagnostic(
                            code,
                            ".env",
                            reason,
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
        command_result = self._command(
            context,
            "compose-config",
            compose_prefix + ("config", "--quiet"),
        )
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
            if name == "mysql":
                health_result = self._command(
                    context,
                    "mysql-health-status",
                    ("docker", "inspect", "--format", "{{.State.Health.Status}}", "aiapitest-mysql"),
                )
                if health_result.success:
                    health = health_result.redacted_output_tail.strip()
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
