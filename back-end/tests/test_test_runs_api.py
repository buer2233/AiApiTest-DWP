"""测试任务与失败用例 API 测试。
本文件用 fake api-test runner 验证任务创建、列表详情、失败用例查询、三类重试和 Allure 报告访问。
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.test_runs.models import FailureCase as FailureCaseModel
from apps.test_runs.models import TestRun as TestRunModel


pytestmark = pytest.mark.django_db


class FakeApiTestRunner:
    """用于替代真实 api-test 执行器的测试替身。
    记录调用参数，并按重试模式返回固定 summary，避免 API 测试启动真实 pytest。
    """

    calls = []

    @classmethod
    def reset(cls):
        """清空执行器调用记录。"""
        cls.calls = []

    @classmethod
    def run(cls, *, case_path, node_ids=None, retry_mode="none", retry_count=0):
        """模拟 api-test runner 执行结果。
        Args:
            case_path: 测试模块路径。
            node_ids: 指定重跑的 pytest node id。
            retry_mode: 重试模式。
            retry_count: 重试次数。
        Returns:
            dict: 与真实 runner summary 兼容的执行摘要。
        """
        cls.calls.append(
            {
                "case_path": case_path,
                "node_ids": list(node_ids or []),
                "retry_mode": retry_mode,
                "retry_count": retry_count,
            }
        )
        suffix = len(cls.calls)
        status = "failed" if retry_mode == "none" else "passed"
        failed_nodeids = (
            ["test_case/test_gbif_case/test_gbif_api.py::test_species_search"]
            if retry_mode == "none"
            else []
        )
        return {
            "run_id": f"fake-run-{suffix}",
            "status": status,
            "return_code": 1 if status == "failed" else 0,
            "case_path": case_path,
            "node_ids": list(node_ids or []),
            "retry_mode": retry_mode,
            "retry_count": retry_count,
            "failed_nodeids": failed_nodeids,
            "allure_results_dir": f"/tmp/fake-run-{suffix}/allure-results",
            "allure_report_dir": f"/tmp/fake-run-{suffix}/allure-report",
            "console_log_path": f"/tmp/fake-run-{suffix}/console.log",
        }


def create_user(username="stage6-user", role="member"):
    """创建测试任务 API 测试用户。"""
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        password="local-test-pass",
        role=role,
    )


def authenticated_client(user=None):
    """返回已认证的 DRF APIClient。"""
    client = APIClient()
    client.force_authenticate(user=user or create_user())
    return client


@pytest.fixture(autouse=True)
def fake_runner(monkeypatch):
    """自动把视图层 ApiTestRunner 替换为 fake 实现。"""
    FakeApiTestRunner.reset()
    monkeypatch.setattr(
        "apps.test_runs.views.ApiTestRunner",
        FakeApiTestRunner,
    )


def test_create_test_run_records_summary_and_failure_cases():
    """验证创建测试任务会保存 summary 并登记失败用例。"""
    client = authenticated_client()

    response = client.post(
        "/api/test-runs/",
        {
            "case_path": "test_case/test_gbif_case",
            "retry_mode": "none",
            "retry_count": 0,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["run_id"] == "fake-run-1"
    assert response.data["status"] == "failed"
    assert response.data["case_path"] == "test_case/test_gbif_case"
    assert response.data["trigger_source"] == "api"
    assert response.data["triggered_by"]["username"] == "stage6-user"
    assert response.data["summary"]["return_code"] == 1
    assert response.data["failure_count"] == 1

    test_run = TestRunModel.objects.get(run_id="fake-run-1")
    failure = FailureCaseModel.objects.get(test_run=test_run)
    assert failure.node_id == "test_case/test_gbif_case/test_gbif_api.py::test_species_search"
    assert failure.case_name == "test_species_search"
    assert failure.module_path == "test_case/test_gbif_case"
    assert failure.status == "failed"


def test_list_and_detail_test_runs():
    """验证测试任务列表和详情接口返回任务摘要与失败数量。"""
    user = create_user("list-user")
    test_run = TestRunModel.objects.create(
        run_id="stored-run",
        case_path="test_case/test_gbif_case",
        retry_mode=TestRunModel.RetryMode.NONE,
        retry_count=0,
        status=TestRunModel.Status.FAILED,
        triggered_by=user,
        trigger_source=TestRunModel.TriggerSource.API,
        summary={"return_code": 1},
    )
    FailureCaseModel.objects.create(
        test_run=test_run,
        node_id="test_case/test_gbif_case/test_gbif_api.py::test_species_search",
        case_name="test_species_search",
        module_path="test_case/test_gbif_case",
        status=FailureCaseModel.Status.FAILED,
    )
    client = authenticated_client(user)

    list_response = client.get("/api/test-runs/")
    detail_response = client.get(f"/api/test-runs/{test_run.id}/")

    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert list_response.data["results"][0]["run_id"] == "stored-run"
    assert list_response.data["results"][0]["failure_count"] == 1
    assert detail_response.status_code == 200
    assert detail_response.data["id"] == test_run.id
    assert detail_response.data["summary"] == {"return_code": 1}


def test_failure_cases_endpoint_returns_failures_for_run():
    """验证失败用例接口只返回指定任务下的失败用例。"""
    user = create_user("failure-user")
    test_run = TestRunModel.objects.create(
        run_id="failure-run",
        case_path="test_case/test_gbif_case",
        retry_mode=TestRunModel.RetryMode.NONE,
        status=TestRunModel.Status.FAILED,
        triggered_by=user,
    )
    FailureCaseModel.objects.create(
        test_run=test_run,
        node_id="test_case/test_gbif_case/test_gbif_api.py::test_species_search",
        case_name="test_species_search",
        module_path="test_case/test_gbif_case",
        description="Search species by keyword",
        error_type="AssertionError",
        assertion_message="expected 200",
        status=FailureCaseModel.Status.FAILED,
    )
    client = authenticated_client(user)

    response = client.get(f"/api/test-runs/{test_run.id}/failures/")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["node_id"].endswith("::test_species_search")
    assert response.data["results"][0]["error_type"] == "AssertionError"


def test_retry_selected_failure_cases_creates_retry_run_and_marks_retry_status():
    """验证选择失败用例重试会创建子任务并回写重试状态。"""
    user = create_user("retry-selected-user")
    original = TestRunModel.objects.create(
        run_id="original-selected",
        case_path="test_case/test_gbif_case",
        retry_mode=TestRunModel.RetryMode.NONE,
        status=TestRunModel.Status.FAILED,
        triggered_by=user,
    )
    failure = FailureCaseModel.objects.create(
        test_run=original,
        node_id="test_case/test_gbif_case/test_gbif_api.py::test_species_search",
        case_name="test_species_search",
        module_path="test_case/test_gbif_case",
        status=FailureCaseModel.Status.FAILED,
    )
    client = authenticated_client(user)

    response = client.post(
        f"/api/test-runs/{original.id}/retry-selected/",
        {"failure_ids": [failure.id], "retry_count": 1},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["retry_mode"] == "selected"
    assert response.data["node_ids"] == [failure.node_id]
    assert FakeApiTestRunner.calls[-1] == {
        "case_path": "test_case/test_gbif_case",
        "node_ids": [failure.node_id],
        "retry_mode": "selected",
        "retry_count": 1,
    }
    failure.refresh_from_db()
    assert failure.retry_status == FailureCaseModel.RetryStatus.PASSED
    assert failure.last_retry_run.run_id == "fake-run-1"


def test_retry_all_failed_uses_all_failed_node_ids():
    """验证一键失败重试会收集原任务下所有 failed 用例 node id。"""
    user = create_user("retry-all-user")
    original = TestRunModel.objects.create(
        run_id="original-all",
        case_path="test_case/test_gbif_case",
        retry_mode=TestRunModel.RetryMode.NONE,
        status=TestRunModel.Status.FAILED,
        triggered_by=user,
    )
    failures = [
        FailureCaseModel.objects.create(
            test_run=original,
            node_id=f"test_case/test_gbif_case/test_gbif_api.py::test_case_{index}",
            case_name=f"test_case_{index}",
            module_path="test_case/test_gbif_case",
            status=FailureCaseModel.Status.FAILED,
        )
        for index in range(2)
    ]
    client = authenticated_client(user)

    response = client.post(
        f"/api/test-runs/{original.id}/retry-all-failed/",
        {"retry_count": 2},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["retry_mode"] == "all-failed"
    assert FakeApiTestRunner.calls[-1]["node_ids"] == [failure.node_id for failure in failures]
    assert FakeApiTestRunner.calls[-1]["retry_count"] == 2


def test_retry_module_uses_module_path_as_case_path():
    """验证模块重试会把 module_path 作为 case_path 交给执行器。"""
    user = create_user("retry-module-user")
    original = TestRunModel.objects.create(
        run_id="original-module",
        case_path="test_case/test_gbif_case",
        retry_mode=TestRunModel.RetryMode.NONE,
        status=TestRunModel.Status.FAILED,
        triggered_by=user,
    )
    client = authenticated_client(user)

    response = client.post(
        f"/api/test-runs/{original.id}/retry-module/",
        {"module_path": "test_case/test_gbif_case", "retry_count": 1},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["case_path"] == "test_case/test_gbif_case"
    assert response.data["retry_mode"] == "module"
    assert FakeApiTestRunner.calls[-1] == {
        "case_path": "test_case/test_gbif_case",
        "node_ids": [],
        "retry_mode": "module",
        "retry_count": 1,
    }


def test_report_endpoint_returns_report_url_without_leaking_server_path(tmp_path, settings):
    """验证报告 API 返回受控 URL 且不暴露服务器绝对路径。"""
    settings.ALLURE_REPORTS_ROOT = str(tmp_path)
    user = create_user("report-user")
    report_dir = tmp_path / "allure-report"
    report_dir.mkdir()
    (report_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    test_run = TestRunModel.objects.create(
        run_id="report-run",
        case_path="test_case/test_gbif_case",
        status=TestRunModel.Status.PASSED,
        report_path=str(report_dir),
        triggered_by=user,
    )
    client = authenticated_client(user)

    response = client.get(f"/api/test-runs/{test_run.id}/report/")

    assert response.status_code == 200
    assert response.data == {
        "report_url": "/reports/report-run/",
        "run_id": "report-run",
    }


def test_report_endpoint_requires_existing_allure_index(tmp_path, settings):
    """验证报告目录缺少 index.html 时报告 API 返回 404。"""
    settings.ALLURE_REPORTS_ROOT = str(tmp_path)
    user = create_user("missing-report-user")
    report_dir = tmp_path / "missing-report"
    report_dir.mkdir()
    test_run = TestRunModel.objects.create(
        run_id="missing-report-run",
        case_path="test_case/test_gbif_case",
        status=TestRunModel.Status.PASSED,
        report_path=str(report_dir),
        triggered_by=user,
    )
    client = authenticated_client(user)

    response = client.get(f"/api/test-runs/{test_run.id}/report/")

    assert response.status_code == 404
    assert response.data == {"detail": "Report is not available."}


def test_report_static_entry_serves_allure_index(tmp_path, settings):
    """验证 `/reports/<run_id>/` 可以服务 Allure 首页。"""
    settings.ALLURE_REPORTS_ROOT = str(tmp_path)
    user = create_user("static-report-user")
    report_dir = tmp_path / "allure-report"
    report_dir.mkdir()
    (report_dir / "index.html").write_text("<html><body>Allure Report</body></html>", encoding="utf-8")
    TestRunModel.objects.create(
        run_id="static-report-run",
        case_path="test_case/test_gbif_case",
        status=TestRunModel.Status.PASSED,
        report_path=str(report_dir),
        triggered_by=user,
    )
    client = authenticated_client(user)

    response = client.get("/reports/static-report-run/")

    assert response.status_code == 200
    assert b"Allure Report" in b"".join(response.streaming_content)


def test_report_static_entry_rejects_paths_outside_report_root(tmp_path, settings):
    """验证报告服务拒绝 ALLURE_REPORTS_ROOT 外部路径。"""
    settings.ALLURE_REPORTS_ROOT = str(tmp_path / "allowed")
    user = create_user("unsafe-report-user")
    report_dir = tmp_path / "outside" / "allure-report"
    report_dir.mkdir(parents=True)
    (report_dir / "index.html").write_text("<html><body>Unsafe</body></html>", encoding="utf-8")
    test_run = TestRunModel.objects.create(
        run_id="unsafe-report-run",
        case_path="test_case/test_gbif_case",
        status=TestRunModel.Status.PASSED,
        report_path=str(report_dir),
        triggered_by=user,
    )
    client = authenticated_client(user)

    api_response = client.get(f"/api/test-runs/{test_run.id}/report/")
    static_response = client.get("/reports/unsafe-report-run/")

    assert api_response.status_code == 404
    assert static_response.status_code == 404
