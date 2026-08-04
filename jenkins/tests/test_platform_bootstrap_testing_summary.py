"""Stage13 Task 3A 测试计划与摘要测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.evidence import EvidenceStore  # noqa: E402
from platform_bootstrap.models import CommandResult, HttpResponse, RunContext  # noqa: E402
from platform_bootstrap.summary import SummaryService  # noqa: E402
from platform_bootstrap.testing import TestService  # noqa: E402


class FakeRunner:
    def __init__(self, fail_copy=False, fail_cleanup=False):
        self.fail_copy = fail_copy
        self.fail_cleanup = fail_cleanup
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        copy_failed = self.fail_copy and spec.argv[:2] == ("docker", "cp")
        cleanup_failed = self.fail_cleanup and spec.argv[:2] == ("docker", "rm")
        return CommandResult.from_output(
            31 if copy_failed else (32 if cleanup_failed else 0),
            "copy failed" if copy_failed else ("cleanup failed" if cleanup_failed else "ok"),
            spec.evidence_path,
        )


class FakeHttpClient:
    def __init__(self, status=200):
        self.status = status
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return HttpResponse(status=self.status, headers={}, body=b"ok")


def make_context(tmp_path, run_full_tests=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docker-compose.yml").write_text("name: aiapitest-dwp\n", encoding="utf-8")
    (tmp_path / ".env").write_text("KEY=value\n", encoding="utf-8")
    return RunContext.create(
        workspace=tmp_path,
        evidence_dir=tmp_path / "evidence",
        build_id="testing-summary-unit",
        build_url="https://jenkins.example.invalid/job/Platform/7/",
        build_all=False,
        run_full_tests=run_full_tests,
    )


def test_default_test_plan_is_credential_free_smoke_only(tmp_path):
    context = make_context(tmp_path)
    plan = TestService.build_plan(context)

    assert plan.mode == "smoke"
    assert plan.commands == ()
    assert {probe.name for probe in plan.http_probes} >= {
        "backend-live",
        "backend-ready",
        "frontend-health",
        "frontend-spa",
        "frontend-api-proxy",
        "api-docs",
    }
    serialized = json.dumps(plan.to_dict())
    for forbidden in ["username", "password", "token", "cookie", "authorization"]:
        assert forbidden not in serialized.lower()


def test_full_test_plan_uses_three_verified_images_without_runtime_install(tmp_path):
    context = make_context(tmp_path, run_full_tests=True)
    plan = TestService.build_plan(context)

    assert plan.mode == "full"
    serialized = "\n".join(" ".join(command.argv) for command in plan.commands)
    for image in [
        "aiapitest-backend:local",
        "aiapitest-frontend-test:local",
        "aiapitest-api-runner:local",
    ]:
        assert image in serialized
    for expected in [
        "python -m pytest tests",
        "npm run test:unit",
        "npm run build",
        "npm run test:e2e",
        "api-test/tests",
        "jenkins/tests",
    ]:
        assert expected in serialized
    for forbidden in [
        "pip install",
        "npm install",
        "npm ci",
        "npx playwright install",
        "api-test/test_case",
        "down",
        "stop",
    ]:
        assert forbidden not in serialized
    assert serialized.count("/tmp/platform-bootstrap-evidence") >= len(plan.commands)
    assert serialized.count("--network aiapitest-platform") == len(plan.commands)

    frontend_playwright = next(command for command in plan.commands if command.name == "frontend-playwright")
    assert "--env" in frontend_playwright.argv
    assert "CI=true" in frontend_playwright.argv
    assert all("FRONTEND_DEV_API_PROXY_TARGET" not in item for item in frontend_playwright.argv)


def test_test_service_executes_smoke_with_fake_http_and_full_with_fake_runner(tmp_path):
    smoke_context = make_context(tmp_path / "smoke")
    smoke_store = EvidenceStore(smoke_context.evidence_dir)
    smoke_store.write_stage_result("health", {"stage": "health", "success": True})
    smoke_http = FakeHttpClient()
    smoke_result = TestService(FakeRunner(), smoke_http, smoke_store).run(
        smoke_context,
        {
            "BACKEND_SERVICE_URL": "https://api.example.invalid",
            "FRONTEND_SERVICE_URL": "https://platform.example.invalid",
        },
    )
    assert smoke_result.success is True
    assert len(smoke_http.requests) == 6
    assert [request.url for request in smoke_http.requests] == [
        "http://backend:8000/api/v1/health/live/",
        "http://backend:8000/api/v1/health/ready/",
        "http://frontend/health",
        "http://frontend/login",
        "http://frontend/api/v1/health/ready/",
        "http://backend:8000/api/docs/",
    ]
    for name in [
        "backend-live",
        "backend-ready",
        "frontend-health",
        "frontend-spa",
        "frontend-api-proxy",
        "api-docs",
    ]:
        evidence = smoke_context.evidence_dir / f"test-smoke-{name}.log"
        assert evidence.is_file()
        assert "status=200" in evidence.read_text(encoding="utf-8")

    full_context = make_context(tmp_path / "full", run_full_tests=True)
    full_store = EvidenceStore(full_context.evidence_dir)
    full_store.write_stage_result("health", {"stage": "health", "success": True})
    full_runner = FakeRunner()
    full_result = TestService(full_runner, FakeHttpClient(), full_store).run(
        full_context,
        {
            "BACKEND_SERVICE_URL": "https://api.example.invalid",
            "FRONTEND_SERVICE_URL": "https://platform.example.invalid",
        },
    )
    assert full_result.success is True
    commands = [spec.argv for spec in full_runner.specs]
    assert len([argv for argv in commands if argv[:2] == ("docker", "create")]) == 5
    assert len([argv for argv in commands if argv[:2] == ("docker", "start")]) == 5
    assert len([argv for argv in commands if argv[:2] == ("docker", "cp")]) == 5
    assert len([argv for argv in commands if argv[:2] == ("docker", "rm")]) == 5


def test_full_test_evidence_copy_failure_preserves_test_container(tmp_path):
    context = make_context(tmp_path, run_full_tests=True)
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result("health", {"stage": "health", "success": True})
    runner = FakeRunner(fail_copy=True)

    result = TestService(runner, FakeHttpClient(), store).run(
        context,
        {
            "BACKEND_SERVICE_URL": "https://api.example.invalid",
            "FRONTEND_SERVICE_URL": "https://platform.example.invalid",
        },
    )

    assert result.success is False
    created = [argv[3] for argv in (spec.argv for spec in runner.specs) if argv[:2] == ("docker", "create")]
    removed = [argv[-1] for argv in (spec.argv for spec in runner.specs) if argv[:2] == ("docker", "rm")]
    assert created
    assert removed == []
    assert any("manual" in diagnostic.suggestion.lower() for diagnostic in result.diagnostics)


def test_smoke_failure_writes_real_http_evidence(tmp_path):
    context = make_context(tmp_path)
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result("health", {"stage": "health", "success": True})

    result = TestService(FakeRunner(), FakeHttpClient(status=503), store).run(context, {})

    assert result.success is False
    for diagnostic in result.diagnostics:
        assert diagnostic.evidence
        evidence = Path(diagnostic.evidence[0])
        assert evidence.is_file()
        assert "status=503" in evidence.read_text(encoding="utf-8")


def test_full_backend_uses_test_settings_and_cleanup_failure_is_structured(tmp_path):
    context = make_context(tmp_path, run_full_tests=True)
    plan = TestService.build_plan(context)
    backend = plan.commands[0].argv
    assert "--env" in backend
    assert "DJANGO_SETTINGS_MODULE=config.settings.test" in backend

    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result("health", {"stage": "health", "success": True})
    runner = FakeRunner(fail_cleanup=True)
    result = TestService(runner, FakeHttpClient(), store).run(context, {})

    assert result.success is False
    cleanup_diagnostics = [item for item in result.diagnostics if "CLEANUP" in item.code]
    assert cleanup_diagnostics
    assert "platform-bootstrap-" in cleanup_diagnostics[0].observed
    assert "manual" in cleanup_diagnostics[0].suggestion.lower()


def test_missing_health_gate_creates_real_evidence_file(tmp_path):
    context = make_context(tmp_path)
    result = TestService(
        FakeRunner(),
        FakeHttpClient(),
        EvidenceStore(context.evidence_dir),
    ).run(context, {})

    assert result.success is False
    assert result.diagnostics[0].evidence
    assert all(Path(path).is_file() for path in result.diagnostics[0].evidence)


def test_success_summary_contains_public_addresses_and_build_artifact_links(tmp_path):
    context = make_context(tmp_path)
    store = EvidenceStore(context.evidence_dir)
    for stage in [
        "preflight",
        "dependencies",
        "schema-initialization",
        "deploy",
        "health",
        "tests",
    ]:
        store.write_stage_result(stage, {"stage": stage, "success": True})
    config = {
        "PLATFORM_PUBLIC_HOST": "platform.example.invalid",
        "PLATFORM_PUBLIC_SCHEME": "https",
        "MYSQL_HOST_PORT": "3307",
        "JENKINS_HTTP_PORT": "8443",
        "BACKEND_HOST_PORT": "8000",
        "FRONTEND_HOST_PORT": "5173",
    }

    result = SummaryService(store).run(context, config)

    assert result.success is True
    assert set(result.addresses) == {
        "jenkins",
        "mysql",
        "frontend",
        "backend",
        "api_docs",
        "live",
        "ready",
        "allure_or_artifacts",
    }
    assert result.addresses["allure_or_artifacts"].startswith(context.build_url)
    assert result.addresses["jenkins"] == "https://platform.example.invalid:8443"
    assert result.addresses["backend"] == "https://platform.example.invalid:8000"
    assert result.addresses["frontend"] == "https://platform.example.invalid:5173"
    assert (context.evidence_dir / "platform-bootstrap-summary.json").exists()
    assert (context.evidence_dir / "platform-bootstrap-summary.md").exists()
    assert (context.evidence_dir / "platform-bootstrap-addresses.json").exists()


def test_summary_reports_missing_address_without_localhost_fallback(tmp_path):
    context = make_context(tmp_path)
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result(
        "preflight",
        {
            "stage": "preflight",
            "success": False,
            "diagnostics": [
                {
                    "stage": "preflight",
                    "code": "FIRST_FAILURE",
                    "target": "docker",
                    "reason": "unavailable",
                    "observed": "exit 1",
                    "evidence": ["preflight.log"],
                    "suggestion": "repair Docker",
                    "rerun": "rebuild the Jenkins job",
                }
            ],
        },
    )
    config = {
        "JENKINS_PUBLIC_BASE_URL": "https://jenkins.example.invalid",
        "MYSQL_HOST": "db.example.invalid",
        "MYSQL_HOST_PORT": "3307",
    }

    result = SummaryService(store).run(context, config)

    codes = [diagnostic.code for diagnostic in result.diagnostics]
    assert result.success is False
    assert codes[0] == "FIRST_FAILURE"
    assert "CONFIG_REQUIRED_ENV_MISSING" in codes
    serialized = json.dumps(result.to_dict())
    assert "localhost" not in serialized


def test_summary_preserves_artifacts_when_public_address_value_is_invalid(tmp_path):
    context = make_context(tmp_path)
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result(
        "preflight",
        {"stage": "preflight", "success": False, "diagnostics": []},
    )
    config = {
        "PLATFORM_PUBLIC_HOST": "platform.example.invalid",
        "PLATFORM_PUBLIC_SCHEME": "invalid-scheme",
        "MYSQL_HOST_PORT": "3307",
        "JENKINS_HTTP_PORT": "8080",
        "BACKEND_HOST_PORT": "8000",
        "FRONTEND_HOST_PORT": "5173",
    }

    result = SummaryService(store).run(context, config)

    assert result.success is False
    assert any(item.code == "CONFIG_ENV_VALUE_INVALID" for item in result.diagnostics)
    assert result.addresses == {}
    assert (context.evidence_dir / "platform-bootstrap-summary.json").is_file()
    assert (context.evidence_dir / "platform-bootstrap-summary.md").is_file()
    assert (context.evidence_dir / "platform-bootstrap-addresses.json").is_file()


def test_summary_fails_when_any_fixed_stage_result_is_missing(tmp_path):
    context = make_context(tmp_path)
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result("preflight", {"stage": "preflight", "success": True})
    config = {
        "JENKINS_PUBLIC_BASE_URL": "https://jenkins.example.invalid",
        "MYSQL_HOST": "db.example.invalid",
        "MYSQL_HOST_PORT": "3307",
        "FRONTEND_SERVICE_URL": "https://platform.example.invalid",
        "BACKEND_SERVICE_URL": "https://api.example.invalid",
        "BACKEND_API_BASE_URL": "https://api.example.invalid/api/v1",
    }

    result = SummaryService(store).run(context, config)

    assert result.success is False
    assert any("dependencies" in item.target for item in result.diagnostics)
    assert any("schema-initialization" in item.target for item in result.diagnostics)
    assert any("tests" in item.target for item in result.diagnostics)
