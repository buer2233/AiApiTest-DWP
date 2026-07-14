"""仅管理三个应用服务的固定 Compose 部署。"""

from __future__ import annotations

from pathlib import Path

from .evidence import EvidenceStore
from .models import CommandSpec, Diagnostic, RunContext, StageResult


APPLICATION_SERVICES = ("backend", "frontend", "jenkins-sync-worker")


class DeployService:
    def __init__(self, runner, evidence: EvidenceStore):
        self.runner = runner
        self.evidence = evidence

    def _command(self, context: RunContext, name: str, suffix: tuple[str, ...]):
        prefix = (
            "docker",
            "compose",
            "--project-name",
            "aiapitest-dwp",
            "--env-file",
            str(context.env_file),
            "-f",
            str(context.compose_file),
        )
        return self.runner.run(
            CommandSpec(
                argv=prefix + suffix,
                cwd=context.workspace,
                timeout_seconds=900,
                evidence_path=self.evidence.path(f"deploy-{name}.log"),
            )
        )

    def run(self, context: RunContext) -> StageResult:
        prerequisite = self.evidence.read_stage_result("dependencies")
        if not prerequisite or prerequisite.get("success") is not True:
            gate_evidence = self.evidence.write_text(
                "deploy-dependency-gate.log",
                "stage=deploy\ntarget=dependencies\nstatus=missing-or-failed\naction=deploy not attempted",
            )
            result = StageResult(
                stage="deploy",
                success=False,
                diagnostics=(
                    Diagnostic(
                        stage="deploy",
                        code="DEPLOY_DEPENDENCY_GATE_FAILED",
                        target="dependencies",
                        reason="dependency assurance did not succeed",
                        observed="deploy was not attempted",
                        evidence=(str(gate_evidence),),
                        suggestion="Repair all dependency domains before deployment.",
                        rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
                    ),
                ),
            )
            self.evidence.write_stage_result("deploy", result)
            return result

        preflight = self.evidence.read_stage_result("preflight")
        baseline_ids = (
            (preflight or {}).get("details", {}).get("baseline_container_ids", {})
            if isinstance((preflight or {}).get("details", {}), dict)
            else {}
        )
        if not preflight or preflight.get("success") is not True or not all(
            baseline_ids.get(name) for name in ("jenkins", "mysql")
        ):
            gate_evidence = self.evidence.write_text(
                "deploy-preflight-gate.log",
                "stage=deploy\ntarget=preflight-baseline\nstatus=missing-or-invalid\naction=deploy not attempted",
            )
            result = StageResult(
                stage="deploy",
                success=False,
                diagnostics=(
                    Diagnostic(
                        stage="deploy",
                        code="DEPLOY_PREFLIGHT_BASELINE_MISSING",
                        target="preflight",
                        reason="Preflight bootstrap container baseline is missing",
                        observed="Deploy was not attempted",
                        evidence=(str(gate_evidence),),
                        suggestion="Rerun the complete Pipeline so Preflight can record Jenkins/MySQL IDs.",
                        rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap from Bootstrap Preflight.",
                    ),
                ),
            )
            self.evidence.write_stage_result("deploy", result)
            return result

        suffix = ("up", "-d", "--no-build")
        if context.build_all:
            suffix += ("--force-recreate",)
        deploy = self._command(context, "up", suffix + APPLICATION_SERVICES)
        if deploy.success:
            current_ids: dict[str, str] = {}
            id_evidence: list[str] = []
            for name, container in (
                ("jenkins", "aiapitest-jenkins"),
                ("mysql", "aiapitest-mysql"),
            ):
                inspected = self.runner.run(
                    CommandSpec(
                        argv=("docker", "inspect", "--format", "{{.Id}}", container),
                        cwd=context.workspace,
                        timeout_seconds=30,
                        evidence_path=self.evidence.path(f"deploy-{name}-id.log"),
                    )
                )
                id_evidence.append(inspected.evidence_path)
                current_ids[name] = inspected.redacted_output_tail.strip() if inspected.success else "unavailable"
            changed = [
                name for name in ("jenkins", "mysql") if current_ids[name] != baseline_ids[name]
            ]
            if changed:
                diagnostics = tuple(
                    Diagnostic(
                        stage="deploy",
                        code="DEPLOY_BOOTSTRAP_CONTAINER_CHANGED",
                        target=name,
                        reason="Bootstrap container ID changed during application deployment",
                        observed=f"before={baseline_ids[name]}; after={current_ids[name]}",
                        evidence=tuple(id_evidence),
                        suggestion="Inspect who changed the bootstrap container; no automatic recovery was attempted. Repair ownership, then rebuild.",
                        rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after Jenkins/MySQL are stable.",
                    )
                    for name in changed
                )
                result = StageResult(
                    stage="deploy",
                    success=False,
                    details={"baseline_container_ids": baseline_ids, "current_container_ids": current_ids},
                    diagnostics=diagnostics,
                )
                self.evidence.write_stage_result("deploy", result)
                return result
            result = StageResult(
                stage="deploy",
                success=True,
                details={
                    "services": list(APPLICATION_SERVICES),
                    "mode": "full" if context.build_all else "incremental",
                    "baseline_container_ids": baseline_ids,
                    "current_container_ids": current_ids,
                },
            )
            self.evidence.write_stage_result("deploy", result)
            return result

        ps = self._command(context, "ps", ("ps", *APPLICATION_SERVICES))
        logs = self._command(
            context,
            "logs",
            ("logs", "--no-color", "--tail", "300", *APPLICATION_SERVICES),
        )
        diagnostic = Diagnostic(
            stage="deploy",
            code="DEPLOY_SERVICE_FAILED",
            target=",".join(APPLICATION_SERVICES),
            reason="Compose application deployment failed",
            observed=f"exit={deploy.returncode}; {deploy.redacted_output_tail}",
            evidence=(deploy.evidence_path, ps.evidence_path, logs.evidence_path),
            suggestion="Inspect Compose status and application logs, repair the reported conflict/configuration, then rebuild.",
            rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
        )
        result = StageResult(stage="deploy", success=False, diagnostics=(diagnostic,))
        self.evidence.write_stage_result("deploy", result)
        return result
