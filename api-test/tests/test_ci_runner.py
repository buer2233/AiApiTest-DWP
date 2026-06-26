import json
import subprocess
import sys

import pytest

from tools import ci_runner


def write_lastfailed(api_test_root, payload):
    cache_file = api_test_root / ".pytest_cache" / "v" / "cache" / "lastfailed"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return cache_file


def test_build_pytest_command_for_module_run(tmp_path):
    allure_results_dir = tmp_path / "runtime" / "ci-runs" / "run-1" / "allure-results"

    command = ci_runner.build_pytest_command(
        targets=["test_case/test_gbif_case"],
        allure_results_dir=allure_results_dir,
        clean=True,
        retry_count=0,
        python_executable="python",
    )

    assert command == [
        "python",
        "-m",
        "pytest",
        "test_case/test_gbif_case",
        f"--alluredir={allure_results_dir}",
        "--clean-alluredir",
    ]


def test_build_pytest_command_for_selected_nodeids_with_rerun_count(tmp_path):
    allure_results_dir = tmp_path / "runtime" / "ci-runs" / "run-1" / "allure-results"
    nodeids = [
        "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword",
        "test_case/test_demo.py::TestDemo::test_param[a/b]",
    ]

    command = ci_runner.build_pytest_command(
        targets=nodeids,
        allure_results_dir=allure_results_dir,
        clean=False,
        retry_count=2,
        python_executable="python",
    )

    assert command == [
        "python",
        "-m",
        "pytest",
        *nodeids,
        f"--alluredir={allure_results_dir}",
        "--reruns",
        "2",
    ]


def test_build_pytest_command_rejects_negative_rerun_count(tmp_path):
    with pytest.raises(ValueError, match="retry_count"):
        ci_runner.build_pytest_command(
            targets=["test_case/test_gbif_case"],
            allure_results_dir=tmp_path / "allure-results",
            retry_count=-1,
        )


def test_run_ci_tests_defaults_to_current_python_interpreter(tmp_path, monkeypatch):
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(ci_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    ci_runner.run_ci_tests(request)

    assert calls["command"][0] == sys.executable


def test_resolve_all_failed_targets_reads_pytest_lastfailed_cache(tmp_path):
    first = "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword"
    second = "test_case/test_demo.py::TestDemo::test_param[a/b]"
    write_lastfailed(tmp_path, {first: True, second: True})
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="all-failed",
        case_path="test_case/test_gbif_case",
    )

    assert ci_runner.resolve_pytest_targets(request) == [first, second]


def test_resolve_selected_targets_uses_explicit_nodeids(tmp_path):
    nodeids = [
        "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword",
        "test_case/test_demo.py::TestDemo::test_param[a/b]",
    ]
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="selected",
        case_path="test_case/test_gbif_case",
        node_ids=nodeids,
    )

    assert ci_runner.resolve_pytest_targets(request) == nodeids


def test_parse_jenkins_node_ids_accepts_newlines_and_commas():
    raw_node_ids = """
    test_case/test_demo.py::TestDemo::test_one,
    test_case/test_demo.py::TestDemo::test_two
    test_case/test_demo.py::TestDemo::test_three,
    test_case/test_demo.py::TestDemo::test_two
    """

    assert ci_runner.parse_jenkins_node_ids(raw_node_ids) == [
        "test_case/test_demo.py::TestDemo::test_one",
        "test_case/test_demo.py::TestDemo::test_two",
        "test_case/test_demo.py::TestDemo::test_three",
    ]


def test_build_run_request_from_jenkins_env_uses_pipeline_parameters(tmp_path):
    env = {
        "CASE_PATH": "test_case/test_gbif_case",
        "PYTEST_NODE_IDS": "test_case/test_demo.py::TestDemo::test_one,\n"
        "test_case/test_demo.py::TestDemo::test_two",
        "RETRY_MODE": "all-failed",
        "RETRY_COUNT": "1",
        "CLEAN_ALLURE": "false",
        "OPEN_REPORT": "true",
        "RUN_ID": "jenkins-demo-12",
    }

    request = ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)

    assert request.api_test_root == tmp_path
    assert request.run_dir == tmp_path / "runtime" / "ci-runs" / "jenkins-demo-12"
    assert request.case_path == "test_case/test_gbif_case"
    assert request.node_ids == [
        "test_case/test_demo.py::TestDemo::test_one",
        "test_case/test_demo.py::TestDemo::test_two",
    ]
    assert request.retry_mode == "all-failed"
    assert request.retry_count == 1
    assert request.clean is False
    assert request.open_report is True


def test_write_summary_creates_required_summary_json(tmp_path):
    run_dir = tmp_path / "runtime" / "ci-runs" / "run-1"
    failed_nodeids = [
        "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword"
    ]

    summary = ci_runner.write_summary(
        run_dir=run_dir,
        return_code=1,
        failed_nodeids=failed_nodeids,
        allure_results_dir=run_dir / "allure-results",
        allure_report_dir=run_dir / "allure-report",
    )

    expected = {
        "status": "failed",
        "return_code": 1,
        "failed_nodeids": failed_nodeids,
        "allure_results_dir": str(run_dir / "allure-results"),
        "allure_report_dir": str(run_dir / "allure-report"),
        "allure_report_status": "unknown",
        "allure_report_message": "",
    }
    assert summary == expected
    assert json.loads((run_dir / "summary.json").read_text(encoding="utf-8")) == expected


def test_run_ci_tests_executes_pytest_and_writes_artifacts(tmp_path, monkeypatch):
    nodeid = "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_species_search_by_keyword"
    write_lastfailed(tmp_path, {nodeid: True})
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="selected",
        case_path="test_case/test_gbif_case",
        node_ids=[nodeid],
        clean=True,
    )
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        write_lastfailed(tmp_path, {nodeid: True})
        return subprocess.CompletedProcess(command, 1, stdout="pytest stdout", stderr="pytest stderr")

    monkeypatch.setattr(ci_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert calls["command"] == [
        "python",
        "-m",
        "pytest",
        nodeid,
        f"--alluredir={request.run_dir / 'allure-results'}",
        "--clean-alluredir",
    ]
    assert calls["kwargs"]["cwd"] == str(tmp_path)
    assert (request.run_dir / "console.log").read_text(encoding="utf-8") == "pytest stdout\npytest stderr"
    assert json.loads((request.run_dir / "failed_nodeids.json").read_text(encoding="utf-8")) == [nodeid]
    assert summary["status"] == "failed"
    assert summary["return_code"] == 1
    assert summary["failed_nodeids"] == [nodeid]


def test_run_ci_tests_clears_stale_lastfailed_before_current_pytest_run(tmp_path, monkeypatch):
    stale_nodeid = "test_case/old_case/test_old_api.py::TestOldAPI::test_old_failure"
    write_lastfailed(tmp_path, {stale_nodeid: True})
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="pytest stdout", stderr="")

    monkeypatch.setattr(ci_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert json.loads((request.run_dir / "failed_nodeids.json").read_text(encoding="utf-8")) == []
    assert summary["status"] == "passed"
    assert summary["failed_nodeids"] == []


def test_run_ci_tests_records_skipped_allure_report_when_cli_is_missing(tmp_path, monkeypatch):
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )

    def fake_run(command, **kwargs):
        (request.run_dir / "allure-results" / "result.json").write_text(
            "{}",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="pytest stdout", stderr="")

    monkeypatch.setattr(ci_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert summary["status"] == "passed"
    assert summary["allure_report_status"] == "skipped"
    assert "Allure CLI" in summary["allure_report_message"]


def test_main_returns_success_for_pytest_failures_in_jenkins_env(tmp_path, monkeypatch):
    """Jenkins 环境下 pytest 用例失败应只进入报告摘要，不应使 Pipeline stage 失败。"""
    env = {
        "CI_RUNNER_ENV": "jenkins",
        "CASE_PATH": "test_case/test_gbif_case",
        "RETRY_MODE": "module",
        "RUN_ID": "jenkins-demo-failed-tests",
    }
    captured = {}

    def fake_build_request(source, api_test_root):
        return ci_runner.RunRequest(
            api_test_root=tmp_path,
            run_dir=tmp_path / "runtime" / "ci-runs" / source["RUN_ID"],
            retry_mode=source["RETRY_MODE"],
            case_path=source["CASE_PATH"],
        )

    def fake_run_ci_tests(request):
        captured["request"] = request
        return {
            "status": "failed",
            "return_code": 1,
            "failed_nodeids": [
                "test_case/test_gbif_case/test_gbif_api_module2.py::TestGbifAPI::test_intentional_failure"
            ],
            "allure_report_status": "generated",
            "allure_report_message": "Allure HTML report generated successfully.",
        }

    monkeypatch.setattr(ci_runner, "build_run_request_from_jenkins_env", fake_build_request)
    monkeypatch.setattr(ci_runner, "run_ci_tests", fake_run_ci_tests)
    monkeypatch.setattr(ci_runner.os, "environ", env)

    exit_code = ci_runner.main(["--from-jenkins-env"])

    assert exit_code == 0
    assert captured["request"].run_dir == tmp_path / "runtime" / "ci-runs" / "jenkins-demo-failed-tests"
