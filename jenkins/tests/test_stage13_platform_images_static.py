"""Stage13 平台不可变镜像与 Compose 契约测试。"""

from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT_DIR / "docker-compose.yml"
IMAGE_LABELS = {
    "aiapitest.component",
    "aiapitest.dependency-hash",
    "aiapitest.build-input-hash",
    "aiapitest.source-revision",
}
BUILD_ARGS = {
    "AIAPITEST_DEPENDENCY_HASH",
    "AIAPITEST_BUILD_INPUT_HASH",
    "AIAPITEST_SOURCE_REVISION",
}


def read_text(relative_path: str) -> str:
    path = ROOT_DIR / relative_path
    assert path.exists(), f"Missing required Stage13 file: {relative_path}"
    return path.read_text(encoding="utf-8")


def load_compose() -> dict:
    return yaml.safe_load(read_text("docker-compose.yml"))


def load_worker_healthcheck_module():
    script_path = ROOT_DIR / "docker" / "healthchecks" / "worker_heartbeat_healthcheck.py"
    assert script_path.exists()
    spec = importlib.util.spec_from_file_location("worker_heartbeat_healthcheck", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compose_uses_fixed_project_and_defines_platform_services():
    compose = load_compose()

    assert compose["name"] == "aiapitest-dwp"
    assert set(compose["services"]) == {
        "mysql",
        "jenkins",
        "backend",
        "frontend",
        "jenkins-sync-worker",
        "api-runner",
    }


def test_application_services_do_not_start_bootstrap_services_implicitly():
    services = load_compose()["services"]

    for service_name in ["backend", "frontend", "jenkins-sync-worker", "api-runner"]:
        assert "depends_on" not in services[service_name]

    assert services["mysql"]["volumes"] == ["aiapitest-mysql-data:/var/lib/mysql"]
    assert "aiapitest-jenkins-home:/var/jenkins_home" in services["jenkins"]["volumes"]


def test_jenkins_controller_uses_tools_image_and_socket_group_permission():
    jenkins = load_compose()["services"]["jenkins"]

    assert jenkins["image"] == "aiapitest-jenkins:lts-jdk17-tools"
    assert jenkins["build"]["dockerfile"] == "docker/jenkins/Dockerfile"
    assert "/var/run/docker.sock:/var/run/docker.sock" in jenkins["volumes"]
    assert jenkins["group_add"] == ["${DOCKER_GID:-0}"]

    dockerfile = read_text("docker/jenkins/Dockerfile")
    assert "docker-ce-cli" in dockerfile
    assert "docker-compose-plugin" in dockerfile
    assert "COPY api-test/requirements.txt" not in dockerfile
    assert "AIAPITEST_PREINSTALLED_REQUIREMENTS" not in dockerfile
    assert "chmod 666" not in dockerfile


def test_backend_and_worker_share_immutable_image_with_healthchecks():
    services = load_compose()["services"]
    backend = services["backend"]
    worker = services["jenkins-sync-worker"]

    assert backend["image"] == "aiapitest-backend:local"
    assert backend["build"]["dockerfile"] == "back-end/Dockerfile"
    assert "gunicorn" in " ".join(backend["command"])
    assert "/api/v1/health/ready/" in " ".join(backend["healthcheck"]["test"])
    assert backend["environment"]["DB_HOST"] == "mysql"
    assert str(backend["environment"]["DB_PORT"]) == "3306"

    assert worker["image"] == backend["image"]
    assert "sync_jenkins_results" in " ".join(worker["command"])
    assert worker["environment"]["JENKINS_API_BASE_URL"] == "http://jenkins:8080"
    assert "worker_heartbeat_healthcheck.py" in " ".join(worker["healthcheck"]["test"])


def test_frontend_runtime_provides_nginx_spa_proxy_and_health():
    frontend = load_compose()["services"]["frontend"]
    dockerfile = read_text("front-end/Dockerfile")
    nginx_config = read_text("docker/nginx/default.conf")

    assert frontend["image"] == "aiapitest-frontend:local"
    assert frontend["build"]["target"] == "runtime"
    assert "nginx" in dockerfile.lower()
    assert "mcr.microsoft.com/playwright:v1.61.1" in dockerfile
    assert "npm ci" in dockerfile
    assert "npx playwright install" not in dockerfile
    assert "location = /health" in nginx_config
    assert "resolver 127.0.0.11" in nginx_config
    assert "set $backend_upstream http://backend:8000" in nginx_config
    assert "proxy_pass $backend_upstream" in nginx_config
    assert "try_files $uri $uri/ /index.html" in nginx_config
    assert "/health" in " ".join(frontend["healthcheck"]["test"])


def test_domain_dockerfiles_publish_hash_and_source_labels():
    for relative_path in ["back-end/Dockerfile", "front-end/Dockerfile", "api-test/Dockerfile"]:
        dockerfile = read_text(relative_path)
        for build_arg in BUILD_ARGS:
            assert f"ARG {build_arg}" in dockerfile
        for image_label in IMAGE_LABELS:
            assert image_label in dockerfile


def test_api_runner_is_non_persistent_and_uses_image_internal_source():
    runner = load_compose()["services"]["api-runner"]
    dockerfile = read_text("api-test/Dockerfile")

    assert runner["image"] == "aiapitest-api-runner:local"
    assert runner["profiles"] == ["tools"]
    assert runner["restart"] == "no"
    assert "volumes" not in runner
    assert runner["working_dir"] == "/workspace/AiApiTest-DWP/api-test"
    assert "COPY . /workspace/AiApiTest-DWP" in dockerfile
    assert "api-test/requirements.txt" in dockerfile
    assert "python -m pip install" in dockerfile
    assert "allure-commandline" in dockerfile
    assert "mkdir -p /workspace/AiApiTest-DWP/api-test/report" in dockerfile


def test_api_runner_uses_supported_java_runtime_for_current_debian_base():
    dockerfile = read_text("api-test/Dockerfile")

    assert "openjdk-21-jre-headless" in dockerfile
    assert "openjdk-17-jre-headless" not in dockerfile


def test_dockerignore_excludes_private_and_generated_content():
    dockerignore = read_text(".dockerignore")
    ignored_lines = dockerignore.splitlines()

    for ignored in [
        ".git",
        ".idea",
        ".env",
        "node_modules",
        ".venv",
        "runtime",
        "report",
        "logs",
        "test-results",
        "htmlcov",
        "*.log",
    ]:
        assert ignored in dockerignore
    assert "!.env.example" in dockerignore
    assert "**/tests/evidence" in ignored_lines
    assert ".gitignore" not in ignored_lines


def test_compose_never_declares_destructive_volume_or_base_service_commands():
    compose_text = read_text("docker-compose.yml")

    for forbidden in ["down -v", "volume rm", "docker rm aiapitest-mysql", "docker rm aiapitest-jenkins"]:
        assert forbidden not in compose_text


def test_worker_heartbeat_healthcheck_handles_fresh_stale_and_missing_files(tmp_path):
    module = load_worker_healthcheck_module()

    heartbeat_path = tmp_path / "worker.heartbeat"
    heartbeat_path.write_text("2026-07-13T00:00:00Z", encoding="utf-8")
    os.utime(heartbeat_path, (1_000.0, 1_000.0))

    assert module.is_heartbeat_fresh(heartbeat_path, max_age_seconds=30, now=1_020.0)
    assert not module.is_heartbeat_fresh(heartbeat_path, max_age_seconds=30, now=1_031.0)
    assert not module.is_heartbeat_fresh(tmp_path / "missing", max_age_seconds=30, now=1_020.0)


def test_worker_heartbeat_healthcheck_main_uses_env_and_returns_nonzero_for_stale(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = load_worker_healthcheck_module()
    heartbeat_path = tmp_path / "worker.heartbeat"
    heartbeat_path.write_text("timestamp-only", encoding="utf-8")
    stale_time = time.time() - 120
    os.utime(heartbeat_path, (stale_time, stale_time))
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_MAX_AGE_SECONDS", "30")

    assert module.main() == 1
    assert "missing or stale" in capsys.readouterr().err


def test_worker_heartbeat_healthcheck_invalid_threshold_uses_safe_default(tmp_path, monkeypatch):
    module = load_worker_healthcheck_module()
    heartbeat_path = tmp_path / "worker.heartbeat"
    heartbeat_path.write_text("timestamp-only", encoding="utf-8")
    fresh_time = time.time() - 5
    os.utime(heartbeat_path, (fresh_time, fresh_time))
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_MAX_AGE_SECONDS", "invalid")

    assert module.main() == 0
