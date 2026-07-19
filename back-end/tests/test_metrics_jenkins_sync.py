from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from metrics.models import JenkinsJobBinding, JenkinsTask, ModuleExecutionLock, TestRun as MetricRun
from tests.p3_metrics_helpers import create_p3_metric_context


pytestmark = pytest.mark.command


@pytest.mark.django_db
def test_sync_cycle_discovers_daily_build_and_is_idempotent():
    from metrics.jenkins_sync import run_jenkins_sync_cycle

    context = create_p3_metric_context(suffix="-sync-cycle")
    binding = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )
    discovered = {
        "job_full_name": binding.job_full_name,
        "build_number": 88,
        "jenkins_build_url": "http://localhost:8080/job/daily/88/",
        "jenkins_result": "SUCCESS",
        "building": False,
        "run_id": "jenkins-daily-88",
        "target_base_url": context["environment"].base_url,
    }
    terminal_result = {
        "jenkins_result": "SUCCESS",
        "finished_at": context["now"],
        "summary": {
            "status": "passed",
            "module_count": 2,
            "total_count": 2,
            "failed_count": 0,
            "passed_count": 2,
            "skipped_count": 0,
            "failed_nodeids": [],
            "modules": [
                {
                    "module_key": context["module"].package_name,
                    "total_count": 1,
                    "failed_count": 0,
                    "passed_count": 1,
                    "skipped_count": 0,
                    "duration_seconds": 3.2,
                    "case_results": [{
                        "node_id": "test_case/test_gbif_case/test_daily.py::test_daily_passed",
                        "case_name": "test_daily_passed",
                        "execution_status": "passed",
                        "error_type": "",
                        "error_message_summary": "",
                    }],
                },
                {
                    "module_key": context["other_module"].package_name,
                    "total_count": 1,
                    "failed_count": 0,
                    "passed_count": 1,
                    "skipped_count": 0,
                    "duration_seconds": 3.2,
                    "case_results": [{
                        "node_id": "test_case/test_other_case/test_daily.py::test_daily_passed",
                        "case_name": "test_daily_passed",
                        "execution_status": "passed",
                        "error_type": "",
                        "error_message_summary": "",
                    }],
                },
            ],
        },
        "failed_nodeids": [],
    }

    with patch("metrics.jenkins_sync.discover_jenkins_builds", return_value=[discovered]), patch(
        "metrics.jenkins_sync.fetch_jenkins_task_result", return_value=terminal_result
    ) as fetch_result:
        first = run_jenkins_sync_cycle()
        second = run_jenkins_sync_cycle()

    task = JenkinsTask.objects.get(job_full_name=binding.job_full_name, build_number=88)
    assert task.status == MetricRun.Status.SUCCESS
    assert JenkinsTask.objects.filter(job_full_name=binding.job_full_name, build_number=88).count() == 1
    assert first["daily_discovered"] == 1
    assert second["skipped"] >= 1
    fetch_result.assert_called_once()


@pytest.mark.django_db
def test_sync_cycle_continues_after_one_active_task_service_error(caplog):
    from metrics.jenkins_service import JenkinsServiceError
    from metrics.jenkins_sync import run_jenkins_sync_cycle

    context = create_p3_metric_context(suffix="-sync-isolation")
    tasks = []
    for index in range(2):
        run = MetricRun.objects.create(
            run_key=f"module-rerun-sync-isolation-{index}",
            run_type=MetricRun.RunType.MODULE_RERUN,
            environment=context["environment"],
            module=context["module"],
            status=MetricRun.Status.QUEUED,
        )
        tasks.append(
            JenkinsTask.objects.create(
                run=run,
                environment=context["environment"],
                module=context["module"],
                task_type=MetricRun.RunType.MODULE_RERUN,
                job_full_name="AiApiTest-DWP-Module-Rerun",
                queue_id=f"sync-isolation-{index}",
                status=MetricRun.Status.QUEUED,
            )
        )

    def fake_fetch(task):
        if task.id == tasks[0].id:
            raise JenkinsServiceError("temporary upstream failure")
        return {"queue_pending": True}

    with patch("metrics.jenkins_sync.fetch_jenkins_task_result", side_effect=fake_fetch), patch(
        "metrics.jenkins_sync.discover_jenkins_builds", return_value=[]
    ), caplog.at_level("WARNING", logger="metrics.jenkins_sync"):
        result = run_jenkins_sync_cycle()

    tasks[1].refresh_from_db()
    assert result["failed"] == 1
    assert result["active_processed"] == 2
    assert tasks[1].last_synced_at is not None
    assert f"task_id={tasks[0].id}" in caplog.text
    assert "error_type=JenkinsServiceError" in caplog.text
    assert "temporary upstream failure" not in caplog.text


@pytest.mark.django_db
def test_sync_cycle_records_the_single_daily_job_discovery_error_without_leaking_details(caplog):
    from metrics.jenkins_service import JenkinsServiceError
    from metrics.jenkins_sync import run_jenkins_sync_cycle

    binding = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )

    with patch(
        "metrics.jenkins_sync.discover_jenkins_builds",
        side_effect=JenkinsServiceError("internal URL must not be logged"),
    ) as discover, caplog.at_level(
        "WARNING", logger="metrics.jenkins_sync"
    ):
        result = run_jenkins_sync_cycle()

    discover.assert_called_once_with(job_full_names=[binding.job_full_name])
    assert result["failed"] == 1
    assert "binding_id=" in caplog.text
    assert "error_type=JenkinsServiceError" in caplog.text
    assert "internal URL" not in caplog.text


@pytest.mark.django_db
def test_sync_cycle_expires_stale_queue_pending_task_and_releases_lock():
    from metrics.jenkins_sync import run_jenkins_sync_cycle

    context = create_p3_metric_context(suffix="-sync-stale")
    stale_at = timezone.now() - timezone.timedelta(hours=3)
    run = MetricRun.objects.create(
        run_key="module-rerun-sync-stale",
        run_type=MetricRun.RunType.MODULE_RERUN,
        environment=context["environment"],
        module=context["module"],
        status=MetricRun.Status.QUEUED,
    )
    task = JenkinsTask.objects.create(
        run=run,
        environment=context["environment"],
        module=context["module"],
        task_type=MetricRun.RunType.MODULE_RERUN,
        job_full_name="AiApiTest-DWP-Module-Rerun",
        queue_id="sync-stale",
        status=MetricRun.Status.QUEUED,
    )
    JenkinsTask.objects.filter(id=task.id).update(created_at=stale_at, updated_at=stale_at)
    lock = ModuleExecutionLock.objects.create(
        environment=context["environment"],
        module=context["module"],
        task=task,
        status=ModuleExecutionLock.Status.ACTIVE,
        locked_at=stale_at,
    )

    with patch("metrics.jenkins_sync.fetch_jenkins_task_result", return_value={"queue_pending": True}), patch(
        "metrics.jenkins_sync.discover_jenkins_builds", return_value=[]
    ):
        result = run_jenkins_sync_cycle()

    task.refresh_from_db()
    lock.refresh_from_db()
    assert task.status == MetricRun.Status.FAILED
    assert lock.status == ModuleExecutionLock.Status.EXPIRED
    assert result["synced"] == 1


@pytest.mark.django_db
def test_daily_discovery_reuses_task_created_by_another_worker_after_unique_conflict():
    from metrics.views import create_or_get_daily_task_from_discovery

    context = create_p3_metric_context(suffix="-sync-race")
    binding = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )
    existing_run = MetricRun.objects.create(
        run_key="jenkins-sync-race-88",
        run_type=MetricRun.RunType.DAILY_FULL,
        environment=context["environment"],
        module=None,
        status=MetricRun.Status.RUNNING,
    )
    existing_task = JenkinsTask.objects.create(
        run=existing_run,
        environment=context["environment"],
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        trigger_source=JenkinsTask.TriggerSource.JENKINS_CRON,
        job_full_name=binding.job_full_name,
        build_number=88,
        status=MetricRun.Status.RUNNING,
    )
    initial_run_count = MetricRun.objects.count()
    no_existing_task = MagicMock()
    no_existing_task.filter.return_value.first.return_value = None

    with patch.object(JenkinsTask.objects, "select_related", return_value=no_existing_task), patch.object(
        JenkinsTask.objects,
        "create",
        side_effect=IntegrityError("duplicate job/build"),
    ):
        task, created = create_or_get_daily_task_from_discovery(
            binding,
            {
                "job_full_name": binding.job_full_name,
                "build_number": 88,
                "run_id": "jenkins-sync-race-88",
                "target_base_url": context["environment"].base_url,
            },
        )

    assert created is False
    assert task.id == existing_task.id
    assert task.module is None
    assert task.run.module is None
    assert MetricRun.objects.count() == initial_run_count
