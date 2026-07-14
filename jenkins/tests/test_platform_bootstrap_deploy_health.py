"""Stage13 Task 3A 部署与有限健康检查测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.deploy import DeployService  # noqa: E402
from platform_bootstrap.evidence import EvidenceStore  # noqa: E402
from platform_bootstrap.health import HealthService  # noqa: E402
from platform_bootstrap.models import (  # noqa: E402
    CommandResult,
    HttpResponse,
    RunContext,
)


class FakeRunner:
    def __init__(self, fail_up=False, worker_status="healthy", container_ids=None, fail_cleanup=False):
        self.fail_up = fail_up
        self.worker_status = worker_status
        self.container_ids = container_ids or {
            "aiapitest-jenkins": "jenkins-id",
            "aiapitest-mysql": "mysql-id",
        }
        self.fail_cleanup = fail_cleanup
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        argv = tuple(spec.argv)
        if "up" in argv and self.fail_up:
            spec.evidence_path.parent.mkdir(parents=True, exist_ok=True)
            spec.evidence_path.write_text("port conflict", encoding="utf-8")
            return CommandResult.from_output(23, "port conflict", spec.evidence_path)
        if argv[:2] == ("docker", "inspect") and "aiapitest-jenkins-sync-worker" in argv:
            spec.evidence_path.parent.mkdir(parents=True, exist_ok=True)
            spec.evidence_path.write_text(self.worker_status, encoding="utf-8")
            return CommandResult.from_output(0, self.worker_status, spec.evidence_path)
        if argv[:4] == ("docker", "inspect", "--format", "{{.Id}}"):
            return CommandResult.from_output(
                0,
                self.container_ids.get(argv[-1], "missing-id"),
                spec.evidence_path,
            )
        spec.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        spec.evidence_path.write_text("ok", encoding="utf-8")
        return CommandResult.from_output(0, "ok", spec.evidence_path)


class FakeHttpClient:
    def __init__(self, statuses=None):
        self.statuses = {key: list(value) for key, value in (statuses or {}).items()}
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        values = self.statuses.get(request.url, [200])
        status = values.pop(0) if len(values) > 1 else values[0]
        self.statuses[request.url] = values
        body = b'{"status":"ok"}' if status == 200 else b'{"reason":"database_unavailable"}'
        return HttpResponse(status=status, headers={}, body=body)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


def make_context(tmp_path, build_all):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docker-compose.yml").write_text("name: aiapitest-dwp\n", encoding="utf-8")
    (tmp_path / ".env").write_text("KEY=value\n", encoding="utf-8")
    return RunContext.create(
        workspace=tmp_path,
        evidence_dir=tmp_path / "evidence",
        build_id="deploy-health-unit",
        build_url="https://jenkins.example.invalid/job/1/",
        build_all=build_all,
        run_full_tests=False,
    )


def mark_dependencies_ready(store):
    store.write_stage_result("dependencies", {"stage": "dependencies", "success": True})


def mark_preflight_ready(store):
    store.write_stage_result(
        "preflight",
        {
            "stage": "preflight",
            "success": True,
            "details": {
                "baseline_container_ids": {
                    "jenkins": "jenkins-id",
                    "mysql": "mysql-id",
                }
            },
        },
    )


def test_full_and_incremental_deploy_use_exact_application_targets(tmp_path):
    for build_all, expected_force in [(True, True), (False, False)]:
        context = make_context(tmp_path / str(build_all), build_all)
        store = EvidenceStore(context.evidence_dir)
        mark_dependencies_ready(store)
        mark_preflight_ready(store)
        runner = FakeRunner()

        result = DeployService(runner, store).run(context)

        assert result.success is True
        command = runner.specs[0].argv
        assert command[:8] == (
            "docker",
            "compose",
            "--project-name",
            "aiapitest-dwp",
            "--env-file",
            str(context.env_file),
            "-f",
            str(context.compose_file),
        )
        assert command[-3:] == ("backend", "frontend", "jenkins-sync-worker")
        assert "--no-build" in command
        assert ("--force-recreate" in command) is expected_force
        assert "mysql" not in command and "jenkins" not in command


def test_deploy_failure_collects_evidence_without_rollback_or_stop(tmp_path):
    context = make_context(tmp_path, True)
    store = EvidenceStore(context.evidence_dir)
    mark_dependencies_ready(store)
    mark_preflight_ready(store)
    runner = FakeRunner(fail_up=True)

    result = DeployService(runner, store).run(context)

    assert result.success is False
    assert result.diagnostics[0].code == "DEPLOY_SERVICE_FAILED"
    all_commands = "\n".join(" ".join(spec.argv) for spec in runner.specs).lower()
    assert any("ps" in spec.argv for spec in runner.specs)
    assert any("logs" in spec.argv for spec in runner.specs)
    for forbidden in ["down", "rollback", " stop ", "volume rm"]:
        assert forbidden not in all_commands


def test_deploy_fails_when_bootstrap_container_id_changes_without_rollback(tmp_path):
    context = make_context(tmp_path, False)
    store = EvidenceStore(context.evidence_dir)
    mark_dependencies_ready(store)
    mark_preflight_ready(store)
    runner = FakeRunner(
        container_ids={
            "aiapitest-jenkins": "jenkins-replaced",
            "aiapitest-mysql": "mysql-id",
        }
    )

    result = DeployService(runner, store).run(context)

    assert result.success is False
    assert result.diagnostics[0].target == "jenkins"
    assert "jenkins-id" in result.diagnostics[0].observed
    assert "jenkins-replaced" in result.diagnostics[0].observed
    commands = "\n".join(" ".join(spec.argv) for spec in runner.specs).lower()
    assert "rollback" not in commands and "down" not in commands and " stop " not in commands


def test_missing_upstream_gate_files_create_real_independent_evidence(tmp_path):
    deploy_context = make_context(tmp_path / "deploy", False)
    deploy_result = DeployService(
        FakeRunner(), EvidenceStore(deploy_context.evidence_dir)
    ).run(deploy_context)
    assert deploy_result.success is False

    health_context = make_context(tmp_path / "health", False)
    health_result = HealthService(
        FakeRunner(),
        FakeHttpClient(),
        EvidenceStore(health_context.evidence_dir),
    ).run(health_context, {})
    assert health_result.success is False

    for result in [deploy_result, health_result]:
        for diagnostic in result.diagnostics:
            assert diagnostic.evidence
            assert all(Path(path).is_file() for path in diagnostic.evidence)


def test_health_checks_fixed_endpoints_and_worker_with_finite_deadline(tmp_path):
    context = make_context(tmp_path, False)
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result("deploy", {"stage": "deploy", "success": True})
    config = {
        "BACKEND_SERVICE_URL": "https://api.example.invalid",
        "FRONTEND_SERVICE_URL": "https://platform.example.invalid",
    }
    clock = FakeClock()
    client = FakeHttpClient()
    runner = FakeRunner(worker_status="healthy")

    result = HealthService(
        runner,
        client,
        store,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    ).run(context, config, timeout_seconds=5, interval_seconds=1)

    assert result.success is True
    assert [request.url for request in client.requests] == [
        "http://backend:8000/api/v1/health/live/",
        "http://backend:8000/api/v1/health/ready/",
        "http://frontend/health",
        "http://frontend/login",
        "http://frontend/api/v1/health/ready/",
    ]
    assert any("aiapitest-jenkins-sync-worker" in spec.argv for spec in runner.specs)
    for name in [
        "backend-live",
        "backend-ready",
        "frontend-health",
        "frontend-spa",
        "frontend-api-proxy",
    ]:
        evidence = context.evidence_dir / f"health-{name}.log"
        assert evidence.is_file()
        assert "status=200" in evidence.read_text(encoding="utf-8")


def test_health_timeout_is_bounded_and_worker_stale_uses_frozen_code(tmp_path):
    context = make_context(tmp_path, False)
    store = EvidenceStore(context.evidence_dir)
    store.write_stage_result("deploy", {"stage": "deploy", "success": True})
    config = {
        "BACKEND_SERVICE_URL": "https://api.example.invalid",
        "FRONTEND_SERVICE_URL": "https://platform.example.invalid",
    }
    live_url = "http://backend:8000/api/v1/health/live/"
    clock = FakeClock()
    client = FakeHttpClient({live_url: [503, 503, 503, 503]})
    runner = FakeRunner(worker_status="unhealthy: heartbeat missing or stale")

    result = HealthService(
        runner,
        client,
        store,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    ).run(context, config, timeout_seconds=2, interval_seconds=1)

    codes = {diagnostic.code for diagnostic in result.diagnostics}
    assert result.success is False
    assert "HEALTH_WORKER_STALE" in codes
    assert len([request for request in client.requests if request.url == live_url]) <= 3
    assert clock.value <= 2
    for diagnostic in result.diagnostics:
        assert diagnostic.evidence
        assert Path(diagnostic.evidence[0]).is_file()
