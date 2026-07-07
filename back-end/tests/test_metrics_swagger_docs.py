import pytest


pytestmark = pytest.mark.api


def test_openapi_schema_includes_metrics_contract(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    paths = response.data["paths"]
    for path in [
        "/api/v1/test-environments",
        "/api/v1/test-environments/{environment_id}/summary",
        "/api/v1/module-snapshots",
        "/api/v1/module-snapshots/filter-options",
        "/api/v1/module-snapshots/{snapshot_id}/cases",
        "/api/v1/module-snapshots/{snapshot_id}/jenkins-tasks",
        "/api/v1/case-results/{case_result_id}/status",
        "/api/v1/module-snapshots/{snapshot_id}/trend",
    ]:
        assert path in paths

    module_get = paths["/api/v1/module-snapshots"]["get"]
    parameter_names = {parameter["name"] for parameter in module_get["parameters"]}
    assert {
        "environment_id",
        "module_test",
        "module_name",
        "module_dev",
        "package_name",
        "page",
        "per_page",
        "sort",
    }.issubset(parameter_names)
    assert "pass_rate_lte" not in parameter_names
    assert "未登录或 Cookie 无效" in module_get["responses"]["401"]["description"]
    assert "筛选、排序或分页参数非法" in module_get["responses"]["422"]["description"]

    filter_options_get = paths["/api/v1/module-snapshots/filter-options"]["get"]
    filter_option_parameter_names = {parameter["name"] for parameter in filter_options_get["parameters"]}
    assert {"environment_id"}.issubset(filter_option_parameter_names)
    assert "authentication_required" in filter_options_get["responses"]["401"]["description"]
    assert "validation_error" in filter_options_get["responses"]["422"]["description"]

    cases_get = paths["/api/v1/module-snapshots/{snapshot_id}/cases"]["get"]
    case_parameter_names = {parameter["name"] for parameter in cases_get["parameters"]}
    assert {"snapshot_id", "status", "case_name", "node_id", "error_type", "page", "per_page"}.issubset(
        case_parameter_names
    )
    assert "module_snapshot_not_found" in cases_get["responses"]["404"]["description"]
    assert "validation_error" in cases_get["responses"]["422"]["description"]

    status_patch = paths["/api/v1/case-results/{case_result_id}/status"]["patch"]
    assert "requestBody" in status_patch
    assert "admin_required" in status_patch["responses"]["403"]["description"]
    assert "case_result_not_found" in status_patch["responses"]["404"]["description"]
    assert "case_status_unchanged" in status_patch["responses"]["409"]["description"]
    assert "archived_case_result" in status_patch["responses"]["409"]["description"]
    assert "invalid_case_status" in status_patch["responses"]["422"]["description"]
    assert "validation_error" in status_patch["responses"]["422"]["description"]

    jenkins_tasks_get = paths["/api/v1/module-snapshots/{snapshot_id}/jenkins-tasks"]["get"]
    jenkins_task_parameter_names = {parameter["name"] for parameter in jenkins_tasks_get["parameters"]}
    assert {"snapshot_id", "date", "status", "task_type", "page", "per_page"}.issubset(jenkins_task_parameter_names)
    assert "module_snapshot_not_found" in jenkins_tasks_get["responses"]["404"]["description"]
    assert "validation_error" in jenkins_tasks_get["responses"]["422"]["description"]

    trend_get = paths["/api/v1/module-snapshots/{snapshot_id}/trend"]["get"]
    trend_parameter_names = {parameter["name"] for parameter in trend_get["parameters"]}
    assert {"snapshot_id", "days"}.issubset(trend_parameter_names)
    assert "module_snapshot_not_found" in trend_get["responses"]["404"]["description"]
    assert "validation_error" in trend_get["responses"]["422"]["description"]
