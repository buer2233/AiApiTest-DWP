from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import install_missing_requirements as installer


def test_collect_missing_requirements_detects_absent_and_version_mismatch(tmp_path, monkeypatch):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        "\n".join(
            [
                "pytest==7.4.4",
                "requests==2.32.5",
                'pyreadline3==3.5.6; platform_system == "Windows"',
            ]
        ),
        encoding="utf-8",
    )
    installed = {
        installer.normalize_package_name("pytest"): "7.4.4",
        installer.normalize_package_name("requests"): "2.31.0",
    }

    monkeypatch.setattr(installer.platform, "system", lambda: "Linux")

    missing = installer.collect_missing_requirements(requirements, installed)

    assert missing == ["requests==2.32.5"]


def test_collect_missing_requirements_installs_windows_marker_only_on_windows(tmp_path, monkeypatch):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text('pyreadline3==3.5.6; platform_system == "Windows"', encoding="utf-8")

    monkeypatch.setattr(installer.platform, "system", lambda: "Linux")
    assert installer.collect_missing_requirements(requirements, {}) == []

    monkeypatch.setattr(installer.platform, "system", lambda: "Windows")
    assert installer.collect_missing_requirements(requirements, {}) == [
        'pyreadline3==3.5.6; platform_system == "Windows"'
    ]


def test_install_missing_requirements_skips_pip_install_when_all_satisfied(tmp_path, monkeypatch):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pytest==7.4.4", encoding="utf-8")
    calls = []

    monkeypatch.setattr(installer, "get_installed_packages", lambda: {"pytest": "7.4.4"})
    monkeypatch.setattr(installer.subprocess, "run", lambda command, check: calls.append(command))

    result = installer.install_missing_requirements(requirements)

    assert result == []
    assert calls == []


def test_install_missing_requirements_installs_only_missing_specs(tmp_path, monkeypatch):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pytest==7.4.4\nrequests==2.32.5", encoding="utf-8")
    calls = []

    monkeypatch.setattr(installer, "get_installed_packages", lambda: {"pytest": "7.4.4"})
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda command, check: calls.append((command, check)) or SimpleNamespace(returncode=0),
    )

    result = installer.install_missing_requirements(requirements)

    assert result == ["requests==2.32.5"]
    assert calls == [([installer.sys.executable, "-m", "pip", "install", "requests==2.32.5"], True)]


def test_get_installed_packages_normalizes_pip_list_package_names(monkeypatch):
    """pip list 返回的包名大小写、下划线和点号差异不应影响依赖匹配。"""

    def fake_run(command, check, capture_output, text):
        assert command == [installer.sys.executable, "-m", "pip", "list", "--format=json"]
        assert check is True
        assert capture_output is True
        assert text is True
        return SimpleNamespace(
            stdout='[{"name": "Requests_Test", "version": "1.0.0"}, {"name": "Py.YAML", "version": "6.0.2"}]'
        )

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    assert installer.get_installed_packages() == {
        "requests-test": "1.0.0",
        "py-yaml": "6.0.2",
    }


def test_get_installed_packages_raises_clear_error_when_pip_list_fails(monkeypatch):
    """pip list 查询失败时应抛出带上下文的 RuntimeError，便于 Jenkins 日志定位。"""

    def fake_run(command, check, capture_output, text):
        raise installer.subprocess.CalledProcessError(
            returncode=2,
            cmd=command,
            stderr="pip is unavailable",
        )

    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Failed to query installed Python packages"):
        installer.get_installed_packages()


def test_get_installed_packages_raises_clear_error_when_pip_list_returns_invalid_json(monkeypatch):
    """pip list 输出不是 JSON 时应给出清晰错误，而不是泄漏底层 JSONDecodeError。"""

    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda command, check, capture_output, text: SimpleNamespace(stdout="not-json"),
    )

    with pytest.raises(RuntimeError, match="pip list returned invalid JSON"):
        installer.get_installed_packages()
