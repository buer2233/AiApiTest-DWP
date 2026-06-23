import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.test_runs.models import FailureCase as FailureCaseModel
from apps.test_runs.models import TestRun as TestRunModel


pytestmark = pytest.mark.django_db


class FakeApiTestRunner:
    calls = []

    @classmethod
    def reset(cls):
        cls.calls = []

    @classmethod
    def run(cls, *, case_path, node_ids=None, retry_mode="none", retry_count=0):
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
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        password="local-test-pass",
        role=role,
    )


def authenticated_client(user=None):
    client = APIClient()
    client.force_authenticate(user=user or create_user())
    return client


@pytest.fixture(autouse=True)
def fake_runner(monkeypatch):
    FakeApiTestRunner.reset()
    monkeypatch.setattr(
        "apps.test_runs.views.ApiTestRunner",
        FakeApiTestRunner,
    )


def test_create_test_run_records_summary_and_failure_cases():
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


def test_report_endpoint_returns_report_url_without_leaking_server_path():
    user = create_user("report-user")
    test_run = TestRunModel.objects.create(
        run_id="report-run",
        case_path="test_case/test_gbif_case",
        status=TestRunModel.Status.PASSED,
        report_path="api-test/runtime/ci-runs/report-run/allure-report",
        triggered_by=user,
    )
    client = authenticated_client(user)

    response = client.get(f"/api/test-runs/{test_run.id}/report/")

    assert response.status_code == 200
    assert response.data == {
        "report_url": "/reports/report-run/",
        "run_id": "report-run",
    }
