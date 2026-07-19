import json
import os
import subprocess
import sys
import threading
import time

import pytest

from tools import ci_runner
from tools.environment_catalog import EnvironmentCatalogValidationError
from tools.sensitive_data import redact_sensitive_text


def write_lastfailed(api_test_root, payload):
    cache_file = api_test_root / ".pytest_cache" / "v" / "cache" / "lastfailed"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return cache_file


def write_case_results(run_dir, payload):
    output_path = run_dir / "case_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return output_path


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
        "-vv",
        "test_case/test_gbif_case",
        f"--alluredir={allure_results_dir}",
        "-p",
        "tools.pytest_case_reporter",
        f"--ci-case-results={allure_results_dir.parent / 'case_results.json'}",
        "-o",
        f"cache_dir={allure_results_dir.parent / '.pytest_cache'}",
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
        "-vv",
        *nodeids,
        f"--alluredir={allure_results_dir}",
        "-p",
        "tools.pytest_case_reporter",
        f"--ci-case-results={allure_results_dir.parent / 'case_results.json'}",
        "-o",
        f"cache_dir={allure_results_dir.parent / '.pytest_cache'}",
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


def test_build_pytest_command_passes_normalized_base_url_to_pytest(tmp_path):
    """Daily Worker 必须复用既有 --base-url 覆盖机制。"""
    allure_results_dir = tmp_path / "runtime" / "ci-runs" / "run-base-url" / "allure-results"

    command = ci_runner.build_pytest_command(
        targets=["test_case/test_gbif_case"],
        allure_results_dir=allure_results_dir,
        base_url="https://stage13-qa.example.invalid/api/",
    )

    assert command[-2:] == ["--base-url", "https://stage13-qa.example.invalid/api"]


def _write_environment_catalog(api_test_root, yaml_content):
    catalog_path = api_test_root / "utils" / "package_environment.yaml"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(yaml_content, encoding="utf-8")


def test_build_run_request_from_jenkins_env_normalizes_target_base_url(tmp_path):
    """Jenkins 传入的目标 URL 必须在执行前完成既有规则校验和规范化。"""
    env = {
        "RETRY_MODE": "module",
        "RUN_ID": "stage13-target-base-url",
        "TARGET_BASE_URL": "https://stage13-qa.example.invalid/api/",
    }
    _write_environment_catalog(
        tmp_path,
        """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
""".lstrip(),
    )

    request = ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)

    assert request.base_url == "https://stage13-qa.example.invalid/api"


@pytest.mark.parametrize(
    "target_base_url",
    [
        "https://unregistered.example.invalid/api",
        "https://user:password@stage13-qa.example.invalid/api",
    ],
)
def test_build_run_request_from_jenkins_env_rejects_unregistered_target_base_url(tmp_path, target_base_url):
    _write_environment_catalog(
        tmp_path,
        """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
""".lstrip(),
    )
    env = {
        "RETRY_MODE": "module",
        "RUN_ID": "stage13-unregistered-target",
        "TARGET_BASE_URL": target_base_url,
    }

    with pytest.raises(ValueError, match="registered environment"):
        ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)


def test_build_run_request_from_jenkins_env_rejects_invalid_environment_catalog(tmp_path):
    _write_environment_catalog(
        tmp_path,
        """
stage13-qa:
  base_url: https://stage13-qa.example.invalid/api
  url_name: Stage13 QA
  url_desc: 自动化回归测试环境
  secret_hint: forbidden
""".lstrip(),
    )
    env = {
        "RETRY_MODE": "module",
        "RUN_ID": "stage13-invalid-catalog",
        "TARGET_BASE_URL": "https://stage13-qa.example.invalid/api",
    }

    with pytest.raises(EnvironmentCatalogValidationError) as exc_info:
        ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)

    assert exc_info.value.code == "unknown_environment_field"


def test_build_run_request_from_jenkins_env_keeps_empty_target_base_url_as_default(tmp_path):
    """空 TARGET_BASE_URL 必须继续使用私有配置默认值，避免改变既有调用。"""
    env = {
        "RETRY_MODE": "module",
        "RUN_ID": "stage13-default-base-url",
        "TARGET_BASE_URL": " ",
    }

    request = ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)

    assert request.base_url is None


def test_run_ci_tests_defaults_to_current_python_interpreter(tmp_path, monkeypatch):
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )
    calls = {}

    def fake_stream(command, **kwargs):
        calls["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(ci_runner, "run_pytest_streaming", fake_stream)
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


def test_resolve_all_failed_targets_prefers_latest_ci_run_artifact(tmp_path):
    stale = "test_case/test_old.py::test_old"
    latest = "test_case/test_latest.py::test_latest"
    write_lastfailed(tmp_path, {stale: True})
    old_run = tmp_path / "runtime" / "ci-runs" / "old"
    latest_run = tmp_path / "runtime" / "ci-runs" / "latest"
    ci_runner.write_nodeids([stale], old_run / "failed_nodeids.json")
    ci_runner.write_nodeids([latest], latest_run / "failed_nodeids.json")
    now = time.time()
    os.utime(old_run, (now - 10, now - 10))
    os.utime(latest_run, (now, now))
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "next",
        retry_mode="all-failed",
    )

    assert ci_runner.resolve_pytest_targets(request) == [latest]


def test_resolve_all_failed_targets_accepts_empty_latest_ci_run_artifact(tmp_path):
    """最新执行已全通过时，不得回退读取共享根 cache 中的历史失败项。"""
    stale = "test_case/test_old.py::test_old"
    write_lastfailed(tmp_path, {stale: True})
    latest_run = tmp_path / "runtime" / "ci-runs" / "latest-passed"
    ci_runner.write_nodeids([], latest_run / "failed_nodeids.json")
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "next",
        retry_mode="all-failed",
    )

    assert ci_runner.resolve_pytest_targets(request) == []


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
    assert request.open_report is False


def test_build_run_request_from_jenkins_env_ignores_open_report_to_prevent_ci_hang(tmp_path):
    """Jenkins 环境即使传入 OPEN_REPORT=true，也不能启动 allure open 常驻服务。"""
    env = {
        "CI_RUNNER_ENV": "jenkins",
        "CASE_PATH": "test_case/test_gbif_case",
        "RETRY_MODE": "none",
        "OPEN_REPORT": "true",
        "RUN_ID": "jenkins-demo-open-report",
    }

    request = ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)

    assert request.open_report is False


def test_build_run_request_from_jenkins_env_uses_default_report_retention_days(tmp_path):
    """Jenkins 默认仅清理超过 30 天的本地 runtime 历史报告。"""
    env = {
        "CI_RUNNER_ENV": "jenkins",
        "CASE_PATH": "test_case/test_gbif_case",
        "RETRY_MODE": "none",
        "RUN_ID": "jenkins-demo-retention-default",
    }

    request = ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)

    assert request.retention_days == 30


def test_build_run_request_from_jenkins_env_uses_configured_report_retention_days(tmp_path):
    """Jenkins 可通过 CI_RUN_RETENTION_DAYS 调整 runtime 历史报告保留天数。"""
    env = {
        "CI_RUNNER_ENV": "jenkins",
        "CASE_PATH": "test_case/test_gbif_case",
        "RETRY_MODE": "none",
        "RUN_ID": "jenkins-demo-retention-configured",
        "CI_RUN_RETENTION_DAYS": "45",
    }

    request = ci_runner.build_run_request_from_jenkins_env(env, api_test_root=tmp_path)

    assert request.retention_days == 45


def test_cleanup_old_ci_runs_removes_only_runs_older_than_retention(tmp_path):
    ci_runs_dir = tmp_path / "runtime" / "ci-runs"
    current_run = ci_runs_dir / "current"
    old_run = ci_runs_dir / "old"
    boundary_run = ci_runs_dir / "boundary"
    recent_run = ci_runs_dir / "recent"
    non_run_file = ci_runs_dir / "README.txt"
    for path in [current_run, old_run, boundary_run, recent_run]:
        path.mkdir(parents=True)
        (path / "summary.json").write_text("{}", encoding="utf-8")
    non_run_file.write_text("keep", encoding="utf-8")
    now = time.time()
    os.utime(old_run, (now - 31 * 24 * 60 * 60, now - 31 * 24 * 60 * 60))
    os.utime(boundary_run, (now - 30 * 24 * 60 * 60, now - 30 * 24 * 60 * 60))
    os.utime(recent_run, (now - 5 * 24 * 60 * 60, now - 5 * 24 * 60 * 60))
    os.utime(current_run, (now - 90 * 24 * 60 * 60, now - 90 * 24 * 60 * 60))

    removed = ci_runner.cleanup_old_ci_runs(
        api_test_root=tmp_path,
        current_run_dir=current_run,
        retention_days=30,
        now=now,
    )

    assert removed == [old_run]
    assert not old_run.exists()
    assert boundary_run.exists()
    assert recent_run.exists()
    assert current_run.exists()
    assert non_run_file.exists()


def test_cleanup_old_ci_runs_tolerates_concurrent_deletion(tmp_path, monkeypatch):
    old_run = tmp_path / "runtime" / "ci-runs" / "old"
    current_run = tmp_path / "runtime" / "ci-runs" / "current"
    old_run.mkdir(parents=True)
    current_run.mkdir(parents=True)
    now = time.time()
    os.utime(old_run, (now - 40 * 24 * 60 * 60, now - 40 * 24 * 60 * 60))

    def already_removed(path):
        path.rmdir()
        raise FileNotFoundError(path)

    monkeypatch.setattr(ci_runner.shutil, "rmtree", already_removed)

    assert ci_runner.cleanup_old_ci_runs(tmp_path, current_run, retention_days=30, now=now) == []


def test_parse_args_preserves_local_open_report_option():
    """本地命令行显式 --open-report 仍保留，限制只作用于 Jenkins env 模式。"""
    args = ci_runner.parse_args(["--open-report"])

    assert args.open_report is True


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
        "case_results": [],
        "error_count": 0,
    }
    assert summary == expected
    assert json.loads((run_dir / "summary.json").read_text(encoding="utf-8")) == expected


def test_parse_pytest_summary_counts_from_console_output():
    console_output = """
    ============================= test session starts =============================
    =============== 1 failed, 2 passed, 1 skipped, 1 error in 12.34s ===============
    """

    assert ci_runner.parse_pytest_summary_counts(console_output) == {
        "total_count": 5,
        "failed_count": 2,
        "error_count": 1,
        "passed_count": 2,
        "skipped_count": 1,
        "duration_seconds": 12.34,
    }


def test_run_ci_tests_writes_count_fields_into_summary(tmp_path, monkeypatch):
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-counts",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )

    def fake_stream(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="================ 1 failed, 2 passed, 1 skipped in 12.34s ================\n",
            stderr="",
        )

    monkeypatch.setattr(ci_runner, "run_pytest_streaming", fake_stream)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert summary["total_count"] == 4
    assert summary["failed_count"] == 1
    assert summary["error_count"] == 0
    assert summary["passed_count"] == 2
    assert summary["skipped_count"] == 1
    assert summary["duration_seconds"] == 12.34


def test_run_ci_tests_writes_failure_summary_when_pytest_times_out(tmp_path, monkeypatch):
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-timeout",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )

    def fake_stream(command, **kwargs):
        raise subprocess.TimeoutExpired(
            command,
            timeout=kwargs.get("timeout"),
            output="pytest partial stdout",
            stderr="pytest partial stderr",
        )

    monkeypatch.setattr(ci_runner, "run_pytest_streaming", fake_stream)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert summary["status"] == "failed"
    assert summary["return_code"] == 124
    assert summary["failed_nodeids"] == []
    assert summary["allure_report_status"] == "skipped"
    assert "timed out" in summary["allure_report_message"]
    assert json.loads((request.run_dir / "failed_nodeids.json").read_text(encoding="utf-8")) == []
    console_log = (request.run_dir / "console.log").read_text(encoding="utf-8")
    assert "pytest partial stdout" in console_log
    assert "pytest partial stderr" in console_log
    assert "timed out" in console_log


def test_run_ci_tests_records_failed_allure_report_when_generation_times_out(tmp_path, monkeypatch):
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-allure-timeout",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )
    calls = []

    def fake_stream(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="1 passed in 0.01s", stderr="")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        raise subprocess.TimeoutExpired(command, timeout=kwargs.get("timeout"), output="", stderr="")

    monkeypatch.setattr(ci_runner, "run_pytest_streaming", fake_stream)
    monkeypatch.setattr(ci_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: "allure")

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert calls[0][1]["timeout"] == ci_runner.DEFAULT_PYTEST_TIMEOUT_SECONDS
    assert calls[1][1]["timeout"] == ci_runner.DEFAULT_ALLURE_TIMEOUT_SECONDS
    assert summary["status"] == "passed"
    assert summary["allure_report_status"] == "failed"
    assert "timed out" in summary["allure_report_message"]
    console_log = (request.run_dir / "console.log").read_text(encoding="utf-8")
    assert "Allure HTML report generation timed out" in console_log


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

    def fake_stream(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        write_case_results(
            request.run_dir,
            [
                {
                    "node_id": nodeid,
                    "case_name": "test_species_search_by_keyword",
                    "execution_status": "failed",
                    "duration_seconds": 0.1,
                    "error_type": "AssertionError",
                    "error_message_summary": "expected species",
                }
            ],
        )
        return subprocess.CompletedProcess(command, 1, stdout="pytest stdout", stderr="pytest stderr")

    monkeypatch.setattr(ci_runner, "run_pytest_streaming", fake_stream)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert calls["command"] == [
        "python",
        "-m",
        "pytest",
        "-vv",
        nodeid,
        f"--alluredir={request.run_dir / 'allure-results'}",
        "-p",
        "tools.pytest_case_reporter",
        f"--ci-case-results={request.run_dir / 'case_results.json'}",
        "-o",
        f"cache_dir={request.run_dir / '.pytest_cache'}",
        "--clean-alluredir",
    ]
    assert calls["kwargs"]["cwd"] == str(tmp_path)
    assert (request.run_dir / "console.log").read_text(encoding="utf-8") == "pytest stdout\npytest stderr"
    assert json.loads((request.run_dir / "failed_nodeids.json").read_text(encoding="utf-8")) == [nodeid]
    assert summary["status"] == "failed"
    assert summary["return_code"] == 1
    assert summary["failed_nodeids"] == [nodeid]
    assert summary["case_results"][0]["execution_status"] == "failed"


def test_run_ci_tests_ignores_shared_stale_lastfailed_after_current_pytest_run(tmp_path, monkeypatch):
    stale_nodeid = "test_case/old_case/test_old_api.py::TestOldAPI::test_old_failure"
    write_lastfailed(tmp_path, {stale_nodeid: True})
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "run-1",
        retry_mode="module",
        case_path="test_case/test_gbif_case",
        clean=True,
    )

    def fake_stream(command, **kwargs):
        write_case_results(request.run_dir, [])
        return subprocess.CompletedProcess(command, 0, stdout="pytest stdout", stderr="")

    monkeypatch.setattr(ci_runner, "run_pytest_streaming", fake_stream)
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

    def fake_stream(command, **kwargs):
        (request.run_dir / "allure-results" / "result.json").write_text(
            "{}",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="pytest stdout", stderr="")

    monkeypatch.setattr(ci_runner, "run_pytest_streaming", fake_stream)
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable="python")

    assert summary["status"] == "passed"
    assert summary["allure_report_status"] == "skipped"
    assert "Allure CLI" in summary["allure_report_message"]


def test_run_pytest_streaming_writes_first_line_before_process_finishes(tmp_path, capsys):
    """pytest 子进程尚未结束时，首行输出已进入 console.log 和当前控制台。"""
    run_dir = tmp_path / "runtime" / "ci-runs" / "streaming"
    run_dir.mkdir(parents=True)
    result_holder = {}

    def invoke_runner():
        result_holder["result"] = ci_runner.run_pytest_streaming(
            [
                sys.executable,
                "-c",
                "import time; print('first-line', flush=True); time.sleep(0.5); print('second-line', flush=True)",
            ],
            cwd=tmp_path,
            run_dir=run_dir,
            timeout=5,
        )

    thread = threading.Thread(target=invoke_runner)
    thread.start()
    console_path = run_dir / "console.log"
    deadline = time.time() + 2
    while time.time() < deadline:
        if console_path.exists() and "first-line" in console_path.read_text(encoding="utf-8"):
            break
        time.sleep(0.02)

    assert thread.is_alive()
    assert "first-line" in console_path.read_text(encoding="utf-8")
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert result_holder["result"].returncode == 0
    assert "second-line" in result_holder["result"].stdout
    assert "first-line" in capsys.readouterr().out


def test_run_pytest_streaming_forces_unbuffered_child_output(tmp_path, monkeypatch):
    """pytest 写入管道时必须禁用 Python 缓冲，保证 Jenkins 能及时收到逐行输出。"""
    captured = {}

    class EmptyStdout:
        def readline(self):
            return ""

    class FakeProcess:
        stdout = EmptyStdout()

        def wait(self, timeout=None):
            return 0

    def fake_popen(command, **kwargs):
        captured.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(ci_runner.subprocess, "Popen", fake_popen)

    result = ci_runner.run_pytest_streaming(
        [sys.executable, "-m", "pytest"],
        cwd=tmp_path,
        run_dir=tmp_path / "run",
        timeout=5,
    )

    assert result.returncode == 0
    assert captured["env"]["PYTHONUNBUFFERED"] == "1"


def test_run_pytest_streaming_closes_stdout_when_reader_survives_process_exit(tmp_path, monkeypatch):
    """pytest 主进程退出后仍有写端存活时，必须清理进程组并关闭读取管道。"""
    terminated = []
    join_calls = []

    class BlockingStdout:
        closed = False

        def close(self):
            self.closed = True

    class FakeProcess:
        stdout = BlockingStdout()
        pid = 321

        def wait(self, timeout=None):
            return 0

        def kill(self):
            return None

    class FakeReader:
        def __init__(self, *args, **kwargs):
            return None

        def start(self):
            return None

        def join(self, timeout=None):
            join_calls.append(timeout)

        def is_alive(self):
            return not process.stdout.closed

    process = FakeProcess()
    monkeypatch.setattr(ci_runner.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(ci_runner.threading, "Thread", FakeReader)
    monkeypatch.setattr(ci_runner, "_terminate_process_tree", lambda value: terminated.append(value))

    result = ci_runner.run_pytest_streaming(
        [sys.executable, "-m", "pytest"],
        cwd=tmp_path,
        run_dir=tmp_path / "run-reader-cleanup",
        timeout=5,
    )

    assert result.returncode == 0
    assert terminated == [process]
    assert process.stdout.closed is True
    assert len(join_calls) == 2


def test_run_pytest_streaming_terminates_process_tree_on_timeout(tmp_path, monkeypatch):
    terminated = []

    class EmptyStdout:
        def readline(self):
            return ""

        def close(self):
            return None

    class FakeProcess:
        stdout = EmptyStdout()
        pid = 123
        wait_count = 0

        def wait(self, timeout=None):
            self.wait_count += 1
            if self.wait_count == 1:
                raise subprocess.TimeoutExpired(["pytest"], timeout)
            return 1

        def kill(self):
            return None

    process = FakeProcess()
    monkeypatch.setattr(ci_runner.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(ci_runner, "_terminate_process_tree", lambda value: terminated.append(value))

    with pytest.raises(subprocess.TimeoutExpired):
        ci_runner.run_pytest_streaming(
            [sys.executable, "-m", "pytest"],
            cwd=tmp_path,
            run_dir=tmp_path / "run-timeout-tree",
            timeout=1,
        )

    assert terminated == [process]


def test_run_pytest_streaming_redacts_sensitive_console_values(tmp_path):
    secret = "correct horse battery staple"
    result = ci_runner.run_pytest_streaming(
        [
            sys.executable,
            "-c",
            (
                "print('Authorization: Bearer " + secret + "', flush=True); "
                "print('Cookie: session=" + secret + "', flush=True); "
                "print('{\"password\": \"" + secret + "\"}', flush=True)"
            ),
        ],
        cwd=tmp_path,
        run_dir=tmp_path / "run-redacted",
        timeout=5,
    )

    console = (tmp_path / "run-redacted" / "console.log").read_text(encoding="utf-8")
    assert secret not in result.stdout
    assert secret not in console
    assert "[REDACTED]" in console


@pytest.mark.parametrize(
    "raw_value",
    [
        'password="correct horse battery staple"',
        "'password': 'correct horse battery staple'",
        r'password=\"correct horse battery staple\"',
        r'{"password": "correct \"horse\" battery staple"}',
        "api_token=stage10-secret-value",
    ],
)
def test_redact_sensitive_text_removes_complete_sensitive_values(raw_value):
    redacted = redact_sensitive_text(raw_value)

    assert "correct" not in redacted
    assert "battery" not in redacted
    assert "stage10-secret-value" not in redacted
    assert "[REDACTED]" in redacted


@pytest.mark.parametrize("run_id", ["../escape", "a/b", "a\\b", "C:\\absolute", "."])
def test_build_run_dir_rejects_unsafe_run_id(tmp_path, run_id):
    with pytest.raises(ValueError, match="run_id"):
        ci_runner.build_run_dir(tmp_path, run_id)


def test_run_ci_tests_rejects_duplicate_run_directory(tmp_path):
    run_dir = tmp_path / "runtime" / "ci-runs" / "duplicate"
    run_dir.mkdir(parents=True)
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=run_dir,
        retry_mode="module",
        case_path="test_case",
    )

    with pytest.raises(FileExistsError, match="already exists"):
        ci_runner.run_ci_tests(request)


def test_run_ci_tests_collects_complete_case_results_from_real_pytest(tmp_path, monkeypatch):
    """真实 pytest 执行必须输出 passed/failed/skipped/error 的最终 node id 明细。"""
    test_file = tmp_path / "test_case_results_sample.py"
    test_file.write_text(
        """
import pytest

@pytest.fixture
def broken_fixture():
    raise RuntimeError("fixture boom")

def test_passed():
    assert True

def test_failed():
    assert False, "expected failure"

@pytest.mark.skip(reason="not ready")
def test_skipped():
    pass

def test_error(broken_fixture):
    pass

@pytest.fixture
def teardown_fixture():
    yield
    raise RuntimeError("teardown boom")

def test_teardown_error(teardown_fixture):
    assert True
""".strip(),
        encoding="utf-8",
    )
    collection_skip_file = tmp_path / "test_collection_skip_sample.py"
    collection_skip_file.write_text(
        'import pytest\npytest.importorskip("stage10_missing_optional_dependency")\n',
        encoding="utf-8",
    )
    request = ci_runner.RunRequest(
        api_test_root=tmp_path,
        run_dir=tmp_path / "runtime" / "ci-runs" / "real-case-results",
        retry_mode="module",
        case_path=".",
        clean=True,
    )
    monkeypatch.setattr(ci_runner.shutil, "which", lambda name: None)

    summary = ci_runner.run_ci_tests(request, python_executable=sys.executable)

    by_name = {item["case_name"]: item for item in summary["case_results"]}
    assert {item["execution_status"] for item in summary["case_results"]} == {
        "passed",
        "failed",
        "skipped",
        "error",
    }
    assert summary["total_count"] == 6
    assert summary["failed_count"] == 3
    assert summary["passed_count"] == 1
    assert summary["skipped_count"] == 2
    assert by_name["test_failed"]["node_id"].endswith("::test_failed")
    assert by_name["test_error"]["error_type"] == "RuntimeError"
    assert by_name["test_teardown_error"]["execution_status"] == "error"
    assert any(item["execution_status"] == "skipped" and "collection_skip" in item["node_id"] for item in summary["case_results"])
    assert set(summary["failed_nodeids"]) == {
        by_name["test_failed"]["node_id"],
        by_name["test_error"]["node_id"],
        by_name["test_teardown_error"]["node_id"],
    }


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
