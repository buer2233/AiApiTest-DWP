from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from metrics.models import EnvironmentSnapshot, ModuleSnapshot, TestEnvironment, TestModule, TestRun


class Command(BaseCommand):
    help = "写入 P2 dev-only 演示快照数据，供只读页面验收。"

    def handle(self, *args, **options):
        environment = TestEnvironment.objects.filter(env_key="mock-gbif", is_active=True).first()
        if environment is None:
            raise CommandError("请先执行 seed_environment。")

        modules = list(TestModule.objects.filter(is_active=True).order_by("package_name"))
        if not modules:
            raise CommandError("请先执行 sync_modules。")

        finished_at = timezone.now().replace(microsecond=0)
        started_at = finished_at - timezone.timedelta(minutes=18, seconds=24)
        run, _ = TestRun.objects.update_or_create(
            run_key="demo-daily-full",
            defaults={
                "run_type": TestRun.RunType.DAILY_FULL,
                "environment": environment,
                "module": None,
                "status": TestRun.Status.SUCCESS,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_seconds": Decimal("1104.00"),
                "summary_json": {"source": "dev-only", "stage": "P2"},
            },
        )

        total_count = 0
        failed_count = 0
        passed_count = 0
        skipped_count = 0
        for index, module in enumerate(modules):
            module_skipped = 3 if index == 0 else 0
            module_total = 100
            module_failed = 4
            module_passed = module_total - module_failed - module_skipped
            total_count += module_total
            failed_count += module_failed
            passed_count += module_passed
            skipped_count += module_skipped
            ModuleSnapshot.objects.update_or_create(
                environment=environment,
                module=module,
                defaults={
                    "latest_run": run,
                    "completed_at": finished_at,
                    "duration_seconds": Decimal("552.00"),
                    "total_count": module_total,
                    "failed_count": module_failed,
                    "passed_count": module_passed,
                    "skipped_count": module_skipped,
                    "pass_rate": Decimal(module_total - module_failed) / Decimal(module_total),
                },
            )

        EnvironmentSnapshot.objects.update_or_create(
            environment=environment,
            defaults={
                "latest_run": run,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_seconds": Decimal("1104.00"),
                "total_count": total_count,
                "failed_count": failed_count,
                "passed_count": passed_count,
                "skipped_count": skipped_count,
                "pass_rate": (Decimal(total_count - failed_count) / Decimal(total_count)) if total_count else Decimal("0"),
            },
        )
        self.stdout.write("seed_demo_metrics dev-only success")
