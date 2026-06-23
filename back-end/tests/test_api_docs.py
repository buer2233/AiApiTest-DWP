import pytest


@pytest.mark.django_db
def test_openapi_schema_is_public_and_documents_auth_endpoints(client):
    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")
    assert "/api/auth/login/" in response.content.decode()
    assert "/api/auth/me/" in response.content.decode()


@pytest.mark.django_db
def test_swagger_ui_is_public(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()


@pytest.mark.django_db
def test_redoc_ui_is_public(client):
    response = client.get("/api/redoc/")

    assert response.status_code == 200
    assert b"redoc" in response.content.lower()
