from __future__ import annotations

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.apps import apps
from django.test import override_settings
from django.utils import timezone

from metrics.jenkins_service import JenkinsBuildMatchError, JenkinsServiceError
from metrics.views import discover_jenkins_builds
from tests.p3_metrics_helpers import create_case_result, create_p3_metric_context


pytestmark = pytest.mark.api


def metric_model(model_name: str):
    return apps.get_model("metrics", model_name)


MODULE_SUMMARY_FIELDS = (
    "total_count",
    "failed_count",
    "passed_count",
    "skipped_count",
    "pass_rate",
    "completed_at",
    "duration_seconds",
    "latest_run_id",
)
ENVIRONMENT_SUMMARY_FIELDS = (
    "total_count",
    "failed_count",
    "passed_count",
    "skipped_count",
    "pass_rate",
    "finished_at",
    "duration_seconds",
    "latest_run_id",
)


def model_field_state(instance, fields: tuple[str, ...]) -> tuple:
    instance.refresh_from_db()
    return tuple(getattr(instance, field) for field in fields)


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


DAILY_PARENT_JOB_NAME = "AiApiTest-DWP-Daily-Full-Module"


def create_daily_parent_binding(job_full_name: str = DAILY_PARENT_JOB_NAME):
    return metric_model("JenkinsJobBinding").objects.create(
        environment=None,
        module=None,
        task_type="daily_full",
        job_full_name=job_full_name,
        default_retry_count=0,
        is_active=True,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("uses_environment", "uses_module"),
    [(True, False), (False, True)],
    ids=["legacy_environment_binding", "legacy_module_binding"],
)
def test_daily_discovery_rejects_legacy_binding_even_with_a_valid_target_base_url(
    uses_environment,
    uses_module,
):
    from metrics.views import DailyParentEnvironmentError, create_or_get_daily_task_from_discovery

    environment = metric_model("TestEnvironment").objects.create(
        env_key="daily-legacy-binding",
        env_name="Daily 遗留绑定环境",
        base_url="https://daily-legacy.example.invalid/api",
        is_active=True,
    )
    module = metric_model("TestModule").objects.create(
        package_name="daily_legacy_binding_module",
        case_path="test_case/daily_legacy_binding_module",
        module_name="Daily 遗留绑定模块",
        module_dev="开发",
        module_test="测试",
        is_active=True,
    )
    binding = metric_model("JenkinsJobBinding").objects.create(
        environment=environment if uses_environment else None,
        module=module if uses_module else None,
        task_type="daily_full",
        job_full_name=DAILY_PARENT_JOB_NAME,
        default_retry_count=0,
        is_active=True,
    )

    with pytest.raises(DailyParentEnvironmentError):
        create_or_get_daily_task_from_discovery(
            binding,
            {
                "job_full_name": binding.job_full_name,
                "build_number": 501,
                "run_id": "legacy-daily-501",
                "target_base_url": environment.base_url,
            },
        )

    assert metric_model("JenkinsTask").objects.count() == 0
    assert metric_model("TestRun").objects.count() == 0


@pytest.mark.parametrize(
    ("uses_environment", "uses_module"),
    [(True, False), (False, True)],
    ids=["legacy_environment_binding", "legacy_module_binding"],
)
def test_daily_discovery_rejects_legacy_binding_before_returning_an_existing_parent_task(
    p5_context,
    uses_environment,
    uses_module,
):
    from metrics.views import DailyParentEnvironmentError, create_or_get_daily_task_from_discovery

    existing_task = create_daily_parent_task(p5_context, build_number=502)
    binding = metric_model("JenkinsJobBinding").objects.create(
        environment=p5_context["environment"] if uses_environment else None,
        module=p5_context["module"] if uses_module else None,
        task_type="daily_full",
        job_full_name=existing_task.job_full_name,
        default_retry_count=0,
        is_active=True,
    )
    task_count = metric_model("JenkinsTask").objects.count()
    run_count = metric_model("TestRun").objects.count()
    original_status = existing_task.status
    original_run_status = existing_task.run.status

    with pytest.raises(DailyParentEnvironmentError):
        create_or_get_daily_task_from_discovery(
            binding,
            {
                "job_full_name": existing_task.job_full_name,
                "build_number": existing_task.build_number,
                "run_id": "legacy-daily-existing-502",
                "target_base_url": p5_context["environment"].base_url,
            },
        )

    existing_task.refresh_from_db()
    existing_task.run.refresh_from_db()
    assert metric_model("JenkinsTask").objects.count() == task_count
    assert metric_model("TestRun").objects.count() == run_count
    assert existing_task.status == original_status
    assert existing_task.run.status == original_run_status


def create_daily_parent_task(
    context: dict,
    *,
    status: str = "running",
    queue_id: str = "daily-queue",
    build_number: int = 12,
    job_full_name: str = DAILY_PARENT_JOB_NAME,
):
    TestRun = metric_model("TestRun")
    run = TestRun.objects.create(
        run_key=f"p5-daily-parent-{timezone.now().timestamp()}",
        run_type="daily_full",
        environment=context["environment"],
        module=None,
        status=status,
    )
    return metric_model("JenkinsTask").objects.create(
        run=run,
        environment=context["environment"],
        module=None,
        task_type="daily_full",
        trigger_source="jenkins_cron",
        job_full_name=job_full_name,
        queue_id=queue_id,
        build_number=build_number,
        jenkins_queue_url=f"http://localhost:8080/queue/item/{queue_id}/",
        jenkins_build_url=f"http://localhost:8080/job/{job_full_name}/{build_number}/",
        status=status,
    )


def daily_parent_build_result(task, environment) -> dict:
    return {
        "job_full_name": task.job_full_name,
        "build_number": task.build_number,
        "run_id": f"daily-discovery-{task.id}",
        "target_base_url": f"  {environment.base_url}/  ",
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "malformed_shape",
    [
        "task_type",
        "task_module",
        "run_missing",
        "run_type",
        "run_module",
        "task_environment",
        "run_environment",
    ],
)
def test_daily_discovery_rejects_malformed_existing_global_parent_task(p5_context, malformed_shape):
    from metrics.views import DailyParentEnvironmentError, create_or_get_daily_task_from_discovery

    JenkinsTask = metric_model("JenkinsTask")
    TestEnvironment = metric_model("TestEnvironment")
    TestRun = metric_model("TestRun")
    binding = create_daily_parent_binding()
    existing_task = create_daily_parent_task(p5_context, build_number=503)
    other_environment = TestEnvironment.objects.create(
        env_key=f"daily-invalid-{malformed_shape}",
        env_name="Daily 异常父任务环境",
        base_url=f"https://daily-invalid-{malformed_shape}.example.invalid/api",
        is_active=True,
    )

    if malformed_shape == "task_type":
        JenkinsTask.objects.filter(pk=existing_task.pk).update(
            task_type="module_rerun",
            module=p5_context["module"],
        )
    elif malformed_shape == "task_module":
        JenkinsTask.objects.filter(pk=existing_task.pk).update(module=p5_context["module"])
    elif malformed_shape == "run_missing":
        JenkinsTask.objects.filter(pk=existing_task.pk).update(run=None)
    elif malformed_shape == "run_type":
        TestRun.objects.filter(pk=existing_task.run_id).update(
            run_type="module_rerun",
            module=p5_context["module"],
        )
    elif malformed_shape == "run_module":
        TestRun.objects.filter(pk=existing_task.run_id).update(module=p5_context["module"])
    elif malformed_shape == "task_environment":
        JenkinsTask.objects.filter(pk=existing_task.pk).update(environment=other_environment)
    else:
        TestRun.objects.filter(pk=existing_task.run_id).update(environment=other_environment)

    task_count = JenkinsTask.objects.count()
    run_count = TestRun.objects.count()
    with pytest.raises(DailyParentEnvironmentError):
        create_or_get_daily_task_from_discovery(
            binding,
            daily_parent_build_result(existing_task, p5_context["environment"]),
        )

    assert JenkinsTask.objects.count() == task_count
    assert TestRun.objects.count() == run_count


@pytest.mark.django_db
def test_daily_discovery_returns_valid_existing_global_parent_task_idempotently(p5_context):
    from metrics.views import create_or_get_daily_task_from_discovery

    binding = create_daily_parent_binding()
    existing_task = create_daily_parent_task(p5_context, build_number=504)

    task, created = create_or_get_daily_task_from_discovery(
        binding,
        daily_parent_build_result(existing_task, p5_context["environment"]),
    )

    assert task.id == existing_task.id
    assert created is False


@pytest.mark.django_db
def test_daily_discovery_integrity_error_fallback_rejects_malformed_existing_parent_task(p5_context):
    from metrics.views import DailyParentEnvironmentError, create_or_get_daily_task_from_discovery

    class EmptyInitialLookup:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    JenkinsTask = metric_model("JenkinsTask")
    binding = create_daily_parent_binding()
    existing_task = create_daily_parent_task(p5_context, build_number=505)
    JenkinsTask.objects.filter(pk=existing_task.pk).update(module=p5_context["module"])

    with patch("metrics.views.JenkinsTask.objects.select_related", return_value=EmptyInitialLookup()), pytest.raises(
        DailyParentEnvironmentError
    ):
        create_or_get_daily_task_from_discovery(
            binding,
            daily_parent_build_result(existing_task, p5_context["environment"]),
        )

    assert JenkinsTask.objects.count() == 1


@pytest.mark.django_db
def test_daily_discovery_integrity_error_fallback_returns_valid_parent_without_orphaned_run(p5_context):
    from metrics.views import create_or_get_daily_task_from_discovery

    class EmptyInitialLookup:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    JenkinsTask = metric_model("JenkinsTask")
    TestRun = metric_model("TestRun")
    binding = create_daily_parent_binding()
    existing_task = create_daily_parent_task(p5_context, build_number=506)
    task_count = JenkinsTask.objects.count()
    run_count = TestRun.objects.count()

    with patch("metrics.views.JenkinsTask.objects.select_related", return_value=EmptyInitialLookup()):
        task, created = create_or_get_daily_task_from_discovery(
            binding,
            daily_parent_build_result(existing_task, p5_context["environment"]),
        )

    assert task.id == existing_task.id
    assert created is False
    assert JenkinsTask.objects.count() == task_count
    assert TestRun.objects.count() == run_count


def daily_parent_summary(context: dict, *, primary_status: str = "passed", other_status: str = "passed") -> dict:
    def module_detail(module, execution_status: str) -> dict:
        failed_count = 1 if execution_status == "failed" else 0
        return {
            "module_key": module.package_name,
            "total_count": 1,
            "failed_count": failed_count,
            "passed_count": 1 - failed_count,
            "skipped_count": 0,
            "duration_seconds": 5.25,
            "case_results": [
                {
                    "node_id": f"{module.case_path}/test_daily.py::test_daily_{execution_status}",
                    "case_name": f"test_daily_{execution_status}",
                    "execution_status": execution_status,
                    "error_type": "AssertionError" if failed_count else "",
                    "error_message_summary": "Daily 父任务用例失败" if failed_count else "",
                }
            ],
        }

    details = [
        module_detail(context["module"], primary_status),
        module_detail(context["other_module"], other_status),
    ]
    failed_count = sum(detail["failed_count"] for detail in details)
    return {
        "status": "failed" if failed_count else "passed",
        "module_count": len(details),
        "total_count": len(details),
        "failed_count": failed_count,
        "passed_count": len(details) - failed_count,
        "skipped_count": 0,
        "failed_nodeids": [],
        "modules": details,
    }


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


def test_stale_local_rerun_task_stays_locked_when_jenkins_is_unavailable(admin_client, p5_context):
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

    assert response.status_code == 409
    expired_task.refresh_from_db()
    expired_lock.refresh_from_db()
    assert expired_task.status == "queued"
    assert expired_task.error_summary == ""
    assert expired_lock.status == "active"
    trigger_build.assert_not_called()


def test_stale_queue_task_recovers_real_build_before_expiring_lock(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    stale_at = timezone.now() - timedelta(hours=3)
    stale_task = create_task(
        p5_context,
        status="queued",
        task_type="failed_rerun",
        queue_id="expired-but-recoverable",
        build_number=None,
    )
    metric_model("JenkinsTask").objects.filter(id=stale_task.id).update(created_at=stale_at, updated_at=stale_at)
    stale_lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=stale_task,
        lock_type="module_execution",
        status="active",
        locked_at=stale_at,
    )
    create_job_binding(p5_context, "failed_rerun")

    with patch(
        "metrics.views.fetch_jenkins_task_result",
        return_value={
            "build_number": 29,
            "jenkins_build_url": "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/29/",
            "jenkins_result": "SUCCESS",
            "finished_at": timezone.now() - timedelta(hours=1),
            "summary": {
                "status": "passed",
                "failed_nodeids": [],
                "allure_report_status": "generated",
            },
            "failed_nodeids": [],
        },
    ) as fetch_result, patch("metrics.views.trigger_jenkins_build") as trigger_build:
        trigger_build.return_value = {"queue_id": "2004", "queue_url": "http://localhost:8080/queue/item/2004/"}
        response = admin_client.post(
            f"/api/v1/module-snapshots/{snapshot.id}/failed-case-retries",
            {"retry_scope": "all_failed"},
            format="json",
        )

    assert response.status_code == 202
    stale_task.refresh_from_db()
    stale_lock.refresh_from_db()
    assert stale_task.status == "success"
    assert stale_task.build_number == 29
    assert stale_lock.status == "released"
    fetch_result.assert_called_once()
    assert metric_model("JenkinsTask").objects.filter(status="queued").count() == 1


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


@override_settings(JENKINS_PUBLIC_BASE_URL="http://localhost:8080")
def test_module_jenkins_tasks_list_returns_actions(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    task = create_task(p5_context, status="running")

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks", {"date": "today"})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    row = response.data["data"][0]
    assert row["id"] == task.id
    assert row["status"] == "running"
    assert row["actions"] == {"cancel": True, "view_report": True, "view_jenkins_task": True}


@override_settings(JENKINS_PUBLIC_BASE_URL="http://localhost:8080")
def test_module_jenkins_tasks_list_derives_jenkins_and_allure_links(admin_client, p5_context):
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
    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks", {"date": "today"})

    assert response.status_code == 200
    row = response.data["data"][0]
    assert row["jenkins_build_url"] == "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/9/"
    assert row["allure_report_url"] == "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/9/allure/"
    assert row["actions"]["view_report"] is True
    assert row["actions"]["view_jenkins_task"] is True


def test_module_jenkins_tasks_list_normalizes_legacy_artifact_report_link(admin_client, p5_context):
    """历史任务保存的 artifact HTML 地址也必须按具体 build 规范化到 Allure 插件入口。"""
    snapshot = p5_context["module_snapshot"]
    task = create_task(
        p5_context,
        status="success",
        build_number=19,
        job_full_name="AiApiTest-DWP-Failed-Rerun",
    )
    task.allure_report_url = (
        "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/19/artifact/"
        "api-test/runtime/ci-runs/legacy/allure-report/index.html"
    )
    task.save(update_fields=["allure_report_url", "updated_at"])

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/jenkins-tasks", {"date": "today"})

    assert response.status_code == 200
    row = response.data["data"][0]
    assert row["allure_report_url"] == "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/19/allure/"


@override_settings(JENKINS_PUBLIC_BASE_URL="http://localhost:8080")
def test_module_jenkins_tasks_list_does_not_derive_report_link_before_build(admin_client, p5_context):
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
    create_daily_parent_binding()

    with patch("metrics.views.discover_jenkins_builds") as discover_builds:
        discover_builds.return_value = []
        response = admin_client.post("/api/v1/jenkins-tasks/sync", {"discover_daily": True}, format="json")

    assert response.status_code == 200
    discover_builds.assert_called_once_with(
        job_full_names=[DAILY_PARENT_JOB_NAME],
        date=None,
    )


def test_default_daily_discovery_ignores_active_legacy_module_bindings(p5_context):
    JenkinsJobBinding = metric_model("JenkinsJobBinding")
    JenkinsJobBinding.objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task_type="daily_full",
        job_full_name="AiApiTest-DWP-Daily-Full-Module-Legacy",
        is_active=True,
    )
    JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type="daily_full",
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )

    with patch("metrics.views.discover_jenkins_builds_from_jenkins", return_value=[]) as discover_from_jenkins:
        result = discover_jenkins_builds()

    assert result == []
    discover_from_jenkins.assert_called_once_with(
        job_full_names=["AiApiTest-DWP-Daily-Full-Module"],
        date=None,
    )


def test_bulk_sync_ignores_same_name_legacy_binding_before_environment_precheck(admin_client, p5_context, monkeypatch):
    JenkinsJobBinding = metric_model("JenkinsJobBinding")
    job_full_name = "AiApiTest-DWP-Daily-Full-Module"
    JenkinsJobBinding.objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task_type="daily_full",
        job_full_name=job_full_name,
        is_active=True,
    )
    JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type="daily_full",
        job_full_name=job_full_name,
        is_active=True,
    )
    # 不能依赖模型默认的 NULL 排序偶然优先全局 binding。
    monkeypatch.setattr(JenkinsJobBinding._meta, "ordering", ["id"])

    with patch(
        "metrics.views.discover_jenkins_builds",
        return_value=[
            {
                "job_full_name": job_full_name,
                "build_number": 93,
                "jenkins_build_url": "http://localhost:8080/job/daily/93/",
                "building": True,
            }
        ],
    ):
        response = admin_client.post("/api/v1/jenkins-tasks/sync", {"discover_daily": True}, format="json")

    assert response.status_code == 200
    assert response.data["data"] == {"created_count": 0, "updated_count": 0, "synced_count": 0}
    assert metric_model("JenkinsTask").objects.count() == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"discover_daily": False},
        {"discover_daily": "false"},
        {"discover_daily": True, "date": "not-a-date"},
    ],
)
def test_bulk_sync_validates_request_before_calling_jenkins(admin_client, payload):
    with patch("metrics.views.discover_jenkins_builds") as discover_builds:
        response = admin_client.post("/api/v1/jenkins-tasks/sync", payload, format="json")

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"
    discover_builds.assert_not_called()


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


def test_single_sync_returns_conflict_and_records_ambiguous_build_diagnostic(admin_client, p5_context):
    task = create_task(p5_context, status="queued", build_number=None, queue_id="173")
    lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        active_lock_key=f"env:{p5_context['environment'].id}:module:{p5_context['module'].id}",
        locked_at=timezone.now(),
    )

    with patch(
        "metrics.views.fetch_jenkins_task_result",
        side_effect=JenkinsBuildMatchError(match_kind="queue_id", match_value="173", match_count=2),
    ):
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 409
    assert response.data["error"]["code"] == "jenkins_build_ambiguous"
    task.refresh_from_db()
    task.run.refresh_from_db()
    lock.refresh_from_db()
    assert task.status == "queued"
    assert task.run.status == "queued"
    assert task.build_number is None
    assert task.finished_at is None
    assert "queue_id=173" in task.error_summary
    assert "matches=2" in task.error_summary
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
                "total_count": 4,
                "failed_count": 2,
                "passed_count": 1,
                "skipped_count": 1,
                "duration_seconds": 42.5,
                "failed_nodeids": ["test_case/test_gbif_case/test_species.py::test_new_failure"],
                "case_results": [
                    {
                        "node_id": "test_case/test_gbif_case/test_species.py::test_new_passed",
                        "case_name": "test_new_passed",
                        "execution_status": "passed",
                        "duration_seconds": 0.1,
                        "error_type": "",
                        "error_message_summary": "",
                    },
                    {
                        "node_id": "test_case/test_gbif_case/test_species.py::test_new_failure",
                        "case_name": "test_new_failure",
                        "execution_status": "failed",
                        "duration_seconds": 0.2,
                        "error_type": "AssertionError",
                        "error_message_summary": "expected 200 but got 500",
                    },
                    {
                        "node_id": "test_case/test_gbif_case/test_species.py::test_new_skipped",
                        "case_name": "test_new_skipped",
                        "execution_status": "skipped",
                        "duration_seconds": 0.0,
                        "error_type": "",
                        "error_message_summary": "environment not ready",
                    },
                    {
                        "node_id": "test_case/test_gbif_case/test_species.py::test_new_error",
                        "case_name": "test_new_error",
                        "execution_status": "error",
                        "duration_seconds": 0.05,
                        "error_type": "RuntimeError",
                        "error_message_summary": "setup failed",
                    },
                ],
                "allure_report_status": "generated",
            },
            "failed_nodeids": ["test_case/test_gbif_case/test_species.py::test_new_failure"],
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    snapshot.refresh_from_db()
    old_failed.refresh_from_db()
    assert snapshot.failed_count == 2
    assert snapshot.duration_seconds == Decimal("42.5")
    assert old_failed.is_current is False
    new_failed = metric_model("TestCaseResult").objects.get(node_id="test_case/test_gbif_case/test_species.py::test_new_failure")
    assert new_failed.is_current is True
    assert new_failed.source_run_id == task.run_id
    current_cases = metric_model("TestCaseResult").objects.filter(module_snapshot=snapshot, is_current=True)
    assert set(current_cases.values_list("execution_status", "display_status")) == {
        ("passed", "passed"),
        ("failed", "failed"),
        ("skipped", "skipped"),
        ("error", "failed"),
    }
    assert metric_model("ModuleRunHistory").objects.filter(source_run=task.run, run_type="module_rerun").exists()


def test_sync_recovered_module_rerun_finishes_in_one_request_with_jenkins_completion_time(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    task = create_task(
        p5_context,
        status="queued",
        task_type="module_rerun",
        queue_id="173",
        build_number=None,
        job_full_name="AiApiTest-DWP-Module-Rerun",
    )
    execution_lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        locked_at=timezone.now(),
    )
    finished_at = timezone.now() - timedelta(hours=2)

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "build_number": 29,
            "jenkins_build_url": "http://localhost:8080/job/AiApiTest-DWP-Module-Rerun/29/",
            "jenkins_result": "SUCCESS",
            "started_at": finished_at - timedelta(seconds=90),
            "finished_at": finished_at,
            "summary": {
                "status": "passed",
                "total_count": 1,
                "failed_count": 0,
                "passed_count": 1,
                "skipped_count": 0,
                "duration_seconds": 4.64,
                "failed_nodeids": [],
                "case_results": [
                    {
                        "node_id": "test_case/test_gbif_case/test_species.py::test_recovered_passed",
                        "case_name": "test_recovered_passed",
                        "execution_status": "passed",
                        "error_type": "",
                        "error_message_summary": "",
                    }
                ],
                "allure_report_status": "generated",
            },
            "failed_nodeids": [],
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    snapshot.refresh_from_db()
    execution_lock.refresh_from_db()
    history = metric_model("ModuleRunHistory").objects.get(source_run=task.run, run_type="module_rerun")
    assert task.status == "success"
    assert task.build_number == 29
    assert task.finished_at == finished_at
    assert snapshot.completed_at == finished_at
    assert history.completed_at == finished_at
    assert history.run_date == timezone.localtime(finished_at).date()
    assert execution_lock.status == "released"


def test_sync_terminal_result_without_jenkins_completion_time_logs_fallback(admin_client, p5_context, caplog):
    task = create_task(p5_context, status="running", task_type="module_rerun")

    with patch(
        "metrics.views.fetch_jenkins_task_result",
        return_value={
            "jenkins_result": "FAILURE",
            "summary": None,
            "failed_nodeids": [],
            "error_summary": "Jenkins summary artifact is missing.",
        },
    ):
        with caplog.at_level("WARNING", logger="metrics.views"):
            response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    assert task.finished_at is not None
    assert "Jenkins completion time unavailable" in caplog.text
    assert "summary artifact" not in caplog.text


def test_sync_older_daily_build_writes_history_without_regressing_current_snapshot(admin_client, p5_context):
    snapshot = p5_context["module_snapshot"]
    snapshot_before = model_field_state(snapshot, MODULE_SUMMARY_FIELDS)
    current_case_ids = set(
        metric_model("TestCaseResult")
        .objects.filter(module_snapshot=snapshot, is_current=True)
        .values_list("id", flat=True)
    )
    older_finished_at = snapshot.completed_at - timedelta(days=1)
    task = create_daily_parent_task(p5_context, status="running", build_number=20)
    summary = daily_parent_summary(p5_context)
    summary["modules"][0].update(
        {
            "total_count": 2,
            "passed_count": 2,
            "case_results": [
                {
                    "node_id": "test_case/test_gbif_case/test_daily.py::test_backfill_passed",
                    "case_name": "test_backfill_passed",
                    "execution_status": "passed",
                    "error_type": "",
                    "error_message_summary": "",
                },
                {
                    "node_id": "test_case/test_gbif_case/test_daily.py::test_backfill_second",
                    "case_name": "test_backfill_second",
                    "execution_status": "passed",
                    "error_type": "",
                    "error_message_summary": "",
                },
            ],
        }
    )

    with patch(
        "metrics.views.fetch_jenkins_task_result",
        return_value={
            "jenkins_result": "SUCCESS",
            "finished_at": older_finished_at,
            "summary": summary,
            "failed_nodeids": [],
        },
    ):
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    assert model_field_state(snapshot, MODULE_SUMMARY_FIELDS) == snapshot_before
    assert set(
        metric_model("TestCaseResult")
        .objects.filter(module_snapshot=snapshot, is_current=True)
        .values_list("id", flat=True)
    ) == current_case_ids
    assert task.module is None
    assert task.run.module is None
    assert metric_model("ModuleRunHistory").objects.filter(source_run=task.run).count() == 2
    history = metric_model("ModuleRunHistory").objects.get(source_run=task.run, module=p5_context["module"])
    assert history.completed_at == older_finished_at
    assert history.total_count == 2
    assert history.failed_count == 0
    assert history.duration_seconds == Decimal("5.25")


def test_sync_module_rerun_without_case_results_preserves_current_cases(admin_client, p5_context):
    """旧版或损坏 summary 没有完整明细时，不得归档清空现有用例。"""
    snapshot = p5_context["module_snapshot"]
    environment_snapshot = p5_context["environment_snapshot"]
    snapshot_before = model_field_state(snapshot, MODULE_SUMMARY_FIELDS)
    environment_before = model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS)
    history_count_before = metric_model("ModuleRunHistory").objects.count()
    current_ids = set(
        metric_model("TestCaseResult")
        .objects.filter(module_snapshot=snapshot, is_current=True)
        .values_list("id", flat=True)
    )
    task = create_task(p5_context, status="running", task_type="module_rerun")

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "passed",
                "total_count": 3,
                "failed_count": 0,
                "passed_count": 3,
                "skipped_count": 0,
                "duration_seconds": 1.2,
                "failed_nodeids": [],
                "allure_report_status": "generated",
            },
            "failed_nodeids": [],
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    remaining_ids = set(
        metric_model("TestCaseResult")
        .objects.filter(module_snapshot=snapshot, is_current=True)
        .values_list("id", flat=True)
    )
    assert remaining_ids == current_ids
    assert model_field_state(snapshot, MODULE_SUMMARY_FIELDS) == snapshot_before
    assert model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS) == environment_before
    assert metric_model("ModuleRunHistory").objects.count() == history_count_before


def test_sync_module_rerun_with_inconsistent_case_counts_preserves_current_cases(admin_client, p5_context):
    """明细状态数与 summary 统计不一致时，不得替换当前用例。"""
    snapshot = p5_context["module_snapshot"]
    environment_snapshot = p5_context["environment_snapshot"]
    snapshot_before = model_field_state(snapshot, MODULE_SUMMARY_FIELDS)
    environment_before = model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS)
    history_count_before = metric_model("ModuleRunHistory").objects.count()
    current_ids = set(
        metric_model("TestCaseResult")
        .objects.filter(module_snapshot=snapshot, is_current=True)
        .values_list("id", flat=True)
    )
    task = create_task(p5_context, status="running", task_type="module_rerun")

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "passed",
                "total_count": 1,
                "failed_count": 0,
                "passed_count": 1,
                "skipped_count": 0,
                "case_results": [
                    {
                        "node_id": "test_case/test_gbif_case/test_species.py::test_inconsistent",
                        "case_name": "test_inconsistent",
                        "execution_status": "failed",
                        "error_type": "AssertionError",
                        "error_message_summary": "failed despite passed summary",
                    }
                ],
                "allure_report_status": "generated",
            },
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    remaining_ids = set(
        metric_model("TestCaseResult")
        .objects.filter(module_snapshot=snapshot, is_current=True)
        .values_list("id", flat=True)
    )
    assert remaining_ids == current_ids
    assert model_field_state(snapshot, MODULE_SUMMARY_FIELDS) == snapshot_before
    assert model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS) == environment_before
    assert metric_model("ModuleRunHistory").objects.count() == history_count_before
    assert "count" in task.error_summary.lower()


def test_sync_module_rerun_with_invalid_summary_counts_preserves_all_current_metrics(admin_client, p5_context):
    """统计字段不可解析时应安全降级，不得产生 500 或部分更新。"""
    snapshot = p5_context["module_snapshot"]
    environment_snapshot = p5_context["environment_snapshot"]
    snapshot_before = model_field_state(snapshot, MODULE_SUMMARY_FIELDS)
    environment_before = model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS)
    history_count_before = metric_model("ModuleRunHistory").objects.count()
    current_ids = set(
        metric_model("TestCaseResult").objects.filter(module_snapshot=snapshot, is_current=True).values_list("id", flat=True)
    )
    task = create_task(p5_context, status="running", task_type="module_rerun")

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "passed",
                "total_count": "invalid",
                "failed_count": 0,
                "passed_count": 0,
                "skipped_count": 0,
                "case_results": [],
                "allure_report_status": "generated",
            },
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    remaining_ids = set(
        metric_model("TestCaseResult").objects.filter(module_snapshot=snapshot, is_current=True).values_list("id", flat=True)
    )
    assert remaining_ids == current_ids
    assert model_field_state(snapshot, MODULE_SUMMARY_FIELDS) == snapshot_before
    assert model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS) == environment_before
    assert metric_model("ModuleRunHistory").objects.count() == history_count_before
    assert "invalid" in task.error_summary.lower()


@pytest.mark.parametrize("invalid_summary", [["invalid"], "invalid"])
def test_sync_module_rerun_with_non_object_summary_fails_safely_and_releases_lock(
    admin_client,
    p5_context,
    invalid_summary,
):
    """summary 顶层不是对象时也必须结束任务、释放锁并保留当前指标。"""
    snapshot = p5_context["module_snapshot"]
    environment_snapshot = p5_context["environment_snapshot"]
    snapshot_before = model_field_state(snapshot, MODULE_SUMMARY_FIELDS)
    environment_before = model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS)
    history_count_before = metric_model("ModuleRunHistory").objects.count()
    current_ids = set(
        metric_model("TestCaseResult").objects.filter(module_snapshot=snapshot, is_current=True).values_list("id", flat=True)
    )
    task = create_task(p5_context, status="running", task_type="module_rerun")
    execution_lock = metric_model("ModuleExecutionLock").objects.create(
        environment=p5_context["environment"],
        module=p5_context["module"],
        task=task,
        lock_type="module_execution",
        status="active",
        locked_at=timezone.now(),
    )

    with patch("metrics.views.fetch_jenkins_task_result") as fetch_result:
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": invalid_summary,
            "finished_at": timezone.now(),
        }
        response = admin_client.post(f"/api/v1/jenkins-tasks/{task.id}/sync", {}, format="json")

    assert response.status_code == 200
    task.refresh_from_db()
    execution_lock.refresh_from_db()
    remaining_ids = set(
        metric_model("TestCaseResult").objects.filter(module_snapshot=snapshot, is_current=True).values_list("id", flat=True)
    )
    assert task.status == "failed"
    assert "invalid" in task.error_summary.lower()
    assert execution_lock.status == "released"
    assert remaining_ids == current_ids
    assert model_field_state(snapshot, MODULE_SUMMARY_FIELDS) == snapshot_before
    assert model_field_state(environment_snapshot, ENVIRONMENT_SUMMARY_FIELDS) == environment_before
    assert metric_model("ModuleRunHistory").objects.count() == history_count_before


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
    create_daily_parent_binding()

    with patch("metrics.views.discover_jenkins_builds") as discover_builds:
        discover_builds.return_value = [
            {
                "job_full_name": DAILY_PARENT_JOB_NAME,
                "build_number": 88,
                "jenkins_build_url": f"http://localhost:8080/job/{DAILY_PARENT_JOB_NAME}/88/",
                "target_base_url": p5_context["environment"].base_url,
                "jenkins_result": "SUCCESS",
                "summary": daily_parent_summary(p5_context),
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
    assert task.module is None
    assert task.run.module is None
    p5_context["module_snapshot"].refresh_from_db()
    assert p5_context["module_snapshot"].failed_count == 0


def test_bulk_sync_fetches_daily_artifacts_with_discovered_run_id(admin_client, p5_context):
    create_daily_parent_binding()

    with patch("metrics.views.discover_jenkins_builds") as discover_builds, patch(
        "metrics.views.fetch_jenkins_task_result"
    ) as fetch_result:
        discover_builds.return_value = [
            {
                "job_full_name": DAILY_PARENT_JOB_NAME,
                "build_number": 88,
                "jenkins_build_url": f"http://localhost:8080/job/{DAILY_PARENT_JOB_NAME}/88/",
                "jenkins_result": "SUCCESS",
                "building": False,
                "run_id": "jenkins-AiApiTest-DWP-Daily-Full-Module-88",
                "target_base_url": p5_context["environment"].base_url,
            }
        ]
        fetch_result.return_value = {
            "jenkins_result": "SUCCESS",
            "summary": daily_parent_summary(p5_context),
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
    assert task.run.run_key == "jenkins-AiApiTest-DWP-Daily-Full-Module-88"
    assert task.module is None
    assert task.run.module is None
    fetch_result.assert_called_once()
    assert fetch_result.call_args.args[0].run.run_key == "jenkins-AiApiTest-DWP-Daily-Full-Module-88"


def test_bulk_sync_redacts_daily_discovery_service_error_from_response_and_log(admin_client, p5_context, caplog):
    create_daily_parent_binding()
    raw_error = "GET https://internal.example.invalid/jenkins?token=secret-token"

    with patch("metrics.views.discover_jenkins_builds") as discover_builds:
        discover_builds.side_effect = JenkinsServiceError(raw_error)
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 503
    assert response.data["error"]["code"] == "jenkins_unavailable"
    assert response.data["error"]["message"] == "Jenkins 服务暂不可用，请稍后重试。"
    assert raw_error not in str(response.data)
    assert raw_error not in caplog.text
    assert metric_model("JenkinsTask").objects.count() == 0


def test_bulk_sync_skips_daily_build_without_resolved_target_base_url(admin_client, p5_context):
    create_daily_parent_binding()

    with patch(
        "metrics.views.discover_jenkins_builds",
        return_value=[
            {
                "job_full_name": DAILY_PARENT_JOB_NAME,
                "build_number": 91,
                "jenkins_build_url": f"http://localhost:8080/job/{DAILY_PARENT_JOB_NAME}/91/",
                "building": True,
                "run_id": "jenkins-daily-parent-91",
                "started_at": timezone.now(),
            }
        ],
    ):
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["data"] == {"created_count": 0, "updated_count": 0, "synced_count": 0}
    assert metric_model("JenkinsTask").objects.count() == 0


def test_bulk_sync_continues_when_one_discovered_build_cannot_fetch_artifacts(admin_client, p5_context):
    create_daily_parent_binding()
    discovered = [
        {
            "job_full_name": DAILY_PARENT_JOB_NAME,
            "build_number": build_number,
            "jenkins_build_url": f"http://localhost:8080/job/{DAILY_PARENT_JOB_NAME}/{build_number}/",
            "building": False,
            "run_id": f"jenkins-daily-parent-{build_number}",
            "target_base_url": p5_context["environment"].base_url,
        }
        for build_number in (91, 92)
    ]

    with patch("metrics.views.discover_jenkins_builds", return_value=discovered), patch(
        "metrics.views.fetch_jenkins_task_result",
        side_effect=[
            JenkinsServiceError("Jenkins artifact unavailable"),
            {
                "build_number": 92,
                "jenkins_build_url": discovered[1]["jenkins_build_url"],
                "building": True,
                "started_at": timezone.now(),
            },
        ],
    ):
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["data"] == {"created_count": 2, "updated_count": 0, "synced_count": 1}
    failed_fetch_task = metric_model("JenkinsTask").objects.get(build_number=91)
    synced_task = metric_model("JenkinsTask").objects.get(build_number=92)
    assert failed_fetch_task.status == "running"
    assert synced_task.status == "running"


def test_bulk_sync_redacts_artifact_service_error_and_keeps_existing_daily_task_status(admin_client, p5_context, caplog):
    create_daily_parent_binding()
    existing_task = create_daily_parent_task(
        p5_context,
        status="running",
        queue_id="daily-queue",
        build_number=88,
    )
    raw_error = "GET https://internal.example.invalid/artifact?token=secret-token"

    with patch("metrics.views.discover_jenkins_builds") as discover_builds, patch(
        "metrics.views.fetch_jenkins_task_result"
    ) as fetch_result:
        discover_builds.return_value = [
            {
                "job_full_name": DAILY_PARENT_JOB_NAME,
                "build_number": 88,
                "jenkins_build_url": f"http://localhost:8080/job/{DAILY_PARENT_JOB_NAME}/88/",
                "building": False,
                "target_base_url": p5_context["environment"].base_url,
            }
        ]
        fetch_result.side_effect = JenkinsServiceError(raw_error)
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 503
    assert response.data["error"]["code"] == "jenkins_unavailable"
    assert response.data["error"]["message"] == "Jenkins 服务暂不可用，请稍后重试。"
    assert raw_error not in str(response.data)
    assert raw_error not in caplog.text
    existing_task.refresh_from_db()
    assert existing_task.status == "running"
    assert existing_task.module is None
    assert existing_task.run.module is None


def test_bulk_sync_does_not_report_ambiguous_build_as_jenkins_unavailable(admin_client, p5_context):
    create_daily_parent_binding()
    existing_task = create_daily_parent_task(
        p5_context,
        status="running",
        queue_id="daily-queue",
        build_number=88,
    )

    with patch("metrics.views.discover_jenkins_builds") as discover_builds, patch(
        "metrics.views.fetch_jenkins_task_result",
        side_effect=JenkinsBuildMatchError(match_kind="run_id", match_value=existing_task.run.run_key, match_count=2),
    ):
        discover_builds.return_value = [
            {
                "job_full_name": DAILY_PARENT_JOB_NAME,
                "build_number": 88,
                "jenkins_build_url": f"http://localhost:8080/job/{DAILY_PARENT_JOB_NAME}/88/",
                "building": False,
                "target_base_url": p5_context["environment"].base_url,
            }
        ]
        response = admin_client.post(
            "/api/v1/jenkins-tasks/sync",
            {"discover_daily": True, "date": "2026-07-05"},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["data"] == {"created_count": 0, "updated_count": 1, "synced_count": 0}
    existing_task.refresh_from_db()
    assert existing_task.status == "running"
    assert existing_task.module is None
    assert existing_task.run.module is None
    assert f"run_id={existing_task.run.run_key}" in existing_task.error_summary
    assert "matches=2" in existing_task.error_summary


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
