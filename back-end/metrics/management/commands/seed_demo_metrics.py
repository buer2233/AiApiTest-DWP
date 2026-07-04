from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from metrics.models import (
    EnvironmentSnapshot,
    ModuleRunHistory,
    ModuleSnapshot,
    TestCaseResult,
    TestEnvironment,
    TestModule,
    TestRun,
)


class Command(BaseCommand):
    help = "写入 P3 dev-only 演示快照、用例详情和趋势数据，供模块页验收。"

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
                "summary_json": {"source": "dev-only", "stage": "P3"},
            },
        )

        total_count = 0
        failed_count = 0
        passed_count = 0
        skipped_count = 0
        case_result_count = 0
        history_count = 0
        for index, module in enumerate(modules):
            module_skipped = 3 if index == 0 else 0
            module_total = 100
            module_failed = 4
            module_passed = module_total - module_failed - module_skipped
            total_count += module_total
            failed_count += module_failed
            passed_count += module_passed
            skipped_count += module_skipped
            module_snapshot, _ = ModuleSnapshot.objects.update_or_create(
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
            case_specs = [
                ("failed", "search_species", "AssertionError", "expected status_code == 200"),
                ("passed", "get_species", "", ""),
                ("skipped", "legacy_species", "", "历史接口人工跳过"),
            ]
            for display_status, case_suffix, error_type, assertion_text in case_specs:
                execution_status = display_status if display_status in {"passed", "skipped"} else "failed"
                node_id = f"{module.case_path}/test_demo.py::test_{case_suffix}"
                TestCaseResult.objects.update_or_create(
                    environment=environment,
                    module=module,
                    node_id=node_id,
                    is_current=True,
                    defaults={
                        "module_snapshot": module_snapshot,
                        "source_run": run,
                        "case_name": f"test_{case_suffix}",
                        "case_summary": f"{module.module_name} {case_suffix} 演示用例",
                        "assertion_text": assertion_text,
                        "error_type": error_type,
                        "error_message": "AssertionError: expected 200, got 500; Authorization: Bearer demo-token; password=demo",
                        "error_message_summary": "AssertionError: expected 200, got 500" if display_status == "failed" else "",
                        "execution_status": execution_status,
                        "display_status": display_status,
                        "confirmation_result": "人工确认中" if display_status == "failed" else "",
                        "occurred_at": finished_at,
                    },
                )
                case_result_count += 1

            # 生成 30 天趋势演示数据，供近 7/30 天弹窗共用；数据源只来自数据库，不由前端临时推算。
            for day_offset in range(29, -1, -1):
                run_date = (finished_at - timezone.timedelta(days=day_offset)).date()
                demo_failed = max(0, min(10, module_failed + ((day_offset % 5) - 2)))
                demo_skipped = module_skipped if day_offset % 4 else max(module_skipped, 1)
                ModuleRunHistory.objects.update_or_create(
                    environment=environment,
                    module=module,
                    source_run=run,
                    run_date=run_date,
                    run_type=TestRun.RunType.DAILY_FULL,
                    defaults={
                        "completed_at": finished_at - timezone.timedelta(days=day_offset),
                        "duration_seconds": Decimal("552.00"),
                        "total_count": module_total,
                        "failed_count": demo_failed,
                        "passed_count": module_total - demo_failed - demo_skipped,
                        "skipped_count": demo_skipped,
                        "pass_rate": Decimal(module_total - demo_failed) / Decimal(module_total),
                    },
                )
                history_count += 1

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
        self.stdout.write(
            f"seed_demo_metrics dev-only success case_results={case_result_count} module_run_history={history_count}"
        )
