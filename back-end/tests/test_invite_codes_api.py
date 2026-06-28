import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import RegistrationInviteCode


@pytest.mark.django_db
def test_admin_can_create_invite_code(auth_client, admin_user):
    client = auth_client(admin_user)

    response = client.post(
        "/api/v1/invite-codes",
        {"code": "INVITE-ADMIN", "max_uses": 5, "expires_at": None},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["data"]["code"] == "INVITE-ADMIN"
    assert response.data["data"]["status"] == "active"


@pytest.mark.django_db
def test_member_cannot_create_invite_code(auth_client, member_user):
    client = auth_client(member_user)

    response = client.post(
        "/api/v1/invite-codes",
        {"code": "INVITE-MEMBER", "max_uses": 1},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_list_and_filter_invite_codes(auth_client, admin_user):
    RegistrationInviteCode.objects.create(code="ALPHA-001", max_uses=1, created_by=admin_user)
    RegistrationInviteCode.objects.create(code="BETA-001", max_uses=1, status="disabled", created_by=admin_user)
    client = auth_client(admin_user)

    response = client.get("/api/v1/invite-codes", {"keyword": "ALPHA", "status": "active"})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    assert response.data["data"][0]["code"] == "ALPHA-001"


@pytest.mark.django_db
def test_admin_can_disable_active_invite_code(auth_client, admin_user):
    invite = RegistrationInviteCode.objects.create(code="DISABLE-001", max_uses=1, created_by=admin_user)
    client = auth_client(admin_user)

    response = client.post(f"/api/v1/invite-codes/{invite.id}/disable")

    assert response.status_code == 200
    invite.refresh_from_db()
    assert invite.status == "disabled"


@pytest.mark.django_db
def test_invite_code_validation_rejects_duplicate_invalid_max_uses_and_past_expiry(auth_client, admin_user):
    RegistrationInviteCode.objects.create(code="DUPLICATE", max_uses=1, created_by=admin_user)
    client = auth_client(admin_user)

    duplicate = client.post("/api/v1/invite-codes", {"code": "DUPLICATE", "max_uses": 1}, format="json")
    invalid_uses = client.post("/api/v1/invite-codes", {"code": "BAD-USES", "max_uses": 0}, format="json")
    past_expiry = client.post(
        "/api/v1/invite-codes",
        {
            "code": "BAD-TIME",
            "max_uses": 1,
            "expires_at": (timezone.now() - timedelta(days=1)).isoformat(),
        },
        format="json",
    )

    assert duplicate.status_code == 409
    assert invalid_uses.status_code == 400
    assert past_expiry.status_code == 400


@pytest.mark.django_db
def test_invite_code_model_constraints_reject_invalid_usage_counts(admin_user):
    with pytest.raises(IntegrityError), transaction.atomic():
        RegistrationInviteCode.objects.create(
            code="BAD-CONSTRAINT",
            max_uses=1,
            used_count=2,
            created_by=admin_user,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        RegistrationInviteCode.objects.create(
            code="BAD-MAX-USES",
            max_uses=0,
            used_count=0,
            created_by=admin_user,
        )
