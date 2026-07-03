import pytest


pytestmark = pytest.mark.api


def test_openapi_schema_includes_current_backend_contract(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    assert response.data["openapi"].startswith("3.")

    paths = response.data["paths"]
    for path in [
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/auth/register",
        "/api/v1/users",
        "/api/v1/invitations",
        "/api/v1/invitations/{invitation_id}/revoke",
    ]:
        assert path in paths


def test_swagger_ui_is_public_but_business_api_still_requires_cookie(api_client):
    docs_response = api_client.get("/api/docs/")
    protected_response = api_client.get("/api/v1/auth/me")

    assert docs_response.status_code == 200
    assert b"SwaggerUIBundle" in docs_response.content
    assert b"/api/schema/" in docs_response.content
    assert b"#swagger-ui" in docs_response.content
    assert protected_response.status_code == 401
    assert protected_response.data["error"]["code"] == "authentication_required"
