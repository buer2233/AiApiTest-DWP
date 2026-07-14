"""Stage13 Task 3A 三域不可变依赖编排测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.dependencies import (  # noqa: E402
    DependencyAssuranceService,
    compute_domain_hashes,
    default_domain_specs,
)
from platform_bootstrap.evidence import EvidenceStore  # noqa: E402
from platform_bootstrap.models import CommandResult, RunContext  # noqa: E402


class DependencyRunner:
    def __init__(
        self,
        labels,
        build_failures=(),
        raise_images=(),
        raise_after_build_images=(),
        raise_build_targets=(),
    ):
        self.labels = dict(labels)
        self.build_failures = set(build_failures)
        self.raise_images = set(raise_images)
        self.raise_after_build_images = set(raise_after_build_images)
        self.raise_build_targets = set(raise_build_targets)
        self.completed_build_targets = set()
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        argv = tuple(spec.argv)
        if argv[:3] == ("docker", "image", "inspect"):
            image = argv[3]
            if image in self.raise_images or (
                image in self.raise_after_build_images and self.completed_build_targets
            ):
                raise RuntimeError(f"inspect exploded: {image}")
            if image not in self.labels:
                return CommandResult.from_output(1, "No such image", spec.evidence_path)
            return CommandResult.from_output(
                0, json.dumps(self.labels[image]), spec.evidence_path
            )
        if argv[:3] == ("docker", "buildx", "bake"):
            target = argv[-1]
            if target in self.raise_build_targets:
                raise RuntimeError(f"build launch exploded: {target}")
            if target in self.build_failures:
                return CommandResult.from_output(17, f"build failed: {target}", spec.evidence_path)
            domain = {"backend": "backend", "frontend": "frontend", "api-runner": "api-runner"}[target]
            dependency_hash = spec.env[f"{domain.upper().replace('-', '_')}_DEPENDENCY_HASH"]
            build_hash = spec.env[f"{domain.upper().replace('-', '_')}_BUILD_INPUT_HASH"]
            revision = spec.env["AIAPITEST_SOURCE_REVISION"]
            for image, component in {
                "backend": [("aiapitest-backend:local", "backend")],
                "frontend": [
                    ("aiapitest-frontend:local", "frontend"),
                    ("aiapitest-frontend-test:local", "frontend-test"),
                ],
                "api-runner": [("aiapitest-api-runner:local", "api-runner")],
            }[domain]:
                self.labels[image] = {
                    "aiapitest.component": component,
                    "aiapitest.dependency-hash": dependency_hash,
                    "aiapitest.build-input-hash": build_hash,
                    "aiapitest.source-revision": revision,
                }
            self.completed_build_targets.add(target)
            return CommandResult.from_output(0, "build ok", spec.evidence_path)
        return CommandResult.from_output(0, "integrity ok", spec.evidence_path)


def make_workspace(tmp_path: Path):
    files = {
        "back-end/Dockerfile": "FROM python:3.12-slim\nCOPY back-end/ /app\n",
        "back-end/requirements.txt": "Django==5.2.4\n",
        "back-end/app.py": "print('backend')\n",
        "docker/healthchecks/worker_heartbeat_healthcheck.py": "print('health')\n",
        "front-end/Dockerfile": "FROM node:22\nCOPY front-end/ /app\n",
        "front-end/package.json": "{}\n",
        "front-end/package-lock.json": "{}\n",
        "front-end/src/main.ts": "export {}\n",
        "docker/nginx/default.conf": "location / {}\n",
        "api-test/Dockerfile": "FROM python:3.12-slim\nCOPY . /workspace\n",
        "api-test/requirements.txt": "pytest==8.4.1\n",
        "api-test/tests/test_sample.py": "def test_ok(): assert True\n",
        ".dockerignore": ".env\nruntime\n",
        "docker-compose.yml": "name: aiapitest-dwp\nservices: {}\n",
        ".env": "PLACEHOLDER=value\n",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def make_context(tmp_path: Path, build_all=False):
    return RunContext.create(
        workspace=tmp_path,
        evidence_dir=tmp_path / "evidence",
        build_id="dependency-unit",
        build_url="https://jenkins.example.invalid/job/1/",
        build_all=build_all,
        run_full_tests=False,
        source_revision="unit-revision",
    )


def valid_labels(context):
    labels = {}
    for domain in default_domain_specs(context.workspace):
        dependency_hash, build_hash = compute_domain_hashes(domain)
        for image in domain.images:
            labels[image.image] = {
                "aiapitest.component": image.component_label,
                "aiapitest.dependency-hash": dependency_hash,
                "aiapitest.build-input-hash": build_hash,
                "aiapitest.source-revision": context.source_revision,
            }
    return labels


def ready_store(context):
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result("preflight", {"stage": "preflight", "success": True})
    return store


def test_incremental_reuses_three_satisfied_domains_without_build(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path)
    runner = DependencyRunner(valid_labels(context))

    result = DependencyAssuranceService(
        runner, ready_store(context)
    ).run(context)

    assert result.success is True
    assert [(item.name, item.dependency_status, item.image_status, item.build_attempts) for item in result.domain_results] == [
        ("backend", "SATISFIED", "REUSED", 0),
        ("frontend", "SATISFIED", "REUSED", 0),
        ("api-runner", "SATISFIED", "REUSED", 0),
    ]
    assert not any(spec.argv[:3] == ("docker", "buildx", "bake") for spec in runner.specs)


def test_full_build_invokes_each_domain_once_and_never_no_cache(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path, build_all=True)
    runner = DependencyRunner(valid_labels(context))

    result = DependencyAssuranceService(
        runner, ready_store(context)
    ).run(context)

    builds = [spec for spec in runner.specs if spec.argv[:3] == ("docker", "buildx", "bake")]
    assert result.success is True
    assert [spec.argv[-1] for spec in builds] == ["backend", "frontend", "api-runner"]
    assert all(item.build_attempts == 1 for item in result.domain_results)
    assert "--no-cache" not in " ".join(" ".join(spec.argv) for spec in builds)


def test_build_failures_are_aggregated_and_other_domains_continue(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path)
    runner = DependencyRunner({}, build_failures={"backend", "frontend"})

    result = DependencyAssuranceService(
        runner, ready_store(context)
    ).run(context)

    assert result.success is False
    assert [item.name for item in result.domain_results] == ["backend", "frontend", "api-runner"]
    assert [item.build_attempts for item in result.domain_results] == [1, 1, 1]
    assert [item.dependency_status for item in result.domain_results] == [
        "INSTALL_FAILED",
        "INSTALL_FAILED",
        "INSTALL_SUCCESS",
    ]
    assert len([spec for spec in runner.specs if spec.argv[:3] == ("docker", "buildx", "bake")]) == 3


def test_source_only_change_builds_once_but_does_not_report_install(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path)
    labels = valid_labels(context)
    labels["aiapitest-backend:local"]["aiapitest.build-input-hash"] = "old-source-hash"
    runner = DependencyRunner(labels)

    result = DependencyAssuranceService(
        runner, ready_store(context)
    ).run(context)

    backend = result.domain_results[0]
    assert backend.dependency_status == "SATISFIED"
    assert backend.image_status == "BUILD_SUCCESS"
    assert backend.build_attempts == 1


def test_bake_frontend_is_one_group_and_api_integrity_checks_pip_and_allure(tmp_path):
    make_workspace(tmp_path)
    bake_file = SCRIPTS_DIR / "platform-bootstrap-bake.hcl"
    bake = bake_file.read_text(encoding="utf-8")
    assert 'group "frontend"' in bake
    assert 'targets = ["frontend-runtime", "frontend-test"]' in bake

    api_runner = default_domain_specs(tmp_path)[2].images[0]
    integrity = " ".join(api_runner.integrity_argv)
    assert "pip" in integrity and "check" in integrity
    assert "allure" in integrity and "--version" in integrity


def test_dependencies_require_successful_preflight_before_any_docker_command(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path)
    runner = DependencyRunner(valid_labels(context))

    result = DependencyAssuranceService(
        runner, EvidenceStore(context.evidence_dir)
    ).run(context)

    assert result.success is False
    assert runner.specs == []
    assert result.diagnostics[0].target == "preflight"
    assert result.diagnostics[0].code
    assert all(Path(path).is_file() for path in result.diagnostics[0].evidence)


def test_domain_exception_becomes_install_failed_and_remaining_domains_continue(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path)
    runner = DependencyRunner(
        valid_labels(context),
        raise_images={"aiapitest-backend:local"},
    )

    result = DependencyAssuranceService(runner, ready_store(context)).run(context)

    assert result.success is False
    assert [item.name for item in result.domain_results] == ["backend", "frontend", "api-runner"]
    assert result.domain_results[0].dependency_status == "INSTALL_FAILED"
    assert result.domain_results[0].image_status == "BUILD_FAILED"
    assert result.domain_results[0].diagnostics[0].observed
    assert result.domain_results[1].dependency_status == "SATISFIED"
    assert result.domain_results[2].dependency_status == "SATISFIED"


def test_post_build_exception_keeps_one_attempt_hashes_phase_and_build_evidence(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path)
    labels = valid_labels(context)
    labels["aiapitest-backend:local"]["aiapitest.build-input-hash"] = "old-build-input"
    runner = DependencyRunner(
        labels,
        raise_after_build_images={"aiapitest-backend:local"},
    )

    result = DependencyAssuranceService(runner, ready_store(context)).run(context)

    backend = result.domain_results[0]
    assert result.success is False
    assert backend.build_attempts == 1
    assert backend.dependency_hash != "unknown"
    assert backend.build_input_hash != "unknown"
    diagnostic = backend.diagnostics[0]
    assert "post" in diagnostic.observed.lower()
    assert any("dependency-backend-build-intent.log" in path for path in diagnostic.evidence)
    assert all(Path(path).is_file() for path in diagnostic.evidence)
    assert result.domain_results[1].name == "frontend"
    assert result.domain_results[2].name == "api-runner"


def test_build_launch_exception_uses_real_intent_evidence_and_keeps_audit(tmp_path):
    make_workspace(tmp_path)
    context = make_context(tmp_path)
    labels = valid_labels(context)
    labels["aiapitest-backend:local"]["aiapitest.build-input-hash"] = "old-build-input"
    runner = DependencyRunner(labels, raise_build_targets={"backend"})

    result = DependencyAssuranceService(runner, ready_store(context)).run(context)

    backend = result.domain_results[0]
    assert backend.build_attempts == 1
    assert backend.dependency_hash != "unknown"
    assert backend.build_input_hash != "unknown"
    assert "phase=build" in backend.diagnostics[0].observed
    assert backend.diagnostics[0].evidence
    assert all(Path(path).is_file() for path in backend.diagnostics[0].evidence)
    assert any("build-intent" in Path(path).name for path in backend.diagnostics[0].evidence)
    assert all(Path(path).name != "dependency-backend-build.log" for path in backend.diagnostics[0].evidence)
    assert [item.name for item in result.domain_results] == ["backend", "frontend", "api-runner"]
