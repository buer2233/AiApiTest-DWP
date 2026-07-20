"""Stage13 F5 Schema & Initial Data 受控初始化测试。"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "jenkins" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.evidence import EvidenceStore  # noqa: E402
from platform_bootstrap.models import CommandResult, RunContext  # noqa: E402
from platform_bootstrap.security import Redactor  # noqa: E402


def schema_initialization_service():
    """延迟导入以确认 RED 阶段失败源于服务尚未实现。"""
    try:
        module = importlib.import_module("platform_bootstrap.schema_initialization")
    except ImportError as exc:
        pytest.fail(f"SchemaInitializationService 尚未实现：{exc}")
    return module.SchemaInitializationService


class SchemaRunner:
    def __init__(self, failures: tuple[int, ...] = (), output: str = "ok"):
        self.failures = set(failures)
        self.output = output
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        spec.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        spec.evidence_path.write_text(self.output, encoding="utf-8")
        return CommandResult.from_output(
            17 if len(self.specs) in self.failures else 0,
            self.output,
            spec.evidence_path,
        )


def make_context(tmp_path: Path) -> RunContext:
    (tmp_path / "docker-compose.yml").write_text("name: aiapitest-dwp\n", encoding="utf-8")
    (tmp_path / ".env").write_text("KEY=value\n", encoding="utf-8")
    return RunContext.create(
        workspace=tmp_path,
        evidence_dir=tmp_path / "evidence",
        build_id="schema-initialization-unit",
        build_url="https://jenkins.example.invalid/job/Platform/13/",
        build_all=False,
        run_full_tests=False,
    )


def mark_dependencies_ready(store: EvidenceStore) -> None:
    store.write_stage_result("dependencies", {"stage": "dependencies", "success": True})


def test_schema_initialization_uses_fixed_compose_argv_in_required_order(tmp_path):
    context = make_context(tmp_path)
    store = EvidenceStore(context.evidence_dir)
    mark_dependencies_ready(store)
    runner = SchemaRunner()

    result = schema_initialization_service()(runner, store).run(context)

    prefix = (
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
    assert result.success is True
    assert [spec.argv for spec in runner.specs] == [
        prefix + ("migrate", "--noinput"),
        prefix + ("seed_environment",),
        prefix + ("init_admin", "--bootstrap-only"),
    ]
    assert (context.evidence_dir / "schema-initialization.json").is_file()


def test_schema_initialization_failure_short_circuits_without_sensitive_evidence(tmp_path):
    context = make_context(tmp_path)
    secret = "SyntheticAdminPassword123"
    store = EvidenceStore(context.evidence_dir, Redactor(extra_secrets=(secret,)))
    mark_dependencies_ready(store)
    runner = SchemaRunner(failures=(2,), output=f"password={secret}")

    result = schema_initialization_service()(runner, store).run(context)

    payload = (context.evidence_dir / "schema-initialization.json").read_text(encoding="utf-8")
    assert result.success is False
    assert len(runner.specs) == 2
    assert result.diagnostics[0].code == "SCHEMA_INITIALIZATION_COMMAND_FAILED"
    assert secret not in json.dumps(result.to_dict())
    assert secret not in payload
    assert json.loads(payload)["details"]["completed_steps"] == ["migrate"]


def test_schema_initialization_requires_successful_dependencies_before_any_command(tmp_path):
    context = make_context(tmp_path)
    runner = SchemaRunner()

    result = schema_initialization_service()(runner, EvidenceStore(context.evidence_dir)).run(context)

    assert result.success is False
    assert result.diagnostics[0].code == "SCHEMA_INITIALIZATION_DEPENDENCY_GATE_FAILED"
    assert runner.specs == []


def test_deploy_requires_successful_schema_initialization_before_any_compose_command(tmp_path):
    from platform_bootstrap.deploy import DeployService

    context = make_context(tmp_path)
    store = EvidenceStore(context.evidence_dir)
    mark_dependencies_ready(store)
    store.write_stage_result(
        "preflight",
        {
            "stage": "preflight",
            "success": True,
            "details": {
                "baseline_container_ids": {"jenkins": "jenkins-id", "mysql": "mysql-id"}
            },
        },
    )
    runner = SchemaRunner()

    result = DeployService(runner, store).run(context)

    assert result.success is False
    assert result.diagnostics[0].code == "DEPLOY_SCHEMA_INITIALIZATION_GATE_FAILED"
    assert runner.specs == []


def test_cli_dispatches_schema_initialization_service(tmp_path, monkeypatch):
    import platform_bootstrap.cli as cli

    context = make_context(tmp_path)
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_WORKSPACE", str(context.workspace))
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_EVIDENCE_DIR", str(context.evidence_dir))
    calls = []

    class SuccessfulService:
        def __init__(self, runner, evidence):
            calls.append((runner, evidence))

        def run(self, received_context):
            calls.append(received_context)
            return type("Result", (), {"success": True})()

    monkeypatch.setattr(cli, "SchemaInitializationService", SuccessfulService, raising=False)

    assert cli.run_stage("schema-initialization") == 0
    assert calls[-1].build_id == "manual"


def test_compose_declares_one_shot_backend_bootstrap_outside_application_services():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    deploy = (ROOT / "jenkins" / "scripts" / "platform_bootstrap" / "deploy.py").read_text(
        encoding="utf-8"
    )

    assert "backend-bootstrap:" in compose
    bootstrap = compose[compose.index("  backend-bootstrap:") : compose.index("  frontend:")]
    assert "image: aiapitest-backend:local" in bootstrap
    assert 'profiles: ["bootstrap"]' in bootstrap
    assert "INITIAL_ADMIN_USERNAME: ${INITIAL_ADMIN_USERNAME:-}" in bootstrap
    assert "INITIAL_ADMIN_DISPLAY_NAME: ${INITIAL_ADMIN_DISPLAY_NAME:-}" in bootstrap
    assert "INITIAL_ADMIN_PASSWORD: ${INITIAL_ADMIN_PASSWORD:-}" in bootstrap
    for forbidden in ["ports:", "volumes:", "container_name:", "healthcheck:", "depends_on:", "restart:"]:
        assert forbidden not in bootstrap
    assert "backend-bootstrap" not in deploy
