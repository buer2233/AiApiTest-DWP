from pathlib import Path
from types import SimpleNamespace
import sys

import runpytest


def test_build_pytest_command_supports_case_path_marker_and_clean(tmp_path):
    command = runpytest.build_pytest_command(
        case_path="test_case/test_demo_case",
        marker="smoke",
        clean=True,
        allure_results_dir=tmp_path / "allure-results",
    )

    assert command[:3] == ["python", "-m", "pytest"]
    assert "test_case/test_demo_case" in command
    assert "-m" in command
    assert "smoke" in command
    assert "--clean-alluredir" in command


def test_build_timestamped_allure_report_dir_uses_timestamp_subdir(tmp_path):
    report_root = tmp_path / "allure-report"

    report_dir = runpytest.build_timestamped_allure_report_dir(
        base_report_dir=report_root,
        timestamp="20260604_114500",
    )

    assert report_dir == report_root / "20260604_114500"


def test_build_timestamped_allure_report_dir_avoids_existing_report_dir(tmp_path):
    report_root = tmp_path / "allure-report"
    existing_dir = report_root / "20260604_114500"
    existing_dir.mkdir(parents=True)

    report_dir = runpytest.build_timestamped_allure_report_dir(
        base_report_dir=report_root,
        timestamp="20260604_114500",
    )

    assert report_dir == report_root / "20260604_114500_001"


def test_build_allure_generate_command_keeps_previous_reports(tmp_path):
    results_dir = tmp_path / "allure-results"
    report_dir = tmp_path / "allure-report" / "20260604_114500"

    command = runpytest.build_allure_generate_command(results_dir, report_dir)

    assert command == [
        "allure",
        "generate",
        str(results_dir),
        "-o",
        str(report_dir),
    ]


def test_main_supports_default_runtime_options(monkeypatch, tmp_path):
    commands = []
    report_dir = tmp_path / "allure-report" / "20260604_114500"

    monkeypatch.setattr(sys, "argv", ["runpytest.py"])
    monkeypatch.setattr(runpytest, "ensure_runtime_dirs", lambda: None)
    monkeypatch.setattr(runpytest.shutil, "which", lambda name: name)
    monkeypatch.setattr(runpytest, "build_timestamped_allure_report_dir", lambda: report_dir)

    def fake_run_command(command):
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runpytest, "run_command", fake_run_command)

    try:
        runpytest.main(
            case_path="test_case/test_douban_case",
            marker="smoke",
            open_report=True,
            clean=True,
        )
    except SystemExit as exc:
        assert exc.code == 0

    pytest_command = commands[0]
    assert "test_case/test_douban_case" in pytest_command
    assert "-m" in pytest_command
    assert "smoke" in pytest_command
    assert "--clean-alluredir" in pytest_command
    assert commands[-1] == ["allure", "open", str(report_dir)]


def test_main_cleans_allure_results_by_default(monkeypatch):
    commands = []

    monkeypatch.setattr(sys, "argv", ["runpytest.py"])
    monkeypatch.setattr(runpytest, "ensure_runtime_dirs", lambda: None)
    monkeypatch.setattr(runpytest.shutil, "which", lambda name: None)

    def fake_run_command(command):
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runpytest, "run_command", fake_run_command)

    try:
        runpytest.main(case_path="test_case/test_douban_case")
    except SystemExit as exc:
        assert exc.code == 0

    assert "--clean-alluredir" in commands[0]
