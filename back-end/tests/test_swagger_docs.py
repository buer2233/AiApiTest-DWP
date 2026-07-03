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

    register_post = paths["/api/v1/auth/register"]["post"]
    assert register_post["responses"]["422"]["description"] == "邀请码不可用、账号格式非法、密码不一致或密码不满足要求"

    register_schema_ref = register_post["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    register_schema_name = register_schema_ref.rsplit("/", 1)[-1]
    register_schema = response.data["components"]["schemas"][register_schema_name]
    # 密码复杂度由后端对象级校验统一处理，避免客户端 schema 先拦截而绕过错误优先级契约。
    for field_name in ["password", "confirm_password"]:
        password_schema = register_schema["properties"][field_name]
        assert "minLength" not in password_schema
        assert "maxLength" not in password_schema


def test_swagger_ui_is_public_but_business_api_still_requires_cookie(api_client):
    docs_response = api_client.get("/api/docs/")
    protected_response = api_client.get("/api/v1/auth/me")

    assert docs_response.status_code == 200
    assert b"SwaggerUIBundle" in docs_response.content
    assert b"/api/schema/" in docs_response.content
    assert b"#swagger-ui" in docs_response.content
    assert protected_response.status_code == 401
    assert protected_response.data["error"]["code"] == "authentication_required"
