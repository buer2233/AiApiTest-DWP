"""受控执行 Django schema 与首次数据初始化。"""

from __future__ import annotations

from .evidence import EvidenceStore
from .models import CommandSpec, Diagnostic, RunContext, StageResult


class SchemaInitializationService:
    """通过固定的一次性 Compose 服务执行不可拼接的初始化命令。"""

    stage_name = "schema-initialization"
    steps = (
        ("migrate", ("migrate", "--noinput")),
        ("seed_environment", ("seed_environment", "--reconcile")),
        ("sync_modules", ("sync_modules", "--reconcile")),
        ("init_admin", ("init_admin", "--bootstrap-only")),
    )

    def __init__(self, runner, evidence: EvidenceStore):
        self.runner = runner
        self.evidence = evidence

    @staticmethod
    def _prefix(context: RunContext) -> tuple[str, ...]:
        return (
            "docker",
            "compose",
            "--project-name",
            "aiapitest-dwp",
            "--env-file",
            str(context.env_file),
            "-f",
            str(context.compose_file),
            "--profile",
            "bootstrap",
            "run",
            "--rm",
            "--no-deps",
            "backend-bootstrap",
            "python",
            "manage.py",
        )

    def _gate_failure(self) -> StageResult:
        evidence_path = self.evidence.write_text(
            "schema-initialization-dependency-gate.log",
            "stage=schema-initialization\ntarget=dependencies\n"
            "status=missing-or-failed\naction=initialization not attempted",
        )
        return StageResult(
            stage=self.stage_name,
            success=False,
            diagnostics=(
                Diagnostic(
                    stage=self.stage_name,
                    code="SCHEMA_INITIALIZATION_DEPENDENCY_GATE_FAILED",
                    target="dependencies",
                    reason="dependency assurance did not succeed",
                    observed="schema and initial data commands were not attempted",
                    evidence=(str(evidence_path),),
                    suggestion="Repair all dependency domains before schema initialization.",
                    rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
                ),
            ),
        )

    def run(self, context: RunContext) -> StageResult:
        prerequisite = self.evidence.read_stage_result("dependencies")
        if not prerequisite or prerequisite.get("success") is not True:
            result = self._gate_failure()
            self.evidence.write_stage_result(self.stage_name, result)
            return result

        completed_steps: list[str] = []
        for step_name, command in self.steps:
            command_result = self.runner.run(
                CommandSpec(
                    argv=self._prefix(context) + command,
                    cwd=context.workspace,
                    timeout_seconds=900,
                    evidence_path=self.evidence.path(
                        f"schema-initialization-{step_name}.log"
                    ),
                )
            )
            if not command_result.success:
                # 命令日志由 runner 脱敏保存；结构化诊断只记录固定元数据，避免重复暴露输出。
                result = StageResult(
                    stage=self.stage_name,
                    success=False,
                    details={"completed_steps": completed_steps},
                    diagnostics=(
                        Diagnostic(
                            stage=self.stage_name,
                            code="SCHEMA_INITIALIZATION_COMMAND_FAILED",
                            target=step_name,
                            reason="schema or initial data command failed",
                            observed=(
                                f"step={step_name}; exit={command_result.returncode}; "
                                f"timed_out={command_result.timed_out}"
                            ),
                            evidence=(command_result.evidence_path,),
                            suggestion="Inspect the redacted command evidence, repair the reported issue, then rebuild.",
                            rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
                        ),
                    ),
                )
                self.evidence.write_stage_result(self.stage_name, result)
                return result
            completed_steps.append(step_name)

        result = StageResult(
            stage=self.stage_name,
            success=True,
            details={"completed_steps": completed_steps},
        )
        self.evidence.write_stage_result(self.stage_name, result)
        return result
