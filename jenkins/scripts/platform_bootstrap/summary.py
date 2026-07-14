"""稳定汇总阶段结果、公开地址和可操作诊断。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .evidence import EvidenceStore
from .models import Diagnostic, RunContext


REQUIRED_ADDRESS_KEYS = (
    "JENKINS_PUBLIC_BASE_URL",
    "MYSQL_HOST",
    "MYSQL_HOST_PORT",
    "FRONTEND_SERVICE_URL",
    "BACKEND_SERVICE_URL",
    "BACKEND_API_BASE_URL",
)
REQUIRED_STAGES = ("preflight", "dependencies", "deploy", "health", "tests")


@dataclass(frozen=True)
class SummaryResult:
    success: bool
    addresses: Mapping[str, str]
    diagnostics: tuple[Diagnostic, ...]
    stages: tuple[Mapping[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "addresses": dict(self.addresses),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "stages": [dict(item) for item in self.stages],
        }


class SummaryService:
    def __init__(self, evidence: EvidenceStore):
        self.evidence = evidence

    def _addresses(self, context: RunContext, config: Mapping[str, str]) -> dict[str, str]:
        backend = config["BACKEND_SERVICE_URL"].rstrip("/")
        api_base = config["BACKEND_API_BASE_URL"].rstrip("/")
        frontend = config["FRONTEND_SERVICE_URL"].rstrip("/")
        build_url = context.build_url.rstrip("/") + "/"
        return {
            "jenkins": config["JENKINS_PUBLIC_BASE_URL"].rstrip("/"),
            "mysql": f"{config['MYSQL_HOST']}:{config['MYSQL_HOST_PORT']}",
            "frontend": frontend,
            "backend": backend,
            "api_docs": f"{backend}/api/docs/",
            "live": f"{api_base}/health/live/",
            "ready": f"{api_base}/health/ready/",
            "allure_or_artifacts": f"{build_url}artifact/",
        }

    def run(self, context: RunContext, config: Mapping[str, str]) -> SummaryResult:
        stages = tuple(self.evidence.read_stage_results())
        diagnostics: list[Diagnostic] = []
        for stage in stages:
            for value in stage.get("diagnostics", []):
                if isinstance(value, dict):
                    diagnostics.append(Diagnostic.from_dict(value))

        present_stages = {str(stage.get("stage")) for stage in stages}
        missing_stages = [stage for stage in REQUIRED_STAGES if stage not in present_stages]
        if missing_stages:
            diagnostics.append(
                Diagnostic(
                    stage="summary",
                    code="SUMMARY_REQUIRED_STAGE_MISSING",
                    target=",".join(missing_stages),
                    reason="One or more fixed Pipeline stage results are missing",
                    observed="missing stages: " + ",".join(missing_stages),
                    evidence=(str(self.evidence.root),),
                    suggestion="Inspect the primary Jenkins failure that interrupted stage result persistence, then rebuild.",
                    rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap from Checkout/Workspace.",
                )
            )

        missing = [key for key in REQUIRED_ADDRESS_KEYS if not config.get(key)]
        addresses: dict[str, str] = {}
        if missing:
            diagnostics.append(
                Diagnostic(
                    stage="summary",
                    code="CONFIG_REQUIRED_ENV_MISSING",
                    target=",".join(missing),
                    reason="required public address configuration is missing",
                    observed="missing keys only: " + ",".join(missing),
                    evidence=(str(context.env_file),),
                    suggestion="Add the listed public address keys to the private root .env, then rebuild.",
                    rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
                )
            )
        else:
            addresses = self._addresses(context, config)

        stages_success = (
            not missing_stages
            and all(stage.get("success") is True for stage in stages)
        )
        result = SummaryResult(
            success=stages_success and not diagnostics,
            addresses=addresses,
            diagnostics=tuple(diagnostics),
            stages=stages,
        )
        self.evidence.write_json("platform-bootstrap-summary.json", result.to_dict())
        self.evidence.write_json("platform-bootstrap-addresses.json", addresses)
        markdown = self._markdown(result)
        self.evidence.path("platform-bootstrap-summary.md").write_text(markdown, encoding="utf-8")
        return result

    @staticmethod
    def _markdown(result: SummaryResult) -> str:
        lines = ["# Platform Bootstrap Summary", "", f"Status: {'SUCCESS' if result.success else 'FAILURE'}", ""]
        if result.addresses:
            lines.extend(["## Addresses", ""])
            lines.extend(f"- {name}: {url}" for name, url in result.addresses.items())
            lines.append("")
        if result.diagnostics:
            lines.extend(["## Diagnostics", ""])
            for diagnostic in result.diagnostics:
                lines.append(
                    f"- [{diagnostic.code}] {diagnostic.target}: {diagnostic.reason}; "
                    f"suggestion={diagnostic.suggestion}; rerun={diagnostic.rerun}"
                )
            lines.append("")
        return "\n".join(lines) + "\n"
