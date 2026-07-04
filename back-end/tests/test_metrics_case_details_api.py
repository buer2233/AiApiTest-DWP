from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from tests.p3_metrics_helpers import create_case_result, create_p3_metric_context
from tests.p3_metrics_helpers import metric_model


pytestmark = pytest.mark.api


@pytest.fixture
def p3_context(db) -> dict:
    context = create_p3_metric_context()
    create_case_result(context, display_status="failed", node_suffix="search_species")
    create_case_result(context, display_status="passed", node_suffix="get_species")
    create_case_result(context, display_status="skipped", node_suffix="legacy_species")
    return context


def test_case_details_default_failed_filter_returns_admin_detail(admin_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 200
    assert response.data["meta"] == {"total": 1, "page": 1, "per_page": 20, "total_pages": 1}
    row = response.data["data"][0]
    assert row["case_name"] == "test_search_species"
    assert row["display_status"] == "failed"
    assert row["error_type"] == "AssertionError"
    assert row["error_message_summary"] == "AssertionError: expected 200, got 500"
    assert row["error_message_detail"]
    assert "demo-token" not in row["error_message_detail"]
    assert "password=demo" not in row["error_message_detail"]
    assert "sessionid=secret" not in row["error_message_detail"]
    assert "10.0.0.5" not in row["error_message_detail"]
    assert row["actions"] == {"can_update_status": True, "can_retry": False}


@pytest.mark.parametrize(
    ("status_value", "expected_case"),
    [
        ("passed", "test_get_species"),
        ("skipped", "test_legacy_species"),
    ],
)
def test_case_details_filter_by_passed_and_skipped(admin_client, p3_context, status_value, expected_case):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases", {"status": status_value})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    assert response.data["data"][0]["case_name"] == expected_case
    assert response.data["data"][0]["display_status"] == status_value


def test_case_details_member_only_receives_summary(member_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = member_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 200
    row = response.data["data"][0]
    assert row["error_message_summary"]
    assert row["error_message_detail"] is None
    assert row["actions"] == {"can_update_status": False, "can_retry": False}


def test_case_details_supports_query_filters(admin_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(
        f"/api/v1/module-snapshots/{snapshot.id}/cases",
        {"status": "failed", "case_name": "search", "node_id": "species.py", "error_type": "AssertionError"},
    )

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    assert response.data["data"][0]["case_name"] == "test_search_species"


@pytest.mark.parametrize(
    "params",
    [
        {"status": "archived"},
        {"page": "0"},
        {"per_page": "101"},
        {"case_name": "x" * 257},
        {"node_id": "x" * 1025},
        {"error_type": "x" * 129},
    ],
)
def test_case_details_rejects_invalid_query_params(admin_client, p3_context, params):
    snapshot = p3_context["module_snapshot"]

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases", params)

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_case_details_unknown_snapshot_returns_404(admin_client):
    response = admin_client.get("/api/v1/module-snapshots/999999/cases")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "module_snapshot_not_found"


def test_case_details_inactive_environment_snapshot_returns_404(admin_client, p3_context):
    snapshot = p3_context["module_snapshot"]
    environment = p3_context["environment"]
    environment.is_active = False
    environment.save(update_fields=["is_active", "updated_at"])

    response = admin_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "module_snapshot_not_found"


def test_case_details_requires_login(api_client, p3_context):
    snapshot = p3_context["module_snapshot"]

    response = api_client.get(f"/api/v1/module-snapshots/{snapshot.id}/cases")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "authentication_required"


def test_current_case_result_is_unique_by_environment_module_and_node_id(p3_context):
    existing = create_case_result(p3_context, display_status="failed", node_suffix="unique_case")
    assert existing.current_node_key == existing.node_id

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_case_result(p3_context, display_status="failed", node_suffix="unique_case")

    archived_copy = create_case_result(
        p3_context,
        display_status="failed",
        node_suffix="unique_case",
        is_current=False,
    )
    assert archived_copy.node_id == existing.node_id
    assert archived_copy.current_node_key is None


def test_current_case_result_unique_constraint_is_mysql_compatible():
    TestCaseResult = metric_model("TestCaseResult")

    constraints = {constraint.name: constraint for constraint in TestCaseResult._meta.constraints}
    current_unique = constraints["uniq_current_case_result_env_module_node"]
    assert tuple(current_unique.fields) == ("environment", "module", "current_node_key")
    assert current_unique.condition is None
