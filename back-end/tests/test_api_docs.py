"""后端 API 文档入口测试。
本文件验证 OpenAPI schema、Swagger UI 和 Redoc UI 可以公开访问，便于前后端联调。
"""

import pytest


@pytest.mark.django_db
def test_openapi_schema_is_public_and_documents_auth_endpoints(client):
    """验证 OpenAPI schema 可访问且包含认证接口。"""
    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")
    assert "/api/auth/login/" in response.content.decode()
    assert "/api/auth/me/" in response.content.decode()


@pytest.mark.django_db
def test_swagger_ui_is_public(client):
    """验证 Swagger UI 页面可访问。"""
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()


@pytest.mark.django_db
def test_redoc_ui_is_public(client):
    """验证 Redoc UI 页面可访问。"""
    response = client.get("/api/redoc/")

    assert response.status_code == 200
    assert b"redoc" in response.content.lower()
