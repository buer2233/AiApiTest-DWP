"""Stage13 Task 3B 双平台 trigger wrapper 静态契约。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = ROOT / "scripts" / "trigger-platform-bootstrap.ps1"
BASH = ROOT / "scripts" / "trigger-platform-bootstrap.sh"


def read_required(path: Path) -> str:
    assert path.is_file(), f"missing required Task3B wrapper: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_powershell_wrapper_has_only_two_strict_boolean_parameters_and_same_core():
    source = read_required(POWERSHELL)

    assert "[ValidateSet('true', 'false')]" in source
    assert "$BuildAll = 'true'" in source
    assert "$RunFullTests = 'false'" in source
    assert "platform_bootstrap_cli.py" in source
    assert "trigger" in source
    assert "--build-all" in source
    assert "--run-full-tests" in source
    assert "$PSScriptRoot" in source
    assert "python" in source.lower()


def test_bash_wrapper_has_strict_defaults_and_same_core():
    source = read_required(BASH)

    assert "BUILD_ALL=true" in source
    assert "RUN_FULL_TESTS=false" in source
    assert "--build-all" in source
    assert "--run-full-tests" in source
    assert "platform_bootstrap_cli.py" in source
    assert "python3" in source
    assert "python" in source
    assert "exec" in source


def test_wrappers_do_not_parse_env_or_bypass_pipeline():
    source = (read_required(POWERSHELL) + "\n" + read_required(BASH)).lower()

    for forbidden in [
        "get-content",
        "source .env",
        "dotenv",
        "docker",
        "compose",
        "pip ",
        "npm ",
        "curl ",
        "invoke-webrequest",
        "jenkins_api_token",
        "jenkins_username",
    ]:
        assert forbidden not in source
