from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
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


def _decorator_name(decorator: ast.expr) -> str:
    if isinstance(decorator, ast.Call):
        return _decorator_name(decorator.func)
    if isinstance(decorator, ast.Attribute):
        parent = _decorator_name(decorator.value)
        return f"{parent}.{decorator.attr}" if parent else decorator.attr
    if isinstance(decorator, ast.Name):
        return decorator.id
    return ""


def _has_skip_marker(decorators: list[ast.expr]) -> bool:
    return any(_decorator_name(decorator).endswith(("skip", "skipif")) for decorator in decorators)


def _iter_test_functions(module_case_path: Path, api_test_root: Path) -> list[dict[str, object]]:
    if not module_case_path.exists():
        return []

    case_specs: list[dict[str, object]] = []
    for test_file in sorted(module_case_path.rglob("test*.py")):
        tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        relative_file = test_file.relative_to(api_test_root).as_posix()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                case_specs.append(
                    {
                        "node_id": f"{relative_file}::{node.name}",
                        "case_name": node.name,
                        "is_skipped": _has_skip_marker(node.decorator_list),
                    }
                )
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                class_skipped = _has_skip_marker(node.decorator_list)
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                        case_specs.append(
                            {
                                "node_id": f"{relative_file}::{node.name}::{child.name}",
                                "case_name": child.name,
                                "is_skipped": class_skipped or _has_skip_marker(child.decorator_list),
                            }
                        )
    return case_specs


def _display_status_for_case(case_name: str, is_skipped: bool) -> str:
    if is_skipped:
        return TestCaseResult.DisplayStatus.SKIPPED
    if "deliberate_assertion_failure" in case_name or "deliberate_failure" in case_name:
        return TestCaseResult.DisplayStatus.FAILED
    return TestCaseResult.DisplayStatus.PASSED


def _pass_rate(total_count: int, failed_count: int) -> Decimal:
    return (Decimal(total_count - failed_count) / Decimal(total_count)) if total_count else Decimal("0")


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
        api_test_root = settings.REPO_ROOT / "api-test"
        for index, module in enumerate(modules):
            case_specs = _iter_test_functions(api_test_root / module.case_path, api_test_root)
            module_total = len(case_specs)
            module_failed = sum(
                1
                for case_spec in case_specs
                if _display_status_for_case(str(case_spec["case_name"]), bool(case_spec["is_skipped"]))
                == TestCaseResult.DisplayStatus.FAILED
            )
            module_skipped = sum(1 for case_spec in case_specs if bool(case_spec["is_skipped"]))
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
                    "pass_rate": _pass_rate(module_total, module_failed),
                },
            )
            current_node_ids = {str(case_spec["node_id"]) for case_spec in case_specs}
            TestCaseResult.objects.filter(environment=environment, module=module, is_current=True).exclude(
                node_id__in=current_node_ids
            ).update(is_current=False, current_node_key=None)
            for case_spec in case_specs:
                case_name = str(case_spec["case_name"])
                display_status = _display_status_for_case(case_name, bool(case_spec["is_skipped"]))
                execution_status = (
                    TestCaseResult.ExecutionStatus.FAILED
                    if display_status == TestCaseResult.DisplayStatus.FAILED
                    else display_status
                )
                error_type = "AssertionError" if display_status == TestCaseResult.DisplayStatus.FAILED else ""
                assertion_text = "演示失败：断言不满足" if display_status == TestCaseResult.DisplayStatus.FAILED else ""
                if display_status == TestCaseResult.DisplayStatus.SKIPPED:
                    assertion_text = "pytest skip marker"
                TestCaseResult.objects.update_or_create(
                    environment=environment,
                    module=module,
                    node_id=str(case_spec["node_id"]),
                    is_current=True,
                    defaults={
                        "module_snapshot": module_snapshot,
                        "source_run": run,
                        "case_name": case_name,
                        "case_summary": f"{module.module_name} {case_name}",
                        "assertion_text": assertion_text,
                        "error_type": error_type,
                        "error_message": "AssertionError: 演示失败，断言不满足"
                        if display_status == TestCaseResult.DisplayStatus.FAILED
                        else "",
                        "error_message_summary": "AssertionError: 演示失败"
                        if display_status == TestCaseResult.DisplayStatus.FAILED
                        else "",
                        "execution_status": execution_status,
                        "display_status": display_status,
                        "confirmation_result": "人工确认中" if display_status == TestCaseResult.DisplayStatus.FAILED else "",
                        "occurred_at": finished_at,
                    },
                )
                case_result_count += 1

            # 生成 30 天趋势演示数据，供近 7/30 天弹窗共用；数据源只来自数据库，不由前端临时推算。
            for day_offset in range(29, -1, -1):
                run_date = (finished_at - timezone.timedelta(days=day_offset)).date()
                demo_failed = max(0, min(module_total, module_failed + ((day_offset % 5) - 2)))
                demo_skipped = module_skipped if day_offset % 4 else max(module_skipped, 1 if module_total else 0)
                demo_skipped = min(demo_skipped, max(0, module_total - demo_failed))
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
                        "passed_count": max(0, module_total - demo_failed - demo_skipped),
                        "skipped_count": demo_skipped,
                        "pass_rate": _pass_rate(module_total, demo_failed),
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
                "pass_rate": _pass_rate(total_count, failed_count),
            },
        )
        self.stdout.write(
            f"seed_demo_metrics dev-only success case_results={case_result_count} module_run_history={history_count}"
        )
