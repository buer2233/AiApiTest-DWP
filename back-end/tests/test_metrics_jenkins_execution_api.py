from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.apps import apps
from django.utils import timezone

from metrics.jenkins_service import JenkinsServiceError
from metrics.views import discover_jenkins_builds
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


def create_task(
    context: dict,
    *,
    status: str = "running",
    task_type: str = "failed_rerun",
    queue_id: str = "1288",
    build_number: int = 12,
    job_full_name: str = "AiApiTest-DWP-Failed-Rerun",
):
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
        job_full_name=job_full_name,
        queue_id=queue_id,
        build_number=build_number,
        jenkins_queue_url=f"http://localhost:8080/queue/item/{queue_id}/",
        jenkins_build_url=f"http://localhost:8080/job/{job_full_name}/{build_number}/",
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
    assert response.data["error"]["message"] == "本模块已经有真正执行的重试!"


@pytest.mark.parametrize(
    ("existing_status", "existing_task_type"),
    [
        ("queued", "failed_rerun"),
        ("running", "failed_rerun"),
        ("canceling", "failed_rerun"),
        ("queued", "module_rerun"),
        ("running", "module_rerun"),
        ("canceling", "module_rerun"),
    ],
)
def test_active_jenkins_task_without_lock_blocks_new_retry_tasks(
    admin_client,
    p5_context,
    existing_status,
    existing_task_type,
):
    snapshot = p5_context["module_snapshot"]
    create_task(p5_context, status=existing_status, task_type=existing_task_type)
    create_job_binding(p5_context, "failed_rerun")
    create_job_binding(p5_context, "module_rerun", "AiApiTest-DWP-Module-Rerun")

    with patch("metrics.views.trigger_jenkins_build") as trigger_build:
        failed_response = admin_client.post(
            f"/api/v1/module-snapshots/{snapshot.id}/failed-case-retries",
            {"retry_scope": "all_failed"},
            format="json",
        )
        module_response = admin_client.post(f"/api/v1/module-snapshots/{snapshot.id}/module-reruns", {}, format="json")

    assert failed_response.status_code == 409
    assert failed_response.data["error"]["code"] == "module_execution_locked"
    assert failed_response.data["error"]["message"] == "本模块已经有真正执行的重试!"
    assert module_response.status_code == 409
    assert module_response.data["error"]["code"] == "module_execution_locked"
    assert module_response.data["error"]["message"] == "本模块已经有真正执行的重试!"
    assert metric_model("JenkinsTask").objects.count() == 1
    trigger_build.assert_not_called()


def test_stale_jenkins_queue_task_is_released_before_failed_retry(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    stale_task = create_task(p5_context, status="queued", queue_id="stale-queue", build_number=None)
    stale_lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=stale_task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )
    create_job_binding(p5_context, "failed_rerun")

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result, patch("metrics.views.trigger_jenkins_build") as trigger_build:
        fetch_result.side_effect = JenkinsServiceError("HTTP Error 404: Not Found")
        trigger_build.return_value = {"queue_id": "2002", "queue_url": "http://localhost:8080/queue/item/2002/"}
        response = admin_client.post(
            f"/api/v1/module-snapshots/{snapshot.id}/failed-case-retries",
            {"retry_scope": "all_failed"},
            format="json",
        )

    assert response.status_code == 202
    stale_task.refresh_from_db()
    stale_lock.refresh_from_db()
    assert stale_task.status == "failed"
    assert "not found" in stale_task.error_summary.lower()
    assert stale_lock.status == "released"
    assert metric_model("JenkinsTask").objects.filter(status="queued").count() == 1
    trigger_build.assert_called_once()


def test_expired_local_rerun_task_is_released_when_jenkins_cannot_be_checked(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    expired_at = timezone.now() - timedelta(hours=3)
    expired_task = create_task(p5_context, status="queued", queue_id="expired-queue", build_number=None)
    metric_model("JenkinsTask").objects.filter(id=expired_task.id).update(created_at=expired_at, updated_at=expired_at)
    expired_lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=expired_task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=expired_at,
    )
    create_job_binding(p5_context, "failed_rerun")

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result, patch("metrics.views.trigger_jenkins_build") as trigger_build:
        fetch_result.side_effect = JenkinsServiceError("HTTP Error 403: Forbidden")
        trigger_build.return_value = {"queue_id": "2003", "queue_url": "http://localhost:8080/queue/item/2003/"}
        response = admin_client.post(
            f"/api/v1/module-snapshots/{snapshot.id}/failed-case-retries",
            {"retry_scope": "all_failed"},
            format="json",
        )

    assert response.status_code == 202
    expired_task.refresh_from_db()
    expired_lock.refresh_from_db()
    assert expired_task.status == "failed"
    assert "expired" in expired_task.error_summary.lower()
    assert expired_lock.status == "expired"
    trigger_build.assert_called_once()


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


def test_module_jenkins_tasks_list_returns_actions(admin_client, p5_context, monkeypatch):
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "http://localhost:8080")
    snapshot = p5_context["module_snapshot"]
    task = create_task(p5_context, status="running")

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks", {"date": "today"})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    row = response.data["data"][0]
    assert row["id"] == task.id
    assert row["status"] == "running"
    assert row["actions"] == {"cancel": True, "view_report": True, "view_jenkins_task": True}


def test_module_jenkins_tasks_list_derives_jenkins_and_allure_links(admin_client, p5_context, monkeypatch):
    snapshot = p5_context["module_snapshot"]
    task = create_task(
        p5_context,
        status="running",
        build_number=9,
        job_full_name="AiApiTest-DWP-Failed-Rerun",
    )
    task.jenkins_build_url = ""
    task.allure_report_url = ""
    task.save(update_fields=["jenkins_build_url", "allure_report_url", "updated_at"])
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "http://localhost:8080")

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks", {"date": "today"})

    assert response.status_code == 200
    row = response.data["data"][0]
    assert row["jenkins_build_url"] == "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/9/"
    assert row["allure_report_url"] == "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/allure/"
    assert row["actions"]["view_report"] is True
    assert row["actions"]["view_jenkins_task"] is True


def test_module_jenkins_tasks_list_does_not_derive_report_link_before_build(admin_client, p5_context, monkeypatch):
    snapshot = p5_context["module_snapshot"]
    task = create_task(
        p5_context,
        status="queued",
        build_number=None,
        job_full_name="AiApiTest-DWP-Failed-Rerun",
    )
    task.jenkins_build_url = ""
    task.allure_report_url = ""
    task.save(update_fields=["jenkins_build_url", "allure_report_url", "updated_at"])
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "http://localhost:8080")

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks", {"date": "today"})

    assert response.status_code == 200
    row = response.data["data"][0]
    assert row["jenkins_build_url"] == ""
    assert row["allure_report_url"] == ""
    assert row["actions"]["view_report"] is False
    assert row["actions"]["view_jenkins_task"] is False


def test_module_jenkins_tasks_list_filters_by_task_type(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    create_task(
        p5_context,
        status="running",
        task_type="failed_rerun",
        queue_id="failed-queue",
        build_number=12,
        job_full_name="AiApiTest-DWP-Failed-Rerun",
    )
    module_task = create_task(
        p5_context,
        status="running",
        task_type="module_rerun",
        queue_id="module-queue",
        build_number=13,
        job_full_name="AiApiTest-DWP-Module-Rerun",
    )

    response = admin_client.get(
        f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks",
        {"date": "today", "task_type": "module_rerun"},
    )

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    assert response.data["data"][0]["id"] == module_task.id
    assert response.data["data"][0]["task_type"] == "module_rerun"
    assert response.data["data"][0]["job_name"] == "AiApiTest-DWP-Module-Rerun"


def test_module_jenkins_tasks_list_rejects_invalid_task_type(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]

    response = admin_client.get(
        f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks",
        {"date": "today", "task_type": "unknown"},
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_bulk_sync_discovers_daily_builds_with_active_daily_job_names(admin_client, p5_context):
    create_job_binding(p5_context, "daily_full", "AiApiTest-DWP-Daily-Full-Module-test_gbif_case")

    with patch("metrics.views.discover_jenkins_builds") as discover_builds:
        discover_builds.return_value = []
        response = admin_client.post("/api/v1/jenkins-tasks/sync", {"discover_daily": True}, format="json")

    assert response.status_code == 200
    discover_builds.assert_called_once_with(
        job_full_names=["AiApiTest-DWP-Daily-Full-Module-test_gbif_case"],
        date=None,
    )


def test_daily_discovery_wrapper_accepts_explicit_job_names():
    with patch("metrics.views.discover_jenkins_builds_from_jenkins") as discover_from_jenkins:
        discover_from_jenkins.return_value = [{"build_number": 12}]
        result = discover_jenkins_builds(job_full_names=["daily/job-a"], date="2026-07-09")

    assert result == [{"build_number": 12}]
    discover_from_jenkins.assert_called_once_with(job_full_names=["daily/job-a"], date="2026-07-09")


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


def test_cancel_task_jenkins_not_found_returns_conflict(admin_client, p5_context):
    task = create_task(p5_context, status="queued")

    with patch("metrics.views.cancel_jenkins_task") as cancel_task:
        cancel_task.side_effect = JenkinsServiceError("HTTP Error 404: Not Found")
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/cancel", {}, format="json")

    assert response.status_code == 409
    assert response.data["error"]["code"] == "task_not_cancelable"
    assert response.data["error"]["message"] == "任务已不在 Jenkins 队列中，请同步状态后重试。"
    task.refresh_from_db()
    assert task.status == "queued"


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


def test_module_snapshot_retry_actions_remain_clickable_when_execution_locked(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    task = create_task(p5_context, status="running")
    create_job_binding(p5_context, "failed_rerun")
    create_job_binding(p5_context, "module_rerun", "AiApiTest-DWP-Module-Rerun")
    metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        locked_at=timezone.now(),
    )

    response = admin_client.get("/api/v1/module-snapshots", {"environment_id": p5_context["environment"].id})

    assert response.status_code == 200
    row = next(item for item in response.data["data"] if item["id"] == snapshot.id)
    assert row["actions"]["failed_rerun"] is True
    assert row["actions"]["module_rerun"] is True


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


def test_bulk_sync_returns_readable_error_when_daily_discovery_unavailable(admin_client, p5_context):
    create_job_binding(p5_context, "daily_full", "AiApiTest-DWP-Daily-Full-Module-Species")

    with patch("metrics.views.discover_jenkins_builds") as discover_builds:
        discover_builds.side_effect = JenkinsServiceError("JENKINS_API_BASE_URL is not configured")
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 503
    assert response.data["error"]["code"] == "jenkins_unavailable"
    assert "JENKINS_API_BASE_URL is not configured" in response.data["error"]["message"]
    assert metric_model("JenkinsTask").objects.count() == 0


def test_bulk_sync_fetch_error_keeps_existing_daily_task_status(admin_client, p5_context):
    create_job_binding(p5_context, "daily_full", "AiApiTest-DWP-Daily-Full-Module-Species")
    existing_task = create_task(
        p5_context,
        status="running",
        task_type="daily_full",
        queue_id="daily-queue",
        build_number=88,
        job_full_name="AiApiTest-DWP-Daily-Full-Module-Species",
    )

    with patch("metrics.views.discover_jenkins_builds") as discover_builds, patch(
        "metrics.views.fetch_jenkins_task_result"
    ) as fetch_result:
        discover_builds.return_value = [
            {
                "job_full_name": "AiApiTest-DWP-Daily-Full-Module-Species",
                "build_number": 88,
                "jenkins_build_url": "http://localhost:8080/job/AiApiTest-DWP-Daily-Full-Module-Species/88/",
                "building": False,
            }
        ]
        fetch_result.side_effect = JenkinsServiceError("Jenkins artifact unavailable")
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 503
    assert response.data["error"]["code"] == "jenkins_unavailable"
    assert "Jenkins artifact unavailable" in response.data["error"]["message"]
    existing_task.refresh_from_db()
    assert existing_task.status == "running"


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
