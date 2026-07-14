"""平台环境编排使用的不可变数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Diagnostic:
    stage: str
    code: str
    target: str
    reason: str
    observed: str
    evidence: tuple[str, ...]
    suggestion: str
    rerun: str

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "code": self.code,
            "target": self.target,
            "reason": self.reason,
            "observed": self.observed,
            "evidence": list(self.evidence),
            "suggestion": self.suggestion,
            "rerun": self.rerun,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "Diagnostic":
        return cls(
            stage=str(value.get("stage", "unknown")),
            code=str(value.get("code", "UNKNOWN_FAILURE")),
            target=str(value.get("target", "unknown")),
            reason=str(value.get("reason", "unknown")),
            observed=str(value.get("observed", "unknown")),
            evidence=tuple(str(item) for item in value.get("evidence", [])),
            suggestion=str(value.get("suggestion", "inspect evidence")),
            rerun=str(value.get("rerun", "rebuild the Jenkins job")),
        )


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: Path
    timeout_seconds: int
    evidence_path: Path
    env: Mapping[str, str] | None = None


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    duration_seconds: float
    timed_out: bool
    redacted_output_tail: str
    evidence_path: str

    @classmethod
    def from_output(
        cls,
        returncode: int,
        output: str,
        evidence_path: Path,
        *,
        timed_out: bool = False,
        duration_seconds: float = 0.0,
    ) -> "CommandResult":
        return cls(
            returncode=returncode,
            duration_seconds=duration_seconds,
            timed_out=timed_out,
            redacted_output_tail=output,
            evidence_path=str(evidence_path),
        )

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict[str, object]:
        return {
            "returncode": self.returncode,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "redacted_output_tail": self.redacted_output_tail,
            "evidence_path": self.evidence_path,
        }


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes | None = None
    timeout_seconds: int = 10


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class RunContext:
    workspace: Path
    env_file: Path
    compose_file: Path
    evidence_dir: Path
    build_id: str
    build_url: str
    build_all: bool
    run_full_tests: bool
    source_revision: str

    @classmethod
    def create(
        cls,
        *,
        workspace: Path,
        evidence_dir: Path,
        build_id: str,
        build_url: str,
        build_all: bool,
        run_full_tests: bool,
        source_revision: str = "unknown",
    ) -> "RunContext":
        resolved_workspace = workspace.resolve()
        resolved_evidence = evidence_dir.resolve()
        if resolved_workspace not in resolved_evidence.parents and resolved_evidence != resolved_workspace:
            raise ValueError("evidence directory must stay inside workspace")
        return cls(
            workspace=resolved_workspace,
            env_file=resolved_workspace / ".env",
            compose_file=resolved_workspace / "docker-compose.yml",
            evidence_dir=resolved_evidence,
            build_id=build_id,
            build_url=build_url,
            build_all=build_all,
            run_full_tests=run_full_tests,
            source_revision=source_revision,
        )


@dataclass(frozen=True)
class StageResult:
    stage: str
    success: bool
    details: Mapping[str, object] = field(default_factory=dict)
    diagnostics: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "success": self.success,
            "details": dict(self.details),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }
