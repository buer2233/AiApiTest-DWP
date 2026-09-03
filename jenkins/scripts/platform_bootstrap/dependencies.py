"""三域镜像 label、完整性和一次构建编排。"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .evidence import EvidenceStore
from .models import CommandSpec, Diagnostic, RunContext


LABEL_COMPONENT = "aiapitest.component"
LABEL_DEPENDENCY_HASH = "aiapitest.dependency-hash"
LABEL_BUILD_INPUT_HASH = "aiapitest.build-input-hash"
LABEL_SOURCE_REVISION = "aiapitest.source-revision"


@dataclass(frozen=True)
class ImageSpec:
    image: str
    component_label: str
    integrity_argv: tuple[str, ...]


@dataclass(frozen=True)
class DependencyDomainSpec:
    name: str
    bake_target: str
    workspace: Path
    dependency_inputs: tuple[Path, ...]
    build_inputs: tuple[Path, ...]
    images: tuple[ImageSpec, ...]


@dataclass(frozen=True)
class DependencyDomainResult:
    name: str
    dependency_status: str
    image_status: str
    build_attempts: int
    dependency_hash: str
    build_input_hash: str
    diagnostics: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "dependency_status": self.dependency_status,
            "image_status": self.image_status,
            "build_attempts": self.build_attempts,
            "dependency_hash": self.dependency_hash,
            "build_input_hash": self.build_input_hash,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass(frozen=True)
class DependencyAssuranceResult:
    stage: str
    success: bool
    domain_results: tuple[DependencyDomainResult, ...]
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "success": self.success,
            "domain_results": [item.to_dict() for item in self.domain_results],
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }


@dataclass
class DomainAuditState:
    phase: str = "initial"
    build_attempts: int = 0
    dependency_hash: str = "unknown"
    build_input_hash: str = "unknown"
    evidence: list[str] = field(default_factory=list)


IGNORED_PARTS = {
    ".git",
    ".planning",
    ".superpowers",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "runtime",
    "evidence",
    "report",
    "allure-report",
    "allure-results",
    "daily-control",
    "daily-workers",
    "logs",
    "dist",
    "test-results",
}
IGNORED_NAMES = {".env", ".dockerignore"}


def _iter_files(workspace: Path, inputs: Iterable[Path]) -> list[Path]:
    workspace = workspace.resolve()
    files: set[Path] = set()
    for input_path in inputs:
        candidate = input_path.resolve()
        if candidate != workspace and workspace not in candidate.parents:
            raise ValueError(f"hash input escapes workspace: {input_path}")
        if candidate.is_dir():
            for root, dirnames, filenames in os.walk(candidate, followlinks=False):
                # 原运行产物和虚拟环境目录不参与指纹，主动剪枝避免 Windows 挂载下扫描数万文件。
                dirnames[:] = [name for name in dirnames if name not in IGNORED_PARTS]
                for filename in filenames:
                    if filename in IGNORED_NAMES:
                        continue
                    path = Path(root) / filename
                    if path.is_symlink() or not path.is_file():
                        continue
                    relative = path.relative_to(workspace)
                    if any(part in IGNORED_PARTS for part in relative.parts):
                        continue
                    files.add(path)
        elif candidate.is_file() and not candidate.is_symlink():
            relative = candidate.relative_to(workspace)
            if candidate.name not in IGNORED_NAMES and not any(part in IGNORED_PARTS for part in relative.parts):
                files.add(candidate)
    return sorted(files, key=lambda item: item.relative_to(workspace).as_posix())


def _hash_paths(workspace: Path, inputs: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in _iter_files(workspace, inputs):
        relative = path.relative_to(workspace).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def compute_domain_hashes(domain: DependencyDomainSpec) -> tuple[str, str]:
    return (
        _hash_paths(domain.workspace, domain.dependency_inputs),
        _hash_paths(domain.workspace, domain.build_inputs),
    )


def default_domain_specs(workspace: Path) -> tuple[DependencyDomainSpec, ...]:
    workspace = workspace.resolve()
    return (
        DependencyDomainSpec(
            name="backend",
            bake_target="backend",
            workspace=workspace,
            dependency_inputs=(workspace / "back-end/Dockerfile", workspace / "back-end/requirements.txt"),
            build_inputs=(workspace / "back-end", workspace / "docker/healthchecks"),
            images=(
                ImageSpec(
                    "aiapitest-backend:local",
                    "backend",
                    ("docker", "run", "--rm", "aiapitest-backend:local", "python", "-m", "pip", "check"),
                ),
            ),
        ),
        DependencyDomainSpec(
            name="frontend",
            bake_target="frontend",
            workspace=workspace,
            dependency_inputs=(
                workspace / "front-end/Dockerfile",
                workspace / "front-end/package.json",
                workspace / "front-end/package-lock.json",
            ),
            build_inputs=(workspace / "front-end", workspace / "docker/nginx"),
            images=(
                ImageSpec("aiapitest-frontend:local", "frontend", ("docker", "image", "inspect", "aiapitest-frontend:local")),
                ImageSpec(
                    "aiapitest-frontend-test:local",
                    "frontend-test",
                    ("docker", "run", "--rm", "aiapitest-frontend-test:local", "npm", "ls", "--all"),
                ),
            ),
        ),
        DependencyDomainSpec(
            name="api-runner",
            bake_target="api-runner",
            workspace=workspace,
            dependency_inputs=(workspace / "api-test/Dockerfile", workspace / "api-test/requirements.txt"),
            build_inputs=(workspace,),
            images=(
                ImageSpec(
                    "aiapitest-api-runner:local",
                    "api-runner",
                    (
                        "docker",
                        "run",
                        "--rm",
                        "aiapitest-api-runner:local",
                        "python",
                        "-c",
                        "import subprocess; "
                        "subprocess.run(['python', '-m', 'pip', 'check'], check=True); "
                        "subprocess.run(['allure', '--version'], check=True)",
                    ),
                ),
            ),
        ),
    )


class DependencyAssuranceService:
    def __init__(self, runner, evidence: EvidenceStore):
        self.runner = runner
        self.evidence = evidence

    def _run(self, context: RunContext, name: str, argv: tuple[str, ...], env=None):
        return self.runner.run(
            CommandSpec(
                argv=argv,
                cwd=context.workspace,
                timeout_seconds=3600,
                evidence_path=self.evidence.path(name),
                env=env,
            )
        )

    def _inspect(self, context: RunContext, domain: DependencyDomainSpec) -> tuple[bool, list[dict[str, str]]]:
        labels: list[dict[str, str]] = []
        for image in domain.images:
            result = self._run(
                context,
                f"dependency-{domain.name}-inspect-{image.component_label}.log",
                ("docker", "image", "inspect", image.image, "--format", "{{json .Config.Labels}}"),
            )
            if not result.success:
                return False, []
            try:
                labels.append(json.loads(result.redacted_output_tail))
            except (json.JSONDecodeError, TypeError):
                return False, []
        return True, labels

    def _integrity(self, context: RunContext, domain: DependencyDomainSpec) -> bool:
        for image in domain.images:
            result = self._run(
                context,
                f"dependency-{domain.name}-integrity-{image.component_label}.log",
                image.integrity_argv,
            )
            if not result.success:
                return False
        return True

    def _failure(
        self,
        domain: DependencyDomainSpec,
        reason: str,
        evidence: tuple[str, ...],
    ) -> Diagnostic:
        actual_evidence = tuple(path for path in evidence if Path(path).is_file())
        if not actual_evidence:
            fallback = self.evidence.write_text(
                f"dependency-{domain.name}-failure.log",
                f"stage=dependencies\ntarget={domain.name}\nstatus=failed\nreason={reason}",
            )
            actual_evidence = (str(fallback),)
        return Diagnostic(
            stage="dependencies",
            code=f"DEPENDENCY_{domain.name.upper().replace('-', '_')}_INSTALL_FAILED",
            target=domain.name,
            reason=reason,
            observed="single protected image build failed",
            evidence=actual_evidence,
            suggestion="Inspect the complete build log, repair the image dependency/input, then rebuild the Jenkins job.",
            rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
        )

    def _run_domain(
        self,
        context: RunContext,
        domain: DependencyDomainSpec,
        audit: DomainAuditState,
    ) -> DependencyDomainResult:
        audit.phase = "hash-inputs"
        dependency_hash, build_hash = compute_domain_hashes(domain)
        audit.dependency_hash = dependency_hash
        audit.build_input_hash = build_hash
        audit.phase = "pre-build-inspect"
        inspected, labels = self._inspect(context, domain)
        labels_valid = inspected and all(
            label.get(LABEL_COMPONENT) == image.component_label
            and label.get(LABEL_DEPENDENCY_HASH) == dependency_hash
            and label.get(LABEL_BUILD_INPUT_HASH) == build_hash
            and label.get(LABEL_SOURCE_REVISION) == context.source_revision
            for label, image in zip(labels, domain.images)
        )
        audit.phase = "pre-build-integrity"
        integrity_ok = inspected and self._integrity(context, domain)
        if not context.build_all and labels_valid and integrity_ok:
            return DependencyDomainResult(
                domain.name, "SATISFIED", "REUSED", 0, dependency_hash, build_hash
            )

        previous_dependency_ok = inspected and all(
            label.get(LABEL_DEPENDENCY_HASH) == dependency_hash for label in labels
        ) and integrity_ok
        env_prefix = domain.name.upper().replace("-", "_")
        build_env = {
            f"{env_prefix}_DEPENDENCY_HASH": dependency_hash,
            f"{env_prefix}_BUILD_INPUT_HASH": build_hash,
            "AIAPITEST_SOURCE_REVISION": context.source_revision,
        }
        build_log = f"dependency-{domain.name}-build.log"
        audit.phase = "build"
        audit.build_attempts = 1
        intent = self.evidence.write_text(
            f"dependency-{domain.name}-build-intent.log",
            (
                f"stage=dependencies\ntarget={domain.name}\nphase=build\n"
                f"dependency_hash={dependency_hash}\nbuild_input_hash={build_hash}\n"
                "attempt=1"
            ),
        )
        audit.evidence.append(str(intent))
        build = self._run(
            context,
            build_log,
            (
                "docker",
                "buildx",
                "bake",
                "-f",
                str(context.workspace / "jenkins/scripts/platform-bootstrap-bake.hcl"),
                "--load",
                "--progress=plain",
                domain.bake_target,
            ),
            env=build_env,
        )
        if Path(build.evidence_path).is_file():
            audit.evidence.append(build.evidence_path)
        if not build.success:
            diagnostic = self._failure(
                domain,
                f"build exit code {build.returncode}",
                tuple(audit.evidence),
            )
            return DependencyDomainResult(
                domain.name,
                "INSTALL_FAILED",
                "BUILD_FAILED",
                1,
                dependency_hash,
                build_hash,
                (diagnostic,),
            )

        audit.phase = "post-build-hash"
        post_dependency_hash, post_build_hash = compute_domain_hashes(domain)
        audit.phase = "post-build-inspect"
        post_inspected, post_labels = self._inspect(context, domain)
        post_labels_valid = post_inspected and all(
            label.get(LABEL_COMPONENT) == image.component_label
            and label.get(LABEL_DEPENDENCY_HASH) == post_dependency_hash
            and label.get(LABEL_BUILD_INPUT_HASH) == post_build_hash
            and label.get(LABEL_SOURCE_REVISION) == context.source_revision
            for label, image in zip(post_labels, domain.images)
        )
        audit.phase = "post-build-integrity"
        post_integrity = post_inspected and self._integrity(context, domain)
        if post_dependency_hash != dependency_hash or post_build_hash != build_hash:
            diagnostic = self._failure(
                domain,
                "workspace changed during build",
                tuple(audit.evidence),
            )
        elif not post_labels_valid or not post_integrity:
            diagnostic = self._failure(
                domain,
                "post-build label or integrity verification failed",
                tuple(audit.evidence),
            )
        else:
            return DependencyDomainResult(
                domain.name,
                "SATISFIED" if previous_dependency_ok else "INSTALL_SUCCESS",
                "BUILD_SUCCESS",
                1,
                dependency_hash,
                build_hash,
            )
        return DependencyDomainResult(
            domain.name,
            "INSTALL_FAILED",
            "BUILD_FAILED",
            1,
            dependency_hash,
            build_hash,
            (diagnostic,),
        )

    def run(self, context: RunContext) -> DependencyAssuranceResult:
        preflight = self.evidence.read_stage_result("preflight")
        if not preflight or preflight.get("success") is not True:
            gate_evidence = self.evidence.write_text(
                "dependency-preflight-gate.log",
                "stage=dependencies\ntarget=preflight\nstatus=missing-or-failed\naction=no Docker command attempted",
            )
            diagnostic = Diagnostic(
                stage="dependencies",
                code="DEPENDENCY_PREFLIGHT_GATE_FAILED",
                target="preflight",
                reason="Bootstrap Preflight did not succeed",
                observed="No image inspect, integrity check, or build was attempted",
                evidence=(str(gate_evidence),),
                suggestion="Resolve the preflight diagnostics, then rebuild the environment Job.",
                rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after preflight succeeds.",
            )
            result = DependencyAssuranceResult(
                stage="dependencies",
                success=False,
                domain_results=(),
                diagnostics=(diagnostic,),
            )
            self.evidence.write_stage_result("dependencies", result)
            return result

        results: list[DependencyDomainResult] = []
        diagnostics: list[Diagnostic] = []
        for domain in default_domain_specs(context.workspace):
            audit = DomainAuditState()
            try:
                domain_result = self._run_domain(context, domain, audit)
            except Exception as exc:
                evidence_path = self.evidence.path(f"dependency-{domain.name}-exception.log")
                observed = self.evidence.redactor.text(
                    f"phase={audit.phase}; {type(exc).__name__}: {exc}"
                )
                evidence_path.write_text(observed + "\n", encoding="utf-8")
                diagnostic = Diagnostic(
                    stage="dependencies",
                    code=f"DEPENDENCY_{domain.name.upper().replace('-', '_')}_INSTALL_FAILED",
                    target=domain.name,
                    reason="Unexpected dependency-domain exception",
                    observed=observed,
                    evidence=(
                        str(evidence_path),
                        *(path for path in audit.evidence if Path(path).is_file()),
                    ),
                    suggestion="Inspect the domain exception evidence, repair the input/runner failure, then rebuild.",
                    rerun="Rebuild AiApiTest-DWP-Platform-Bootstrap after the issue is resolved.",
                )
                domain_result = DependencyDomainResult(
                    domain.name,
                    "INSTALL_FAILED",
                    "BUILD_FAILED",
                    audit.build_attempts,
                    audit.dependency_hash,
                    audit.build_input_hash,
                    (diagnostic,),
                )
            results.append(domain_result)
            diagnostics.extend(domain_result.diagnostics)

        result = DependencyAssuranceResult(
            stage="dependencies",
            success=not diagnostics,
            domain_results=tuple(results),
            diagnostics=tuple(diagnostics),
        )
        self.evidence.write_stage_result("dependencies", result)
        return result
