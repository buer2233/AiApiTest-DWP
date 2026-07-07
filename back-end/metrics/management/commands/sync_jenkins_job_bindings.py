from __future__ import annotations

import os

from django.core.management.base import BaseCommand

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
        daily_prefix = os.getenv("JENKINS_DAILY_FULL_JOB_PREFIX", "").strip()

        for task_type, job_full_name in fixed_jobs.items():
            if not job_full_name:
                skipped += len(environments) * len(modules)
                self.stdout.write(f"{task_type} skipped: job name is empty")
                continue
            type_created, type_updated = self._sync_task_type(environments, modules, task_type, job_full_name)
            created += type_created
            updated += type_updated

        if not daily_prefix:
            skipped += len(environments) * len(modules)
            self.stdout.write(f"{TestRun.RunType.DAILY_FULL} skipped: job prefix is empty")
        else:
            for environment in environments:
                for module in modules:
                    job_full_name = f"{daily_prefix}-{module.package_name}"
                    was_created = self._upsert_binding(environment, module, TestRun.RunType.DAILY_FULL, job_full_name)
                    if was_created:
                        created += 1
                    else:
                        updated += 1

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
