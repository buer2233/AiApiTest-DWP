from __future__ import annotations

from decimal import Decimal

from django.apps import apps
from django.utils import timezone

from metrics.models import (
    EnvironmentSnapshot,
    ModuleSnapshot,
    TestEnvironment as MetricEnvironment,
    TestModule as MetricModule,
    TestRun as MetricRun,
)


def metric_model(model_name: str):
    return apps.get_model("metrics", model_name)


def create_p3_metric_context(*, suffix: str = "") -> dict:
    now = timezone.datetime(2026, 7, 4, 9, 18, 24, tzinfo=timezone.get_current_timezone())
    started_at = now - timezone.timedelta(minutes=18, seconds=24)
    environment = MetricEnvironment.objects.create(
        env_key=f"mock-gbif{suffix}",
        env_name="模拟测试环境",
        base_url="https://api.gbif.org",
        is_active=True,
    )
    module = MetricModule.objects.create(
        package_name=f"test_gbif_case{suffix}",
        case_path=f"test_case/test_gbif_case{suffix}",
        module_name="示例模块1",
        module_dev="张三",
        module_test="王五",
    )
    other_module = MetricModule.objects.create(
        package_name=f"test_other_case{suffix}",
        case_path=f"test_case/test_other_case{suffix}",
        module_name="示例模块2",
        module_dev="赵四",
        module_test="王麻子",
    )
    run = MetricRun.objects.create(
        run_key=f"demo-daily-full{suffix}",
        run_type=MetricRun.RunType.DAILY_FULL,
        environment=environment,
        status=MetricRun.Status.SUCCESS,
        started_at=started_at,
        finished_at=now,
        duration_seconds=Decimal("1104.00"),
        summary_json={"source": "test"},
    )
    environment_snapshot = EnvironmentSnapshot.objects.create(
        environment=environment,
        latest_run=run,
        started_at=started_at,
        finished_at=now,
        duration_seconds=Decimal("1104.00"),
        total_count=100,
        failed_count=4,
        passed_count=93,
        skipped_count=3,
        pass_rate=Decimal("0.960000"),
    )
    module_snapshot = ModuleSnapshot.objects.create(
        environment=environment,
        module=module,
        latest_run=run,
        completed_at=now,
        duration_seconds=Decimal("552.00"),
        total_count=100,
        failed_count=4,
        passed_count=93,
        skipped_count=3,
        pass_rate=Decimal("0.960000"),
    )
    other_snapshot = ModuleSnapshot.objects.create(
        environment=environment,
        module=other_module,
        latest_run=run,
        completed_at=now,
        duration_seconds=Decimal("552.00"),
        total_count=50,
        failed_count=1,
        passed_count=49,
        skipped_count=0,
        pass_rate=Decimal("0.980000"),
    )
    return {
        "environment": environment,
        "module": module,
        "other_module": other_module,
        "run": run,
        "environment_snapshot": environment_snapshot,
        "module_snapshot": module_snapshot,
        "other_snapshot": other_snapshot,
        "now": now,
    }


def create_case_result(context: dict, *, display_status: str, node_suffix: str, is_current: bool = True):
    TestCaseResult = metric_model("TestCaseResult")
    return TestCaseResult.objects.create(
        environment=context["environment"],
        module=context["module"],
        module_snapshot=context["module_snapshot"],
        source_run=context["run"],
        node_id=f"test_case/test_gbif_case/test_species.py::test_{node_suffix}",
        case_name=f"test_{node_suffix}",
        case_summary=f"{node_suffix} 用例摘要",
        assertion_text="expected status_code == 200",
        error_type="AssertionError" if display_status == "failed" else "",
        error_message=(
            "AssertionError: expected 200, got 500; Authorization: Bearer demo-token; "
            "password=demo; Cookie: sessionid=secret; callback=http://10.0.0.5/internal?token=private"
        ),
        error_message_summary="AssertionError: expected 200, got 500",
        execution_status=display_status if display_status in {"passed", "skipped"} else "failed",
        display_status=display_status,
        confirmation_result="人工确认中",
        is_current=is_current,
        occurred_at=context["now"],
    )


def create_trend_row(context: dict, *, day_offset: int, failed_count: int, module_key: str = "module"):
    ModuleRunHistory = metric_model("ModuleRunHistory")
    module = context[module_key]
    total_count = 100
    skipped_count = 2
    return ModuleRunHistory.objects.create(
        environment=context["environment"],
        module=module,
        source_run=context["run"],
        run_date=(context["now"] - timezone.timedelta(days=day_offset)).date(),
        run_type=MetricRun.RunType.DAILY_FULL,
        completed_at=context["now"] - timezone.timedelta(days=day_offset),
        duration_seconds=Decimal("552.00"),
        total_count=total_count,
        failed_count=failed_count,
        passed_count=total_count - failed_count - skipped_count,
        skipped_count=skipped_count,
        pass_rate=Decimal(total_count - failed_count) / Decimal(total_count),
    )
