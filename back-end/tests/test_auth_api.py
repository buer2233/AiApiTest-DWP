import pytest
from django.utils import timezone

from accounts.models import UserAccount
from tests.conftest import TEST_PASSWORD


pytestmark = pytest.mark.api


def test_login_sets_http_only_auth_cookie_and_me_returns_permissions(api_client, admin_user):
    response = api_client.post(
        "/api/v1/auth/login",
        {"username": admin_user.username, "password": TEST_PASSWORD},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"]["username"] == admin_user.username
    assert response.data["data"]["role"] == "admin"
    assert "users:read" in response.data["data"]["permissions"]

    cookie = response.cookies["authToken"]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/"
    assert int(cookie["max-age"]) > 0

    me_response = api_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.data["data"]["username"] == admin_user.username

    admin_user.refresh_from_db()
    assert admin_user.last_login_at is not None
    assert admin_user.last_login_at <= timezone.now()


def test_login_rejects_invalid_credentials_without_cookie(api_client, admin_user):
    response = api_client.post(
        "/api/v1/auth/login",
        {"username": admin_user.username, "password": "WrongPass123"},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"
    assert "authToken" not in response.cookies


def test_protected_api_requires_auth_cookie(api_client):
    for path in ["/api/v1/auth/me", "/api/v1/users", "/api/v1/invitations"]:
        response = api_client.get(path)
        assert response.status_code == 401
        assert response.data["error"]["code"] == "authentication_required"


def test_invalid_cookie_returns_401(api_client):
    api_client.cookies["authToken"] = "invalid-test-token"

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_or_expired_token"
    assert "secret" not in str(response.data).lower()


def test_logout_clears_cookie_and_blocks_follow_up_request(admin_client):
    response = admin_client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert response.cookies["authToken"].value == ""
    assert int(response.cookies["authToken"]["max-age"]) == 0

    follow_up = admin_client.get("/api/v1/auth/me")
    assert follow_up.status_code == 401


def test_inactive_user_cannot_login(api_client, db):
    inactive_user = UserAccount.objects.create_user(
        username="inactive_user",
        display_name="停用用户",
        password=TEST_PASSWORD,
        role=UserAccount.Role.MEMBER,
        is_active=False,
    )

    response = api_client.post(
        "/api/v1/auth/login",
        {"username": inactive_user.username, "password": TEST_PASSWORD},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "user_inactive"
