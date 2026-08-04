from __future__ import annotations

from contextlib import contextmanager

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from metrics.models import JenkinsJobBinding, TestEnvironment, TestModule, TestRun


GLOBAL_DAILY_BINDING_LOCK_NAME = "ai_api_test_dwp:global_daily_binding"
GLOBAL_DAILY_BINDING_LOCK_TIMEOUT_SECONDS = 10


@contextmanager
def global_daily_binding_lock():
    """MySQL 首次创建全局 Daily 绑定时使用连接级互斥；SQLite 测试无需该锁。"""
    if connection.vendor != "mysql":
        yield
        return

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT GET_LOCK(%s, %s)",
            [GLOBAL_DAILY_BINDING_LOCK_NAME, GLOBAL_DAILY_BINDING_LOCK_TIMEOUT_SECONDS],
        )
        lock_result = cursor.fetchone()
    if not lock_result or lock_result[0] != 1:
        raise CommandError("Unable to acquire global Daily binding lock.")

    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT RELEASE_LOCK(%s)", [GLOBAL_DAILY_BINDING_LOCK_NAME])


class Command(BaseCommand):
    help = "按平台固定 Job 名同步测试环境、模块与 Jenkins Job 的绑定关系。"

    def handle(self, *args, **options):
        environments = list(TestEnvironment.objects.filter(is_active=True).order_by("id"))
        modules = list(TestModule.objects.filter(is_active=True).order_by("id"))
        created = 0
        updated = 0
        skipped = 0

        fixed_jobs = {
            TestRun.RunType.FAILED_RERUN: settings.JENKINS_FAILED_RERUN_JOB_NAME,
            TestRun.RunType.MODULE_RERUN: settings.JENKINS_MODULE_RERUN_JOB_NAME,
        }
        daily_job_name = settings.JENKINS_DAILY_FULL_JOB_NAME

        for task_type, job_full_name in fixed_jobs.items():
            type_created, type_updated = self._sync_task_type(environments, modules, task_type, job_full_name)
            created += type_created
            updated += type_updated

        with global_daily_binding_lock():
            with transaction.atomic():
                binding = (
                    JenkinsJobBinding.objects.select_for_update()
                    .filter(
                        environment__isnull=True,
                        module__isnull=True,
                        task_type=TestRun.RunType.DAILY_FULL,
                    )
                    .order_by("id")
                    .first()
                )
                if binding is None:
                    binding = JenkinsJobBinding.objects.create(
                        environment=None,
                        module=None,
                        task_type=TestRun.RunType.DAILY_FULL,
                        job_full_name=daily_job_name,
                        default_retry_count=0,
                        is_active=True,
                    )
                    created += 1
                else:
                    binding.job_full_name = daily_job_name
                    binding.default_retry_count = 0
                    binding.is_active = True
                    binding.save(update_fields=["job_full_name", "default_retry_count", "is_active", "updated_at"])
                    updated += 1
                JenkinsJobBinding.objects.filter(
                    environment__isnull=True,
                    module__isnull=True,
                    task_type=TestRun.RunType.DAILY_FULL,
                    is_active=True,
                ).exclude(id=binding.id).update(is_active=False)

        self.stdout.write(f"created={created} updated={updated} skipped={skipped}")

    def _sync_task_type(self, environments, modules, task_type: str, job_full_name: str) -> tuple[int, int]:
        created = 0
        updated = 0
        for environment in environments:
            for module in modules:
                was_created = self._upsert_binding(environment, module, task_type, job_full_name)
                if was_created:
                    created += 1
                else:
                    updated += 1
        return created, updated

    def _upsert_binding(self, environment, module, task_type: str, job_full_name: str) -> bool:
        _, was_created = JenkinsJobBinding.objects.update_or_create(
            environment=environment,
            module=module,
            task_type=task_type,
            defaults={
                "job_full_name": job_full_name,
                "default_retry_count": 0,
                "is_active": True,
            },
        )
        return was_created
