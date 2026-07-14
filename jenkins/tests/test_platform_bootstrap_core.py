"""Stage13 Task 3A 环境编排核心契约测试。"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest
from argparse import Namespace


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.adapters import SubprocessCommandRunner  # noqa: E402
from platform_bootstrap.configuration import (  # noqa: E402
    ConfigError,
    DotEnvConfig,
    parse_bounded_int,
)
from platform_bootstrap.models import CommandSpec, Diagnostic  # noqa: E402
from platform_bootstrap.security import Redactor  # noqa: E402


class FakeProcess:
    """提供最小 Popen 接口，避免单元测试启动真实外部进程。"""

    def __init__(self, output: str, returncode: int = 0):
        self.stdout = io.StringIO(output)
        self.returncode = returncode

    def wait(self, timeout=None):
        return self.returncode

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def kill(self):
        self.returncode = -9


def test_diagnostic_has_fixed_structured_fields():
    diagnostic = Diagnostic(
        stage="preflight",
        code="CONFIG_ENV_MISSING",
        target=".env",
        reason="missing",
        observed="not found",
        evidence=("preflight.json",),
        suggestion="create the private configuration",
        rerun="rebuild the Jenkins job",
    )

    assert list(diagnostic.to_dict()) == [
        "stage",
        "code",
        "target",
        "reason",
        "observed",
        "evidence",
        "suggestion",
        "rerun",
    ]


def test_redactor_masks_literals_headers_urls_and_sensitive_mappings():
    redactor = Redactor.from_env(
        {
            "JENKINS_API_TOKEN": "token-value-123",
            "MYSQL_ROOT_PASSWORD": "mysql-pass-456",
            "JENKINS_USERNAME": "sensitive-user",
        },
        extra_secrets=("cookie-value",),
    )
    raw = (
        "Authorization: Bearer token-value-123; Cookie=cookie-value; "
        "http://sensitive-user:mysql-pass-456@example.invalid/path?token=token-value-123"
    )

    redacted = redactor.text(raw)
    assert "token-value-123" not in redacted
    assert "mysql-pass-456" not in redacted
    assert "sensitive-user" not in redacted
    assert "cookie-value" not in redacted
    assert "***" in redacted
    assert redactor.mapping({"password": "plain", "safe": "visible"}) == {
        "password": "***",
        "safe": "visible",
    }


def test_dotenv_parser_supports_required_subset_and_only_reports_key_names(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# comment\n"
        "export FIRST='one value'\n"
        'SECOND="two\\nlines" # trailing comment\n'
        "EMPTY=\n"
        "FIRST=last\n",
        encoding="utf-8",
    )

    config = DotEnvConfig.load(env_path)
    assert config.get("FIRST") == "last"
    assert config.get("SECOND") == "two\nlines"
    assert config.get("EMPTY") == ""
    assert config.key_status(["FIRST", "MISSING"]) == {
        "FIRST": "present",
        "MISSING": "missing",
    }
    assert config.warnings == ("duplicate key: FIRST",)

    with pytest.raises(ConfigError) as exc_info:
        config.require(["FIRST", "MISSING"])
    assert "MISSING" in str(exc_info.value)
    assert "last" not in str(exc_info.value)


def test_invalid_bounded_integer_uses_safe_default():
    assert parse_bounded_int("invalid", default=30, minimum=1, maximum=300) == 30
    assert parse_bounded_int("0", default=30, minimum=1, maximum=300) == 30
    assert parse_bounded_int("999", default=30, minimum=1, maximum=300) == 30
    assert parse_bounded_int("45", default=30, minimum=1, maximum=300) == 45


def test_command_runner_uses_argv_shell_false_and_writes_redacted_full_log(tmp_path):
    calls = []

    def fake_popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return FakeProcess("first line\nsecret-token\nlast line\n", returncode=7)

    evidence_path = tmp_path / "command.log"
    runner = SubprocessCommandRunner(
        redactor=Redactor(extra_secrets=("secret-token",)),
        popen_factory=fake_popen,
    )
    result = runner.run(
        CommandSpec(
            argv=("tool", "--check"),
            cwd=tmp_path,
            timeout_seconds=10,
            evidence_path=evidence_path,
        )
    )

    assert calls[0][0] == ["tool", "--check"]
    assert calls[0][1]["shell"] is False
    assert result.returncode == 7
    assert result.timed_out is False
    assert "secret-token" not in evidence_path.read_text(encoding="utf-8")
    assert "***" in evidence_path.read_text(encoding="utf-8")
    assert json.loads(json.dumps(result.to_dict()))["returncode"] == 7


def test_cli_exposes_six_environment_stages_and_trigger_subcommand():
    from platform_bootstrap.cli import build_parser, main, parse_bool

    parser = build_parser()
    subparsers_action = next(
        action for action in parser._actions if getattr(action, "choices", None)
    )
    assert set(subparsers_action.choices) == {
        "preflight",
        "assure-dependencies",
        "deploy",
        "health",
        "test",
        "summary",
        "trigger",
    }
    assert parse_bool("true") is True
    assert parse_bool("false") is False
    with pytest.raises(ValueError):
        parse_bool("yes")

    dispatched = []
    assert main(
        ["preflight"],
        dispatcher=lambda command, options: dispatched.append((command, options)) or 0,
    ) == 0
    assert dispatched[0][0] == "preflight"

    triggered = []
    assert main(
        ["trigger", "--build-all", "false", "--run-full-tests", "true"],
        dispatcher=lambda command, options: triggered.append((command, options)) or 0,
    ) == 0
    assert triggered[0][0] == "trigger"
    assert triggered[0][1].build_all == "false"
    assert triggered[0][1].run_full_tests == "true"


@pytest.mark.parametrize(
    "env_text",
    [
        None,
        "JENKINS_API_BASE_URL=https://jenkins.example.invalid\n",
        (
            "JENKINS_API_BASE_URL=not-a-url\n"
            "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME=Platform\n"
            "JENKINS_USERNAME=user\n"
            "JENKINS_API_TOKEN=token-value\n"
        ),
    ],
)
def test_trigger_configuration_errors_are_structured_without_traceback(
    tmp_path,
    monkeypatch,
    capsys,
    env_text,
):
    from platform_bootstrap.cli import run_stage

    if env_text is not None:
        (tmp_path / ".env").write_text(env_text, encoding="utf-8")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_WORKSPACE", str(tmp_path))

    exit_code = run_stage(
        "trigger",
        Namespace(build_all="true", run_full_tests="false"),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.out + captured.err
    payload = json.loads(captured.out)
    diagnostic = payload["diagnostics"][0]
    assert list(diagnostic) == [
        "stage",
        "code",
        "target",
        "reason",
        "observed",
        "evidence",
        "suggestion",
        "rerun",
    ]
    assert diagnostic["evidence"]
    assert all(Path(path).is_file() for path in diagnostic["evidence"])
    assert all(Path(path).name != ".env" for path in diagnostic["evidence"])


def test_trigger_invalid_utf8_env_is_structured_without_traceback(tmp_path, monkeypatch, capsys):
    from platform_bootstrap.cli import run_stage

    (tmp_path / ".env").write_bytes(b"JENKINS_API_TOKEN=\xff\xfe")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_WORKSPACE", str(tmp_path))

    exit_code = run_stage("trigger", Namespace(build_all="true", run_full_tests="false"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.out + captured.err
    payload = json.loads(captured.out)
    assert list(payload["diagnostics"][0]) == [
        "stage",
        "code",
        "target",
        "reason",
        "observed",
        "evidence",
        "suggestion",
        "rerun",
    ]
    assert "ff" not in captured.out.lower()


def test_trigger_env_read_oserror_is_structured_without_traceback(
    tmp_path,
    monkeypatch,
    capsys,
):
    from platform_bootstrap.cli import run_stage

    env_path = tmp_path / ".env"
    env_path.write_text("placeholder=value\n", encoding="utf-8")
    original_read_text = Path.read_text

    def failing_read_text(self, *args, **kwargs):
        if self == env_path:
            raise PermissionError("synthetic permission failure with secret-value")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read_text)
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_WORKSPACE", str(tmp_path))

    exit_code = run_stage("trigger", Namespace(build_all="false", run_full_tests="false"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.out + captured.err
    assert "secret-value" not in captured.out + captured.err
    assert json.loads(captured.out)["diagnostics"][0]["code"]


@pytest.mark.parametrize("failure_point", ["mkdir", "write", "replace"])
def test_trigger_evidence_persistence_failure_keeps_primary_config_diagnostic(
    tmp_path,
    monkeypatch,
    capsys,
    failure_point,
):
    from platform_bootstrap.cli import run_stage
    import platform_bootstrap.evidence as evidence_module

    monkeypatch.setenv("PLATFORM_BOOTSTRAP_WORKSPACE", str(tmp_path))
    original_mkdir = Path.mkdir
    original_write_text = Path.write_text
    original_replace = evidence_module.os.replace

    def failing_mkdir(self, *args, **kwargs):
        if failure_point == "mkdir" and "helper-" in str(self):
            raise OSError("synthetic mkdir secret-value")
        return original_mkdir(self, *args, **kwargs)

    def failing_write_text(self, *args, **kwargs):
        if failure_point == "write" and "helper-" in str(self):
            raise OSError("synthetic write secret-value")
        return original_write_text(self, *args, **kwargs)

    def failing_replace(source, destination):
        if failure_point == "replace" and "helper-" in str(destination):
            raise OSError("synthetic replace secret-value")
        return original_replace(source, destination)

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)
    monkeypatch.setattr(Path, "write_text", failing_write_text)
    monkeypatch.setattr(evidence_module.os, "replace", failing_replace)

    exit_code = run_stage("trigger", Namespace(build_all="true", run_full_tests="false"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Traceback" not in captured.out + captured.err
    assert "secret-value" not in captured.out + captured.err
    diagnostic = json.loads(captured.out)["diagnostics"][0]
    assert list(diagnostic) == [
        "stage",
        "code",
        "target",
        "reason",
        "observed",
        "evidence",
        "suggestion",
        "rerun",
    ]
    assert diagnostic["evidence"] == []
    assert "persistence" in diagnostic["observed"].lower()


def test_trigger_evidence_root_symlink_escape_is_rejected_without_external_write(
    tmp_path,
    monkeypatch,
    capsys,
):
    from platform_bootstrap.cli import run_stage

    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    original_resolve = Path.resolve
    original_mkdir = Path.mkdir
    outside_mkdir_calls = []

    def fake_resolve(self, *args, **kwargs):
        if "runtime" in self.parts and "platform-bootstrap" in self.parts:
            return outside / self.name
        return original_resolve(self, *args, **kwargs)

    def guarded_mkdir(self, *args, **kwargs):
        if self == outside or outside in self.parents:
            outside_mkdir_calls.append(self)
            raise OSError("outside write attempted secret-value")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)
    monkeypatch.setattr(Path, "mkdir", guarded_mkdir)
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_WORKSPACE", str(tmp_path))

    exit_code = run_stage("trigger", Namespace(build_all="false", run_full_tests="false"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert outside_mkdir_calls == []
    assert "Traceback" not in captured.out + captured.err
    assert "secret-value" not in captured.out + captured.err
    diagnostic = json.loads(captured.out)["diagnostics"][0]
    assert diagnostic["evidence"] == []
    assert "persistence" in diagnostic["observed"].lower()
