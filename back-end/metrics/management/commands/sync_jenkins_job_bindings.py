from __future__ import annotations

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from metrics.models import JenkinsJobBinding, TestEnvironment, TestModule, TestRun


class Command(BaseCommand):
    help = "根据环境变量同步测试环境、模块与 Jenkins Job 的绑定关系。"

    def handle(self, *args, **options):
        environments = list(TestEnvironment.objects.filter(is_active=True).order_by("id"))
        modules = list(TestModule.objects.filter(is_active=True).order_by("id"))
        created = 0
        updated = 0
        skipped = 0

        fixed_jobs = {
            TestRun.RunType.FAILED_RERUN: os.getenv("JENKINS_FAILED_RERUN_JOB_NAME", "").strip(),
            TestRun.RunType.MODULE_RERUN: os.getenv("JENKINS_MODULE_RERUN_JOB_NAME", "").strip(),
        }
        daily_job_name = os.getenv("JENKINS_DAILY_FULL_JOB_NAME", "").strip()

        for task_type, job_full_name in fixed_jobs.items():
            if not job_full_name:
                skipped += len(environments) * len(modules)
                self.stdout.write(f"{task_type} skipped: job name is empty")
                continue
            type_created, type_updated = self._sync_task_type(environments, modules, task_type, job_full_name)
            created += type_created
            updated += type_updated

        if not daily_job_name:
            skipped += 1
            self.stdout.write(f"{TestRun.RunType.DAILY_FULL} skipped: job name is empty")
        else:
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
