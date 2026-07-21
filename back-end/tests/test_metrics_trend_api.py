from __future__ import annotations

from datetime import datetime, timedelta, timezone as datetime_timezone
from decimal import Decimal

import pytest
from django.apps import apps
from django.utils import timezone as django_timezone

from tests.p3_metrics_helpers import create_p3_metric_context, create_trend_row


pytestmark = pytest.mark.api


def create_history_row(context, *, run_date, run_type, completed_at, failed_count):
    TestRun = apps.get_model("metrics", "TestRun")
    ModuleRunHistory = apps.get_model("metrics", "ModuleRunHistory")
    total_count = 10
    skipped_count = 1
    source_run = TestRun.objects.create(
        run_key=f"trend-{run_type}-{completed_at.timestamp() if completed_at else 'none'}-{ModuleRunHistory.objects.count()}",
        run_type=run_type,
        environment=context["environment"],
        module=context["module"],
        status="success",
        finished_at=completed_at,
    )
    return ModuleRunHistory.objects.create(
        environment=context["environment"],
        module=context["module"],
        source_run=source_run,
        run_date=run_date,
        run_type=run_type,
        completed_at=completed_at,
        duration_seconds=Decimal("5.00"),
        total_count=total_count,
        failed_count=failed_count,
        passed_count=total_count - failed_count - skipped_count,
        skipped_count=skipped_count,
        pass_rate=Decimal(total_count - failed_count) / Decimal(total_count),
    )


@pytest.fixture
def trend_context(db, monkeypatch) -> dict:
    context = create_p3_metric_context(suffix="-trend")
    monkeypatch.setattr("metrics.views.timezone.localdate", lambda: context["now"].date())
    create_trend_row(context, day_offset=2, failed_count=6)
    create_trend_row(context, day_offset=1, failed_count=3)
    create_trend_row(context, day_offset=1, failed_count=1, module_key="other_module")
    return context


def test_trend_7d_returns_current_module_series_sorted_ascending(admin_client, trend_context):
    snapshot = trend_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/trend", {"days": 7})

    assert response.status_code == 200
    data = response.data["data"]
    assert data["module"] == {
        "snapshot_id": snapshot.id,
        "module_name": "示例模块1",
        "package_name": "test_gbif_case-trend",
        "environment_name": "模拟测试环境",
    }
    assert data["days"] == 7
    assert [row["failed_count"] for row in data["series"]] == [6, 3]
    assert [row["pass_rate"] for row in data["series"]] == ["0.940000", "0.970000"]
    assert data["series"][0]["run_date"] < data["series"][1]["run_date"]


def test_trend_30d_accepts_window_and_limits_to_snapshot_module(admin_client, trend_context):
    snapshot = trend_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/trend", {"days": 30})

    assert response.status_code == 200
    assert response.data["data"]["days"] == 30
    assert len(response.data["data"]["series"]) == 2
    assert all(row["run_type"] == "daily_full" for row in response.data["data"]["series"])


@pytest.mark.parametrize("days", [7, 30])
def test_trend_deduplicates_each_date_and_prefers_latest_module_rerun(admin_client, db, days, monkeypatch):
    context = create_p3_metric_context(suffix=f"-trend-dedup-{days}")
    monkeypatch.setattr("metrics.views.timezone.localdate", lambda: context["now"].date())
    today = context["now"].date()
    yesterday = today - timedelta(days=1)

    create_history_row(
        context,
        run_date=today,
        run_type="daily_full",
        completed_at=context["now"] - timedelta(hours=4),
        failed_count=0,
    )
    create_history_row(
        context,
        run_date=today,
        run_type="module_rerun",
        completed_at=context["now"] - timedelta(hours=2),
        failed_count=3,
    )
    create_history_row(
        context,
        run_date=today,
        run_type="module_rerun",
        completed_at=context["now"] - timedelta(hours=1),
        failed_count=2,
    )
    latest_module = create_history_row(
        context,
        run_date=today,
        run_type="module_rerun",
        completed_at=context["now"] - timedelta(hours=1),
        failed_count=1,
    )
    create_history_row(
        context,
        run_date=yesterday,
        run_type="daily_full",
        completed_at=context["now"] - timedelta(days=1, hours=3),
        failed_count=4,
    )
    latest_daily = create_history_row(
        context,
        run_date=yesterday,
        run_type="daily_full",
        completed_at=context["now"] - timedelta(days=1, hours=1),
        failed_count=2,
    )

    response = admin_client.get(f"/api/v1/module-snapshots/{context['module_snapshot'].id}/trend", {"days": days})

    assert response.status_code == 200
    series = response.data["data"]["series"]
    assert len(series) == 2
    assert [row["run_date"] for row in series] == sorted({str(yesterday), str(today)})
    assert len({row["run_date"] for row in series}) == len(series)
    assert series[0]["run_type"] == latest_daily.run_type
    assert series[0]["failed_count"] == latest_daily.failed_count
    assert series[1]["run_type"] == latest_module.run_type
    assert series[1]["failed_count"] == latest_module.failed_count


def test_trend_uses_latest_id_when_module_rerun_completion_times_are_missing(admin_client, db, monkeypatch):
    context = create_p3_metric_context(suffix="-trend-null-completed")
    monkeypatch.setattr("metrics.views.timezone.localdate", lambda: context["now"].date())
    run_date = context["now"].date()
    create_history_row(
        context,
        run_date=run_date,
        run_type="module_rerun",
        completed_at=None,
        failed_count=3,
    )
    latest = create_history_row(
        context,
        run_date=run_date,
        run_type="module_rerun",
        completed_at=None,
        failed_count=1,
    )

    response = admin_client.get(f"/api/v1/module-snapshots/{context['module_snapshot'].id}/trend", {"days": 7})

    assert response.status_code == 200
    assert len(response.data["data"]["series"]) == 1
    assert response.data["data"]["series"][0]["failed_count"] == latest.failed_count


def test_trend_window_uses_local_date_for_snapshot_completion(admin_client, db, monkeypatch):
    context = create_p3_metric_context(suffix="-trend-local-date")
    completed_at = datetime(2026, 7, 9, 16, 30, tzinfo=datetime_timezone.utc)
    local_run_date = django_timezone.localtime(completed_at).date()
    monkeypatch.setattr("metrics.views.timezone.localdate", lambda: local_run_date)
    snapshot = context["module_snapshot"]
    snapshot.completed_at = completed_at
    snapshot.save(update_fields=["completed_at", "updated_at"])
    create_history_row(
        context,
        run_date=local_run_date,
        run_type="module_rerun",
        completed_at=completed_at,
        failed_count=1,
    )

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/trend", {"days": 7})

    assert response.status_code == 200
    assert [row["run_date"] for row in response.data["data"]["series"]] == [str(local_run_date)]


def test_trend_window_ends_today_when_snapshot_completion_is_stale(admin_client, db, monkeypatch):
    context = create_p3_metric_context(suffix="-trend-stale-snapshot")
    local_today = datetime(2026, 7, 12, 12, 0, tzinfo=datetime_timezone.utc).astimezone().date()
    stale_completed_at = datetime(2026, 7, 10, 12, 0, tzinfo=datetime_timezone.utc)
    snapshot = context["module_snapshot"]
    snapshot.completed_at = stale_completed_at
    snapshot.save(update_fields=["completed_at", "updated_at"])
    monkeypatch.setattr("metrics.views.timezone.localdate", lambda: local_today)
    for offset in (1, 0):
        run_date = local_today - timedelta(days=offset)
        create_history_row(
            context,
            run_date=run_date,
            run_type="daily_full",
            completed_at=datetime.combine(run_date, datetime.min.time(), tzinfo=datetime_timezone.utc),
            failed_count=offset,
        )

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/trend", {"days": 30})

    assert response.status_code == 200
    assert [row["run_date"] for row in response.data["data"]["series"]] == [
        str(local_today - timedelta(days=1)),
        str(local_today),
    ]


def test_trend_without_history_returns_empty_series(admin_client, db):
    context = create_p3_metric_context(suffix="-empty-trend")

    response = admin_client.get(f"/api/v1/module-snapshots/{context['module_snapshot'].id}/trend", {"days": 7})

    assert response.status_code == 200
    assert response.data["data"]["series"] == []


@pytest.mark.parametrize("days", ["14", "abc"])
def test_trend_rejects_invalid_days(admin_client, trend_context, days):
    snapshot = trend_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/trend", {"days": days})

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_trend_unknown_snapshot_returns_404(admin_client):
    response = admin_client.get("/api/v1/module-snapshots/999999/trend", {"days": 7})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "module_snapshot_not_found"


def test_trend_inactive_environment_snapshot_returns_404(admin_client, trend_context):
    snapshot = trend_context["module_snapshot"]
    environment = trend_context["environment"]
    environment.is_active = False
    environment.save(update_fields=["is_active", "updated_at"])

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/trend", {"days": 7})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "module_snapshot_not_found"


def test_trend_requires_login(api_client, trend_context):
    snapshot = trend_context["module_snapshot"]

    response = api_client.get(f"/api/v1/module-snapshots/{snapshot.id}/trend", {"days": 7})

    assert response.status_code == 401
    assert response.data["error"]["code"] == "authentication_required"
