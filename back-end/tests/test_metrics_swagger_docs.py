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
    ]:
        assert path in paths

    module_get = paths["/api/v1/module-snapshots"]["get"]
    parameter_names = {parameter["name"] for parameter in module_get["parameters"]}
    assert {
        "environment_id",
        "module_test",
        "module_name",
        "package_name",
        "pass_rate_lte",
        "page",
        "per_page",
        "sort",
    }.issubset(parameter_names)
    assert "未登录或 Cookie 无效" in module_get["responses"]["401"]["description"]
    assert "筛选、排序或分页参数非法" in module_get["responses"]["422"]["description"]
