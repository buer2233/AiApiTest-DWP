"""稳定汇总阶段结果、公开地址和可操作诊断。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .addressing import PUBLIC_ADDRESS_KEYS, derive_public_addresses
from .configuration import ConfigError
from .evidence import EvidenceStore
from .models import Diagnostic, RunContext


REQUIRED_ADDRESS_KEYS = PUBLIC_ADDRESS_KEYS
REQUIRED_STAGES = (
    "preflight",
    "dependencies",
    "schema-initialization",
    "deploy",
    "health",
    "tests",
)


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
        public = derive_public_addresses(config)
        build_url = context.build_url.rstrip("/") + "/"
        return {
            "jenkins": public.jenkins,
            "mysql": public.mysql,
            "frontend": public.frontend,
            "backend": public.backend,
            "api_docs": f"{public.backend}/api/docs/",
            "live": f"{public.backend_api}/health/live/",
            "ready": f"{public.backend_api}/health/ready/",
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
            try:
                addresses = self._addresses(context, config)
            except ConfigError as exc:
                diagnostics.append(
                    Diagnostic(
                        stage="summary",
                        code="CONFIG_ENV_VALUE_INVALID",
                        target="public-address",
                        reason="public address configuration is invalid",
                        observed=str(exc),
                        evidence=(str(context.env_file),),
                        suggestion="Correct the listed public address key, then rebuild.",
                        rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
                    )
                )

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
