"""Stage13 Task 3A 只读预检测试。"""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.evidence import EvidenceStore  # noqa: E402
from platform_bootstrap.models import CommandResult, RunContext  # noqa: E402
from platform_bootstrap.preflight import PreflightService  # noqa: E402


REQUIRED_ENV = {
    "MYSQL_ROOT_PASSWORD": "private-mysql-password",
    "DJANGO_SECRET_KEY": "private-django-secret",
    "AUTH_TOKEN_SECRET": "private-auth-secret",
    "JENKINS_PUBLIC_BASE_URL": "https://jenkins.example.invalid",
    "JENKINS_API_BASE_URL": "https://jenkins-api.example.invalid",
    "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME": "Platform/Bootstrap",
    "MYSQL_HOST": "db.example.invalid",
    "MYSQL_HOST_PORT": "3307",
    "FRONTEND_SERVICE_URL": "https://platform.example.invalid",
    "BACKEND_SERVICE_URL": "https://api.example.invalid",
    "BACKEND_API_BASE_URL": "https://api.example.invalid/api/v1",
}

LIMITED_FORMAT = "{{.Id}}|{{.State.Running}}|unknown"


def limited_inspect(container):
    return ("docker", "inspect", "--format", LIMITED_FORMAT, container)


class FakeRunner:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        key = tuple(spec.argv)
        response = self.responses.get(key, (0, "ok"))
        return CommandResult.from_output(
            returncode=response[0],
            output=response[1],
            evidence_path=spec.evidence_path,
        )


def write_env(path: Path):
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in REQUIRED_ENV.items()) + "\n",
        encoding="utf-8",
    )


def make_context(tmp_path: Path) -> RunContext:
    tmp_path.mkdir(parents=True, exist_ok=True)
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("name: aiapitest-dwp\nservices: {}\n", encoding="utf-8")
    return RunContext.create(
        workspace=tmp_path,
        evidence_dir=tmp_path / "evidence",
        build_id="unit-1",
        build_url="https://jenkins.example.invalid/job/1/",
        build_all=False,
        run_full_tests=False,
    )


def test_missing_env_fails_without_running_any_command(tmp_path):
    context = make_context(tmp_path)
    runner = FakeRunner()

    result = PreflightService(runner, EvidenceStore(context.evidence_dir)).run(context)

    assert result.success is False
    assert result.diagnostics[0].code == "CONFIG_ENV_MISSING"
    assert runner.specs == []
    assert not context.env_file.exists()
    assert result.diagnostics[0].evidence
    assert all(Path(path).is_file() for path in result.diagnostics[0].evidence)
    assert all(Path(path).name != ".env" for path in result.diagnostics[0].evidence)


def test_missing_compose_writes_real_evidence_and_runs_no_command(tmp_path):
    context = make_context(tmp_path)
    write_env(context.env_file)
    context.compose_file.unlink()
    runner = FakeRunner()

    result = PreflightService(runner, EvidenceStore(context.evidence_dir)).run(context)

    assert result.success is False
    assert result.diagnostics[0].code == "CONFIG_COMPOSE_MISSING"
    assert runner.specs == []
    assert result.diagnostics[0].evidence
    assert all(Path(path).is_file() for path in result.diagnostics[0].evidence)
    evidence_text = Path(result.diagnostics[0].evidence[0]).read_text(encoding="utf-8")
    assert "docker-compose.yml" in evidence_text
    assert "MYSQL_ROOT_PASSWORD" not in evidence_text


def test_preflight_is_read_only_and_records_only_key_presence(tmp_path):
    context = make_context(tmp_path)
    write_env(context.env_file)
    responses = {
        limited_inspect("aiapitest-jenkins"): (0, "jenkins-id|true|unknown"),
        limited_inspect("aiapitest-mysql"): (0, "mysql-id|true|unknown"),
        (
            "docker",
            "inspect",
            "--format",
            "{{.State.Health.Status}}",
            "aiapitest-mysql",
        ): (0, "healthy"),
        ("docker", "inspect", "aiapitest-jenkins"): (
            0,
            '[{"Id":"jenkins-id","State":{"Running":true,"Health":{"Status":"healthy"}}}]',
        ),
        ("docker", "inspect", "aiapitest-mysql"): (
            0,
            '[{"Id":"mysql-id","State":{"Running":true,"Health":{"Status":"healthy"}}}]',
        ),
    }
    runner = FakeRunner(responses)

    result = PreflightService(runner, EvidenceStore(context.evidence_dir)).run(context)

    assert result.success is True
    assert result.details["baseline_container_ids"] == {
        "jenkins": "jenkins-id",
        "mysql": "mysql-id",
    }
    serialized = str(result.to_dict())
    for secret in ["private-mysql-password", "private-django-secret", "private-auth-secret"]:
        assert secret not in serialized
    assert result.details["environment_keys"]["MYSQL_ROOT_PASSWORD"] == "present"

    command_text = "\n".join(" ".join(spec.argv) for spec in runner.specs).lower()
    for forbidden in [" up ", " start ", " restart ", " stop ", "chmod", " down "]:
        assert forbidden not in f" {command_text} "
    assert "config --quiet" in command_text
    assert "config --no-interpolate" in command_text
    assert ("docker", "inspect", "aiapitest-jenkins") not in [spec.argv for spec in runner.specs]
    assert ("docker", "inspect", "aiapitest-mysql") not in [spec.argv for spec in runner.specs]
    assert all(".Config" not in " ".join(spec.argv) for spec in runner.specs)
    assert all(".Env" not in " ".join(spec.argv) for spec in runner.specs)


def test_mysql_stopped_and_socket_permission_have_frozen_codes(tmp_path):
    context = make_context(tmp_path)
    write_env(context.env_file)
    stopped = FakeRunner(
        {
            limited_inspect("aiapitest-jenkins"): (0, "jenkins-id|true|unknown"),
            limited_inspect("aiapitest-mysql"): (0, "mysql-id|false|missing"),
            ("docker", "inspect", "aiapitest-jenkins"): (
                0,
                '[{"Id":"jenkins-id","State":{"Running":true,"Health":{"Status":"healthy"}}}]',
            ),
            ("docker", "inspect", "aiapitest-mysql"): (
                0,
                '[{"Id":"mysql-id","State":{"Running":false}}]',
            ),
        }
    )
    stopped_result = PreflightService(stopped, EvidenceStore(context.evidence_dir)).run(context)
    assert {item.code for item in stopped_result.diagnostics} == {
        "BOOTSTRAP_MYSQL_NOT_RUNNING"
    }

    denied_context = make_context(tmp_path / "denied")
    write_env(denied_context.env_file)
    denied = FakeRunner({("docker", "info"): (1, "permission denied /var/run/docker.sock")})
    denied_result = PreflightService(
        denied, EvidenceStore(denied_context.evidence_dir)
    ).run(denied_context)
    assert denied_result.diagnostics[0].code == "DOCKER_SOCKET_PERMISSION_DENIED"
    assert "chmod 666" not in denied_result.diagnostics[0].suggestion


def test_mysql_unhealthy_collects_limited_health_and_tail_logs_without_config_env(tmp_path):
    context = make_context(tmp_path)
    write_env(context.env_file)
    runner = FakeRunner(
        {
            limited_inspect("aiapitest-jenkins"): (0, "jenkins-id|true|unknown"),
            limited_inspect("aiapitest-mysql"): (0, "mysql-id|true|unknown"),
            (
                "docker",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                "aiapitest-mysql",
            ): (0, "unhealthy"),
            (
                "docker",
                "inspect",
                "--format",
                "{{range .State.Health.Log}}{{.ExitCode}}|{{.Output}}{{println}}{{end}}",
                "aiapitest-mysql",
            ): (0, "1|mysqladmin: connection refused"),
            ("docker", "logs", "--tail", "200", "aiapitest-mysql"): (
                0,
                "mysql startup failed without secrets",
            ),
        }
    )

    result = PreflightService(runner, EvidenceStore(context.evidence_dir)).run(context)

    assert result.success is False
    assert result.diagnostics[0].code == "BOOTSTRAP_MYSQL_UNHEALTHY"
    assert len(result.diagnostics[0].evidence) >= 2
    commands = [spec.argv for spec in runner.specs]
    assert ("docker", "logs", "--tail", "200", "aiapitest-mysql") in commands
    assert all(".Config" not in " ".join(argv) for argv in commands)
    assert all(".Env" not in " ".join(argv) for argv in commands)
