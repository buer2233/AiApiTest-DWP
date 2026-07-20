from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from metrics.models import (
    JenkinsJobBinding,
    JenkinsTask,
    ModuleRunHistory,
    ModuleSnapshot,
    TestEnvironment as MetricEnvironment,
    TestModule as MetricModule,
    TestRun as MetricRun,
)


pytestmark = pytest.mark.api


def create_environment() -> MetricEnvironment:
    return MetricEnvironment.objects.create(
        env_key="stage13-daily-qa",
        env_name="Stage13 Daily QA",
        base_url="https://stage13-daily.example.invalid/api",
        url_desc="Daily 父任务测试环境",
        is_active=True,
    )


def create_module(package_name: str) -> MetricModule:
    return MetricModule.objects.create(
        package_name=package_name,
        case_path=f"test_case/{package_name}",
        module_name=f"{package_name} 模块",
        module_dev="开发",
        module_test="测试",
        is_active=True,
    )


def module_detail(*, module_key: str, status: str, node_id: str) -> dict:
    failed_count = 1 if status == "failed" else 0
    return {
        "module_key": module_key,
        "status": status,
        "return_code": 1 if status == "failed" else 0,
        "total_count": 1,
        "passed_count": 1 - failed_count,
        "failed_count": failed_count,
        "error_count": 0,
        "skipped_count": 0,
        "failed_nodeids": [node_id] if failed_count else [],
        "case_results": [
            {
                "node_id": node_id,
                "case_name": node_id.rsplit("::", maxsplit=1)[-1],
                "execution_status": status,
                "error_type": "AssertionError" if failed_count else "",
                "error_message_summary": "预期失败" if failed_count else "",
            }
        ],
    }


@pytest.mark.django_db
def test_daily_parent_summary_creates_one_moduleless_task_and_idempotently_updates_each_module():
    from metrics.views import create_or_get_daily_task_from_discovery, sync_task_with_result

    environment = create_environment()
    alpha = create_module("module-alpha")
    beta = create_module("module-beta")
    ModuleSnapshot.objects.create(environment=environment, module=alpha)
    ModuleSnapshot.objects.create(environment=environment, module=beta)
    binding = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )
    build_result = {
        "job_full_name": binding.job_full_name,
        "build_number": 101,
        "run_id": "daily-parent-101",
        "target_base_url": environment.base_url,
        "jenkins_build_url": "https://ci.example.invalid/job/daily/101/",
    }

    task, created = create_or_get_daily_task_from_discovery(binding, build_result)
    summary = {
        "status": "failed",
        "module_count": 2,
        "total_count": 2,
        "passed_count": 1,
        "failed_count": 1,
        "error_count": 0,
        "skipped_count": 0,
        "failed_nodeids": ["test_case/module-beta/test_api.py::test_failed"],
        "modules": [
            module_detail(
                module_key="module-alpha",
                status="passed",
                node_id="test_case/module-alpha/test_api.py::test_passed",
            ),
            module_detail(
                module_key="module-beta",
                status="failed",
                node_id="test_case/module-beta/test_api.py::test_failed",
            ),
        ],
    }

    synced = sync_task_with_result(
        task,
        {
            "jenkins_result": "FAILURE",
            "summary": summary,
            "finished_at": timezone.now(),
        },
    )

    assert created is True
    assert synced.status == MetricRun.Status.TEST_FAILED
    assert synced.module is None
    assert synced.run.module is None
    assert JenkinsTask.objects.filter(task_type=MetricRun.RunType.DAILY_FULL, build_number=101).count() == 1
    alpha_snapshot = ModuleSnapshot.objects.get(environment=environment, module=alpha)
    beta_snapshot = ModuleSnapshot.objects.get(environment=environment, module=beta)
    assert alpha_snapshot.pass_rate == Decimal("1.000000")
    assert beta_snapshot.failed_count == 1
    assert ModuleRunHistory.objects.filter(source_run=synced.run).count() == 2

    sync_task_with_result(synced, {"summary": summary, "finished_at": timezone.now()})
    assert ModuleRunHistory.objects.filter(source_run=synced.run).count() == 2
    assert JenkinsTask.objects.filter(task_type=MetricRun.RunType.DAILY_FULL, build_number=101).count() == 1


@pytest.mark.django_db
def test_daily_parent_summary_preserves_valid_module_projection_when_another_module_snapshot_is_missing():
    from metrics.views import create_or_get_daily_task_from_discovery, sync_task_with_result

    environment = create_environment()
    alpha = create_module("module-alpha")
    beta = create_module("module-beta")
    ModuleSnapshot.objects.create(environment=environment, module=alpha)
    binding = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )
    task, _ = create_or_get_daily_task_from_discovery(
        binding,
        {
            "job_full_name": binding.job_full_name,
            "build_number": 103,
            "run_id": "daily-parent-103",
            "target_base_url": environment.base_url,
        },
    )

    synced = sync_task_with_result(
        task,
        {
            "jenkins_result": "SUCCESS",
            "summary": {
                "status": "passed",
                "module_count": 2,
                "modules": [
                    module_detail(
                        module_key=alpha.package_name,
                        status="passed",
                        node_id="test_case/module-alpha/test_api.py::test_passed",
                    ),
                    module_detail(
                        module_key=beta.package_name,
                        status="passed",
                        node_id="test_case/module-beta/test_api.py::test_passed",
                    ),
                ],
            },
            "finished_at": timezone.now(),
        },
    )

    alpha_snapshot = ModuleSnapshot.objects.get(environment=environment, module=alpha)
    assert alpha_snapshot.pass_rate == Decimal("1.000000")
    assert ModuleRunHistory.objects.filter(source_run=synced.run, module=alpha).exists()
    assert synced.status == MetricRun.Status.FAILED
    assert synced.run.status == MetricRun.Status.FAILED
    assert beta.package_name in synced.error_summary


@pytest.mark.django_db
@pytest.mark.parametrize("jenkins_result", ["FAILURE", "UNSTABLE"])
def test_daily_parent_passed_summary_is_failed_when_jenkins_result_is_not_success(jenkins_result):
    """父级摘要已通过不能掩盖归档后 Allure 发布导致的 Jenkins FAILURE。"""
    from metrics.serializers import JenkinsTaskSerializer
    from metrics.views import create_or_get_daily_task_from_discovery, sync_task_with_result

    environment = create_environment()
    module = create_module("module-allure-failure")
    ModuleSnapshot.objects.create(environment=environment, module=module)
    binding = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )
    task, _ = create_or_get_daily_task_from_discovery(
        binding,
        {
            "job_full_name": binding.job_full_name,
            "build_number": 104,
            "run_id": "daily-parent-104",
            "target_base_url": environment.base_url,
            "jenkins_build_url": "https://ci.example.invalid/job/daily/104/",
        },
    )

    synced = sync_task_with_result(
        task,
        {
            "jenkins_result": jenkins_result,
            "summary": {
                "status": "passed",
                "module_count": 1,
                "modules": [
                    module_detail(
                        module_key=module.package_name,
                        status="passed",
                        node_id="test_case/module-allure-failure/test_api.py::test_passed",
                    )
                ],
            },
            "allure_report_url": "https://ci.example.invalid/job/daily/104/allure/",
            "finished_at": timezone.now(),
        },
    )

    serialized = JenkinsTaskSerializer(synced).data
    assert synced.status == MetricRun.Status.FAILED
    assert synced.run.status == MetricRun.Status.FAILED
    assert synced.allure_report_url == ""
    assert serialized["allure_report_url"] == ""
    assert serialized["actions"]["view_report"] is False


@pytest.mark.django_db
def test_daily_parent_aborted_build_remains_canceled_before_summary_status_is_evaluated():
    """ABORTED 仍优先映射为取消，不能被 Daily 摘要通过状态覆盖。"""
    from metrics.views import sync_task_with_result

    environment = create_environment()
    run = MetricRun.objects.create(
        run_key="daily-parent-aborted",
        run_type=MetricRun.RunType.DAILY_FULL,
        environment=environment,
        status=MetricRun.Status.RUNNING,
    )
    task = JenkinsTask.objects.create(
        run=run,
        environment=environment,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        build_number=105,
        status=MetricRun.Status.RUNNING,
    )

    synced = sync_task_with_result(
        task,
        {
            "jenkins_result": "ABORTED",
            "summary": {"status": "passed"},
            "finished_at": timezone.now(),
        },
    )

    assert synced.status == MetricRun.Status.CANCELED
    assert synced.run.status == MetricRun.Status.CANCELED


@pytest.mark.django_db
def test_daily_parent_without_resolved_environment_does_not_create_a_platform_task():
    from metrics.views import DailyParentEnvironmentError, create_or_get_daily_task_from_discovery

    binding = JenkinsJobBinding.objects.create(
        environment=None,
        module=None,
        task_type=MetricRun.RunType.DAILY_FULL,
        job_full_name="AiApiTest-DWP-Daily-Full-Module",
        is_active=True,
    )

    with pytest.raises(DailyParentEnvironmentError):
        create_or_get_daily_task_from_discovery(
            binding,
            {
                "job_full_name": binding.job_full_name,
                "build_number": 102,
                "run_id": "daily-parent-102",
            },
        )

    assert JenkinsTask.objects.count() == 0
    assert MetricRun.objects.count() == 0
