from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.apps import apps
from django.utils import timezone

from tests.p3_metrics_helpers import create_case_result, create_p3_metric_context


pytestmark = pytest.mark.api


def metric_model(model_name: str):
    return apps.get_model("metrics", model_name)


@pytest.fixture
def p5_context(db) -> dict:
    context = create_p3_metric_context(suffix="-p5")
    context["failed_case"] = create_case_result(context, display_status="failed", node_suffix="retry_failed")
    context["second_failed_case"] = create_case_result(context, display_status="failed", node_suffix="retry_second")
    context["passed_case"] = create_case_result(context, display_status="passed", node_suffix="retry_passed")
    return context


def create_job_binding(context: dict, task_type: str, job_full_name: str = "AiApiTest-DWP-Failed-Rerun"):
    JenkinsJobBinding = metric_model("JenkinsJobBinding")
    return JenkinsJobBinding.objects.create(
        environment=context["environment"],
        module=context["module"],
        task_type=task_type,
        job_full_name=job_full_name,
        default_retry_count=0,
        is_active=True,
    )


def create_task(context: dict, *, status: str = "running", task_type: str = "failed_rerun"):
    JenkinsTask = metric_model("JenkinsTask")
    TestRun = metric_model("TestRun")
    run = TestRun.objects.create(
        run_key=f"p5-{task_type}-{timezone.now().timestamp()}",
        run_type=task_type,
        environment=context["environment"],
        module=context["module"],
        status=status,
    )
    return JenkinsTask.objects.create(
        run=run,
        environment=context["environment"],
        module=context["module"],
        task_type=task_type,
        trigger_source="platform_user",
        job_full_name="AiApiTest-DWP-Failed-Rerun",
        queue_id="1288",
        build_number=12,
        jenkins_queue_url="http://localhost:8080/queue/item/1288/",
        jenkins_build_url="http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/12/",
        status=status,
    )


def test_admin_triggers_all_failed_retry_creates_queued_task_and_lock(admin_client, admin_user, p5_context):
    snapshot = p5_context["module_snapshot"]
    create_job_binding(p5_context, "failed_rerun")

    with patch("metrics.views.trigger_jenkins_build") as trigger_build:
        trigger_build.return_value = {
            "queue_id": "1288",
            "queue_url": "http://localhost:8080/queue/item/1288/",
        }
        response = admin_client.post(
            f"/api/v1/module-snapshots/{snapshot.id}/failed-case-retries",
            {"retry_scope": "all_failed"},
            format="json",
        )

    assert response.status_code == 202
    task = metric_model("JenkinsTask").objects.get()
    lock = metric_model("ModuleExecutionLock").objects.get()
    assert response.data["data"]["id"] == task.id
    assert task.status == "queued"
    assert task.task_type == "failed_rerun"
    assert task.triggered_by == admin_user
    assert sorted(task.requested_nodeids_json) == sorted(
        [p5_context["failed_case"].node_id, p5_context["second_failed_case"].node_id]
    )
    assert lock.status == "active"
    assert lock.active_lock_key == f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}"
    trigger_build.assert_called_once()
    _, kwargs = trigger_build.call_args
    assert kwargs["job_full_name"] == "AiApiTest-DWP-Failed-Rerun"
    assert kwargs["parameters"]["RETRY_MODE"] == "selected"
    assert kwargs["parameters"]["RUN_ID"] == task.run.run_key
    assert p5_context["failed_case"].node_id in kwargs["parameters"]["PYTEST_NODE_IDS"]


def test_member_cannot_trigger_failed_retry(member_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    create_job_binding(p5_context, "failed_rerun")

    response = member_client.post(
        f"/api/v1/module-snapshots/{snapshot.id}/failed-case-retries",
        {"retry_scope": "all_failed"},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "admin_required"
    assert metric_model("JenkinsTask").objects.count() == 0


def test_failed_retry_rejects_invalid_selected_cases(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    create_job_binding(p5_context, "failed_rerun")

    response = admin_client.post(
        f"/api/v1/module-snapshots/{snapshot.id}/failed-case-retries",
        {"retry_scope": "selected_failed", "case_result_ids": [p5_context["passed_case"].id]},
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "invalid_case_selection"


def test_active_lock_blocks_module_rerun(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    task = create_task(p5_context, status="running")
    ModuleExecutionLock = metric_model("ModuleExecutionLock")
    ModuleExecutionLock.objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )
    create_job_binding(p5_context, "module_rerun", "AiApiTest-DWP-Module-Rerun")

    response = admin_client.post(f"/api/v1/module-snapshots/{snapshot.id}/module-reruns", {}, format="json")

    assert response.status_code == 409
    assert response.data["error"]["code"] == "module_execution_locked"
    assert response.data["error"]["message"] == "已有用例重试，无法执行！"


def test_admin_triggers_module_rerun_with_case_path(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    create_job_binding(p5_context, "module_rerun", "AiApiTest-DWP-Module-Rerun")

    with patch("metrics.views.trigger_jenkins_build") as trigger_build:
        trigger_build.return_value = {"queue_id": "2001", "queue_url": "http://localhost:8080/queue/item/2001/"}
        response = admin_client.post(f"/api/v1/module-snapshots/{snapshot.id}/module-reruns", {}, format="json")

    assert response.status_code == 202
    task = metric_model("JenkinsTask").objects.get()
    assert task.task_type == "module_rerun"
    _, kwargs = trigger_build.call_args
    assert kwargs["job_full_name"] == "AiApiTest-DWP-Module-Rerun"
    assert kwargs["parameters"]["RETRY_MODE"] == "module"
    assert kwargs["parameters"]["CASE_PATH"] == p5_context["module"].case_path
    assert kwargs["parameters"]["RUN_ID"] == task.run.run_key


def test_cancel_running_task_enters_canceling_and_keeps_lock(admin_client, p5_context):
    task = create_task(p5_context, status="running")
    lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )

    with patch("metrics.views.cancel_jenkins_task") as cancel_task:
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/cancel", {}, format="json")

    assert response.status_code == 202
    task.refresh_from_db()
    lock.refresh_from_db()
    assert task.status == "canceling"
    assert lock.status == "active"
    assert lock.active_lock_key is not None
    cancel_task.assert_called_once_with(task)


def test_module_jenkins_tasks_list_returns_actions(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    task = create_task(p5_context, status="running")

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks", {"date": "today"})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    row = response.data["data"][0]
    assert row["id"] == task.id
    assert row["status"] == "running"
    assert row["actions"] == {"cancel": True, "view_report": False, "view_jenkins_task": True}


def test_sync_queued_task_without_build_keeps_queued_and_lock(admin_client, p5_context):
    task = create_task(p5_context, status="queued")
    lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {"queue_pending": True}
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    lock.refresh_from_db()
    assert task.status == "queued"
    assert task.finished_at is None
    assert task.last_synced_at is not None
    assert lock.status == "active"


def test_sync_building_task_keeps_running_and_lock(admin_client, p5_context):
    task = create_task(p5_context, status="queued")
    lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "build_number": 31,
            "jenkins_build_url": "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/31/",
            "building": True,
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    lock.refresh_from_db()
    assert task.status == "running"
    assert task.build_number == 31
    assert task.finished_at is None
    assert lock.status == "active"


def test_repeated_canceling_task_cancel_is_idempotent(admin_client, p5_context):
    task = create_task(p5_context, status="canceling")

    with patch("metrics.views.cancel_jenkins_task") as cancel_task:
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/cancel", {}, format="json")

    assert response.status_code == 202
    assert response.data["data"]["status"] == "canceling"
    cancel_task.assert_not_called()


def test_sync_allure_not_generated_marks_task_failed(admin_client, p5_context):
    task = create_task(p5_context, status="running")
    metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "passed",
                "failed_nodeids": [],
                "allure_report_status": "skipped",
                "allure_report_message": "Allure CLI missing",
            },
            "failed_nodeids": [],
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    assert task.status == "failed"
    assert "Allure CLI missing" in task.error_summary
    assert metric_model("ModuleExecutionLock").objects.get(task=task).status == "released"


def test_sync_canceling_queue_task_releases_lock_after_jenkins_canceled(admin_client, p5_context):
    task = create_task(p5_context, status="canceling")
    metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {"canceled": True}
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    assert task.status == "canceled"
    assert metric_model("ModuleExecutionLock").objects.get(task=task).status == "released"


def test_sync_module_rerun_archives_old_failed_cases_and_writes_history(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    old_failed = p5_context["failed_case"]
    task = create_task(p5_context, status="running", task_type="module_rerun")

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "failed",
                "total_count": 100,
                "failed_count": 1,
                "passed_count": 97,
                "skipped_count": 2,
                "duration_seconds": 42.5,
                "failed_nodeids": ["test_case/test_gbif_case/test_species.py::test_new_failure"],
                "allure_report_status": "generated",
            },
            "failed_nodeids": ["test_case/test_gbif_case/test_species.py::test_new_failure"],
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    snapshot.refresh_from_db()
    old_failed.refresh_from_db()
    assert snapshot.failed_count == 1
    assert snapshot.duration_seconds == Decimal("42.5")
    assert old_failed.is_current is False
    new_failed = metric_model("TestCaseResult").objects.get(node_id="test_case/test_gbif_case/test_species.py::test_new_failure")
    assert new_failed.is_current is True
    assert new_failed.source_run_id == task.run_id
    assert metric_model("ModuleRunHistory").objects.filter(source_run=task.run, run_type="module_rerun").exists()


def test_module_snapshot_actions_include_disabled_reasons(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]

    response = admin_client.get("/api/v1/module-snapshots", {"environment_id": p5_context["environment"].id})

    assert response.status_code == 200
    row = next(item for item in response.data["data"] if item["id"] == snapshot.id)
    assert row["actions"]["failed_rerun"] is False
    assert row["actions"]["module_rerun"] is False
    assert row["disabled_reasons"]["failed_rerun"] == "Jenkins Job 未配置"
    assert row["disabled_reasons"]["module_rerun"] == "Jenkins Job 未配置"


def test_bulk_sync_discovers_daily_build_and_updates_snapshot(admin_client, p5_context):
    create_job_binding(p5_context, "daily_full", "AiApiTest-DWP-Daily-Full-Module-Species")

    with patch("metrics.views.discover_jenkins_builds") as discover_builds:
        discover_builds.return_value = [
            {
                "job_full_name": "AiApiTest-DWP-Daily-Full-Module-Species",
                "build_number": 88,
                "jenkins_build_url": "http://localhost:8080/job/AiApiTest-DWP-Daily-Full-Module-Species/88/",
                "jenkins_result": "SUCCESS",
                "summary": {
                    "status": "passed",
                    "total_count": 100,
                    "failed_count": 0,
                    "passed_count": 98,
                    "skipped_count": 2,
                    "duration_seconds": 60,
                    "failed_nodeids": [],
                    "allure_report_status": "generated",
                },
                "failed_nodeids": [],
                "finished_at": timezone.now(),
            }
        ]
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["data"]["created_count"] == 1
    task = metric_model("JenkinsTask").objects.get(task_type="daily_full", build_number=88)
    assert task.status == "success"
    p5_context["module_snapshot"].refresh_from_db()
    assert p5_context["module_snapshot"].failed_count == 0


def test_bulk_sync_fetches_daily_artifacts_with_discovered_run_id(admin_client, p5_context):
    create_job_binding(p5_context, "daily_full", "AiApiTest-DWP-Daily-Full-Module-Species")

    with patch("metrics.views.discover_jenkins_builds") as discover_builds, patch(
        "metrics.views.fetch_jenkins_task_result"
    ) as fetch_result:
        discover_builds.return_value = [
            {
                "job_full_name": "AiApiTest-DWP-Daily-Full-Module-Species",
                "build_number": 88,
                "jenkins_build_url": "http://localhost:8080/job/AiApiTest-DWP-Daily-Full-Module-Species/88/",
                "jenkins_result": "SUCCESS",
                "building": False,
                "run_id": "jenkins-AiApiTest-DWP-Daily-Full-Module-Species-88",
            }
        ]
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "passed",
                "total_count": 100,
                "failed_count": 0,
                "passed_count": 98,
                "skipped_count": 2,
                "duration_seconds": 60,
                "failed_nodeids": [],
                "allure_report_status": "generated",
            },
            "failed_nodeids": [],
            "finished_at": timezone.now(),
        }
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 200
    task = metric_model("JenkinsTask").objects.get(task_type="daily_full", build_number=88)
    assert task.run.run_key == "jenkins-AiApiTest-DWP-Daily-Full-Module-Species-88"
    fetch_result.assert_called_once()
    assert fetch_result.call_args.args[0].run.run_key == "jenkins-AiApiTest-DWP-Daily-Full-Module-Species-88"


def test_sync_failed_retry_test_failed_updates_cases_without_touching_module_execution_time(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    original_completed_at = snapshot.completed_at
    original_duration = snapshot.duration_seconds
    task = create_task(p5_context, status="running")
    task.requested_nodeids_json = [p5_context["failed_case"].node_id]
    task.save(update_fields=["requested_nodeids_json", "updated_at"])
    metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "failed",
                "return_code": 1,
                "failed_nodeids": [p5_context["second_failed_case"].node_id],
                "allure_report_status": "generated",
            },
            "failed_nodeids": [p5_context["second_failed_case"].node_id],
            "allure_report_url": "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/12/artifact/api-test/runtime/ci-runs/run/allure-report/index.html",
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    snapshot.refresh_from_db()
    p5_context["failed_case"].refresh_from_db()
    p5_context["second_failed_case"].refresh_from_db()
    assert task.status == "test_failed"
    assert p5_context["failed_case"].display_status == "passed"
    assert p5_context["second_failed_case"].display_status == "failed"
    assert snapshot.failed_count == 3
    assert snapshot.pass_rate == Decimal("0.970000")
    assert snapshot.completed_at == original_completed_at
    assert snapshot.duration_seconds == original_duration
    assert metric_model("ModuleExecutionLock").objects.get(task=task).status == "released"
