import pytest
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.accounts.models import RegistrationInviteCode


@pytest.mark.django_db
def test_register_with_valid_invite_creates_active_member_and_consumes_invite(api_client, admin_user):
    invite = RegistrationInviteCode.objects.create(code="INVITE-001", max_uses=2, created_by=admin_user)

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "username": "newmember",
            "email": "newmember@example.com",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
            "invite_code": invite.code,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["data"]["username"] == "newmember"
    assert response.data["data"]["role"] == "member"
    assert response.data["data"]["status"] == "active"
    invite.refresh_from_db()
    assert invite.used_count == 1


@pytest.mark.django_db
def test_register_rejects_duplicate_username_or_email(api_client, admin_user, member_user):
    invite = RegistrationInviteCode.objects.create(code="INVITE-002", max_uses=3, created_by=admin_user)

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "username": member_user.username,
            "email": "other@example.com",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
            "invite_code": invite.code,
        },
        format="json",
    )

    assert response.status_code == 409
    invite.refresh_from_db()
    assert invite.used_count == 0


@pytest.mark.django_db
def test_register_handles_database_unique_conflict_as_duplicate_user(api_client, admin_user, monkeypatch):
    invite = RegistrationInviteCode.objects.create(code="INVITE-CONFLICT", max_uses=1, created_by=admin_user)

    def raise_integrity_error(*args, **kwargs):
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr("apps.accounts.views.User.objects.create_user", raise_integrity_error)

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "username": "raceuser",
            "email": "raceuser@example.com",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
            "invite_code": invite.code,
        },
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "duplicate_user"
    invite.refresh_from_db()
    assert invite.used_count == 0


@pytest.mark.django_db
def test_register_rejects_invalid_password_and_invalid_invite(api_client):
    response = api_client.post(
        "/api/v1/auth/register",
        {
            "username": "newmember",
            "email": "newmember@example.com",
            "password": "short",
            "password_confirm": "different",
            "invite_code": "MISSING",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_register_rejects_exhausted_invite(api_client, admin_user):
    invite = RegistrationInviteCode.objects.create(
        code="INVITE-003",
        max_uses=1,
        used_count=1,
        status="exhausted",
        created_by=admin_user,
    )

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "username": "newmember",
            "email": "newmember@example.com",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
            "invite_code": invite.code,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invite_code_unavailable"


@pytest.mark.django_db
def test_register_rejects_expired_invite_and_persists_expired_status(api_client, admin_user):
    invite = RegistrationInviteCode.objects.create(
        code="INVITE-EXPIRED",
        max_uses=1,
        expires_at=timezone.now() - timezone.timedelta(days=1),
        created_by=admin_user,
    )

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "username": "expiredmember",
            "email": "expiredmember@example.com",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
            "invite_code": invite.code,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invite_code_unavailable"
    invite.refresh_from_db()
    assert invite.status == RegistrationInviteCode.Status.EXPIRED


@pytest.mark.django_db
def test_login_returns_token_and_me_returns_current_user(api_client, member_user):
    response = api_client.post(
        "/api/v1/auth/login",
        {"account": member_user.email, "password": "StrongPass123"},
        format="json",
    )

    assert response.status_code == 200
    token = response.data["data"]["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    me_response = api_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.data["data"]["username"] == member_user.username


@pytest.mark.django_db
def test_login_rejects_invalid_credentials_without_leaking_account(api_client, member_user):
    response = api_client.post(
        "/api/v1/auth/login",
        {"account": member_user.email, "password": "WrongPass123"},
        format="json",
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"


@pytest.mark.django_db
def test_logout_deletes_current_token(api_client, member_user):
    token = Token.objects.create(user=member_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = api_client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert not Token.objects.filter(key=token.key).exists()


@pytest.mark.django_db
def test_protected_api_requires_authentication(api_client):
    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.django_db
def test_invalid_token_uses_unauthorized_error_code(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Token invalid-token")

    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "unauthorized"
