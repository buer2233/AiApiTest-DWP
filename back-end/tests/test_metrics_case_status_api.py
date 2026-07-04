from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.p3_metrics_helpers import create_case_result, create_p3_metric_context, metric_model


pytestmark = pytest.mark.api


@pytest.fixture
def status_context(db) -> dict:
    context = create_p3_metric_context(suffix="-status")
    context["failed_case"] = create_case_result(context, display_status="failed", node_suffix="failed_case")
    context["passed_case"] = create_case_result(context, display_status="passed", node_suffix="passed_case")
    context["skipped_case"] = create_case_result(context, display_status="skipped", node_suffix="skipped_case")
    context["archived_case"] = create_case_result(
        context,
        display_status="archived",
        node_suffix="archived_case",
        is_current=False,
    )
    return context


def test_admin_updates_failed_case_to_skipped_refreshes_summaries_and_audit(admin_client, admin_user, status_context):
    case = status_context["failed_case"]

    response = admin_client.patch(
        f"/api/v1/case-results/{case.id}/status",
        {"display_status": "skipped", "reason": "误报，人工跳过"},
        format="json",
    )

    assert response.status_code == 200
    case.refresh_from_db()
    status_context["module_snapshot"].refresh_from_db()
    status_context["environment_snapshot"].refresh_from_db()
    CaseStatusAudit = metric_model("CaseStatusAudit")
    audit = CaseStatusAudit.objects.get(case_result=case)
    assert case.display_status == "skipped"
    assert case.confirmation_result == "误报，人工跳过"
    assert status_context["module_snapshot"].failed_count == 3
    assert status_context["module_snapshot"].skipped_count == 4
    assert str(status_context["module_snapshot"].pass_rate) == "0.970000"
    assert status_context["environment_snapshot"].failed_count == 3
    assert str(status_context["environment_snapshot"].pass_rate) == "0.970000"
    assert audit.changed_by == admin_user
    assert audit.from_status == "failed"
    assert audit.to_status == "skipped"
    assert audit.reason == "误报，人工跳过"
    assert response.data["data"]["audit_id"] == audit.id


@pytest.mark.parametrize(
    ("case_key", "target_status", "expected_failed", "expected_passed", "expected_skipped"),
    [
        ("failed_case", "passed", 3, 94, 3),
        ("passed_case", "failed", 5, 92, 3),
        ("passed_case", "skipped", 4, 92, 4),
        ("skipped_case", "failed", 5, 93, 2),
        ("skipped_case", "passed", 4, 94, 2),
    ],
)
def test_admin_status_transitions_refresh_all_summary_counters(
    admin_client,
    status_context,
    case_key,
    target_status,
    expected_failed,
    expected_passed,
    expected_skipped,
):
    case = status_context[case_key]

    response = admin_client.patch(
        f"/api/v1/case-results/{case.id}/status",
        {"display_status": target_status, "reason": f"切换为 {target_status}"},
        format="json",
    )

    assert response.status_code == 200
    status_context["module_snapshot"].refresh_from_db()
    status_context["environment_snapshot"].refresh_from_db()
    assert status_context["module_snapshot"].failed_count == expected_failed
    assert status_context["module_snapshot"].passed_count == expected_passed
    assert status_context["module_snapshot"].skipped_count == expected_skipped
    assert status_context["environment_snapshot"].failed_count == expected_failed
    assert str(status_context["module_snapshot"].pass_rate) == f"{(100 - expected_failed) / 100:.6f}"


def test_status_update_rolls_back_case_and_summaries_when_audit_write_fails(admin_client, status_context):
    case = status_context["failed_case"]

    with patch("metrics.views.CaseStatusAudit.objects.create", side_effect=RuntimeError("audit down")):
        with pytest.raises(RuntimeError, match="audit down"):
            admin_client.patch(
                f"/api/v1/case-results/{case.id}/status",
                {"display_status": "passed", "reason": "模拟审计失败"},
                format="json",
            )

    case.refresh_from_db()
    status_context["module_snapshot"].refresh_from_db()
    status_context["environment_snapshot"].refresh_from_db()
    assert case.display_status == "failed"
    assert status_context["module_snapshot"].failed_count == 4
    assert status_context["module_snapshot"].passed_count == 93
    assert status_context["module_snapshot"].skipped_count == 3
    assert status_context["environment_snapshot"].failed_count == 4
    assert metric_model("CaseStatusAudit").objects.count() == 0


def test_member_cannot_update_case_status(member_client, status_context):
    case = status_context["failed_case"]

    response = member_client.patch(
        f"/api/v1/case-results/{case.id}/status",
        {"display_status": "skipped", "reason": "普通成员尝试修改"},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "admin_required"
    case.refresh_from_db()
    assert case.display_status == "failed"
    assert metric_model("CaseStatusAudit").objects.count() == 0


def test_same_status_returns_409_without_audit(admin_client, status_context):
    case = status_context["failed_case"]

    response = admin_client.patch(
        f"/api/v1/case-results/{case.id}/status",
        {"display_status": "failed", "reason": "重复确认"},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "case_status_unchanged"
    assert metric_model("CaseStatusAudit").objects.count() == 0


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ({"display_status": "deleted", "reason": "非法状态"}, "invalid_case_status"),
        ({"display_status": "skipped", "reason": ""}, "validation_error"),
        ({"display_status": "skipped", "reason": "x" * 513}, "validation_error"),
    ],
)
def test_status_update_rejects_invalid_payload(admin_client, status_context, payload, expected_code):
    case = status_context["failed_case"]

    response = admin_client.patch(f"/api/v1/case-results/{case.id}/status", payload, format="json")

    assert response.status_code == 422
    assert response.data["error"]["code"] == expected_code
    assert metric_model("CaseStatusAudit").objects.count() == 0


def test_archived_case_result_cannot_be_updated(admin_client, status_context):
    case = status_context["archived_case"]

    response = admin_client.patch(
        f"/api/v1/case-results/{case.id}/status",
        {"display_status": "failed", "reason": "归档结果不允许修改"},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "archived_case_result"
    assert metric_model("CaseStatusAudit").objects.count() == 0


def test_status_update_unknown_case_returns_404(admin_client):
    response = admin_client.patch(
        "/api/v1/case-results/999999/status",
        {"display_status": "skipped", "reason": "不存在"},
        format="json",
    )

    assert response.status_code == 404
    assert response.data["error"]["code"] == "case_result_not_found"
