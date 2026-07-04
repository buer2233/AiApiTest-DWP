from __future__ import annotations

import pytest

from tests.p3_metrics_helpers import create_p3_metric_context, create_trend_row


pytestmark = pytest.mark.api


@pytest.fixture
def trend_context(db) -> dict:
    context = create_p3_metric_context(suffix="-trend")
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
