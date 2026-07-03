from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import InvitationCode, UserAccount
from tests.conftest import TEST_PASSWORD


pytestmark = pytest.mark.api


def test_admin_can_list_users_with_role_filter_and_pagination(admin_client, member_user):
    response = admin_client.get("/api/v1/users", {"role": "member", "page": 1, "per_page": 20})

    assert response.status_code == 200
    assert response.data["meta"]["page"] == 1
    assert response.data["meta"]["per_page"] == 20
    assert response.data["data"][0]["username"] == member_user.username
    assert response.data["data"][0]["role"] == "member"
    assert "password_hash" not in response.data["data"][0]


def test_member_cannot_access_admin_management_api(member_client):
    users_response = member_client.get("/api/v1/users")
    invitation_response = member_client.post(
        "/api/v1/invitations",
        {"role": "member"},
        format="json",
    )

    assert users_response.status_code == 403
    assert users_response.data["error"]["code"] == "admin_required"
    assert invitation_response.status_code == 403
    assert invitation_response.data["error"]["code"] == "admin_required"


def test_pagination_per_page_cannot_exceed_100(admin_client):
    response = admin_client.get("/api/v1/users", {"per_page": 101})

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_admin_creates_invitation_with_default_expiration_and_list_hides_plain_code(admin_client):
    before_create = timezone.now()

    create_response = admin_client.post(
        "/api/v1/invitations",
        {"role": "member"},
        format="json",
    )

    assert create_response.status_code == 201
    data = create_response.data["data"]
    assert data["plain_code"]
    assert data["role"] == "member"
    assert data["status"] == "unused"

    expires_at = InvitationCode.objects.get(id=data["id"]).expires_at
    assert before_create + timedelta(days=6, hours=23) < expires_at
    assert expires_at < before_create + timedelta(days=7, minutes=1)

    list_response = admin_client.get("/api/v1/invitations")
    assert list_response.status_code == 200
    assert "plain_code" not in list_response.data["data"][0]


def test_admin_creates_admin_invitation_with_custom_future_expiration(admin_client):
    custom_expires_at = timezone.now() + timedelta(days=3, hours=2)

    response = admin_client.post(
        "/api/v1/invitations",
        {
            "role": "admin",
            "expires_at": custom_expires_at.isoformat(),
        },
        format="json",
    )

    assert response.status_code == 201
    data = response.data["data"]
    invitation = InvitationCode.objects.get(id=data["id"])
    assert data["role"] == "admin"
    assert data["plain_code"]
    assert invitation.role == UserAccount.Role.ADMIN
    assert abs((invitation.expires_at - custom_expires_at).total_seconds()) < 1


def test_admin_cannot_create_invitation_with_past_expiration(admin_client):
    response = admin_client.post(
        "/api/v1/invitations",
        {
            "role": "member",
            "expires_at": (timezone.now() - timedelta(minutes=1)).isoformat(),
        },
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"
    assert InvitationCode.objects.count() == 0


def test_invitation_unused_filter_excludes_expired_invitations(admin_client, admin_user):
    active_invitation, active_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
    )
    expired_invitation, expired_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    unused_response = admin_client.get("/api/v1/invitations", {"status": "unused"})
    expired_response = admin_client.get("/api/v1/invitations", {"status": "expired"})

    assert unused_response.status_code == 200
    assert [item["id"] for item in unused_response.data["data"]] == [active_invitation.id]
    assert unused_response.data["data"][0]["status"] == "unused"

    assert expired_response.status_code == 200
    assert [item["id"] for item in expired_response.data["data"]] == [expired_invitation.id]
    assert expired_response.data["data"][0]["status"] == "expired"


def test_register_with_valid_invitation_marks_code_used_without_setting_cookie(api_client, unused_invitation):
    invitation, plain_code = unused_invitation

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": plain_code,
            "username": "member01",
            "display_name": "普通成员01",
            "password": "MemberPass123",
            "confirm_password": "MemberPass123",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["data"]["username"] == "member01"
    assert response.data["data"]["role"] == "member"
    assert "authToken" not in response.cookies

    invitation.refresh_from_db()
    created_user = UserAccount.objects.get(username="member01")
    assert invitation.status == InvitationCode.Status.USED
    assert invitation.used_by == created_user
    assert invitation.used_at is not None


@pytest.mark.parametrize(
    ("password", "expected_fragment", "username"),
    [
        ("12345678", "缺少字母", "weak_member_digits"),
        ("abcdefgh", "缺少数字", "weak_member_letters"),
        ("abc1234", "长度不足 8 位", "weak_member_short"),
    ],
)
def test_register_weak_password_returns_specific_requirement(api_client, admin_user, password, expected_fragment, username):
    invitation, plain_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
    )

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": plain_code,
            "username": username,
            "display_name": "弱密码成员",
            "password": password,
            "confirm_password": password,
        },
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "weak_password"
    assert "密码需 8-64 位，至少包含字母和数字" in response.data["error"]["message"]
    assert expected_fragment in response.data["error"]["message"]
    assert not UserAccount.objects.filter(username=username).exists()

    invitation.refresh_from_db()
    assert invitation.status == InvitationCode.Status.UNUSED


def test_register_used_invitation_returns_explicit_used_message(api_client, admin_user):
    used_invitation, used_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
    )
    used_invitation.status = InvitationCode.Status.USED
    used_invitation.used_at = timezone.now()
    used_invitation.used_by = admin_user
    used_invitation.save(update_fields=["status", "used_at", "used_by", "updated_at"])

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": used_code,
            "username": "used_code_member",
            "display_name": "已使用邀请码成员",
            "password": "MemberPass123",
            "confirm_password": "MemberPass123",
        },
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "invalid_invitation_code"
    assert response.data["error"]["message"] == "邀请码已经被使用。"
    assert not UserAccount.objects.filter(username="used_code_member").exists()


def test_register_rejects_chinese_username_with_specific_message(api_client, unused_invitation):
    invitation, plain_code = unused_invitation

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": plain_code,
            "username": "中文账号",
            "display_name": "中文账号",
            "password": "MemberPass123",
            "confirm_password": "MemberPass123",
        },
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "invalid_username"
    assert response.data["error"]["message"] == "账号只能包含字母、数字、下划线、短横线和点。"
    invitation.refresh_from_db()
    assert invitation.status == InvitationCode.Status.UNUSED


def test_register_password_mismatch_has_priority_over_weak_password(api_client, unused_invitation):
    invitation, plain_code = unused_invitation

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": plain_code,
            "username": "mismatch_member",
            "display_name": "密码不一致成员",
            "password": "abc1234",
            "confirm_password": "abc12345",
        },
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "password_mismatch"
    assert response.data["error"]["message"] == "两次输入的密码不一致。"
    invitation.refresh_from_db()
    assert invitation.status == InvitationCode.Status.UNUSED


def test_register_equal_password_over_64_chars_returns_weak_password(api_client, unused_invitation):
    invitation, plain_code = unused_invitation
    overlong_password = f"MemberPass123{'A' * 52}"
    assert len(overlong_password) == 65

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": plain_code,
            "username": "overlong_password_member",
            "display_name": "超长密码成员",
            "password": overlong_password,
            "confirm_password": overlong_password,
        },
        format="json",
    )

    assert response.status_code == 422
    assert response.data["error"]["code"] == "weak_password"
    assert "长度超过 64 位" in response.data["error"]["message"]
    invitation.refresh_from_db()
    assert invitation.status == InvitationCode.Status.UNUSED


@pytest.mark.parametrize(
    ("payload_override", "omitted_fields", "expected_detail_field"),
    [
        ({}, ["password"], "password"),
        ({}, ["confirm_password"], "confirm_password"),
        ({"password": None}, [], "password"),
        ({"confirm_password": None}, [], "confirm_password"),
        ({"password": ""}, [], "password"),
        ({"confirm_password": ""}, [], "confirm_password"),
    ],
)
def test_register_required_password_fields_return_validation_error(
    api_client,
    unused_invitation,
    payload_override,
    omitted_fields,
    expected_detail_field,
):
    invitation, plain_code = unused_invitation
    payload = {
        "invitation_code": plain_code,
        "username": "required_password_member",
        "display_name": "必填字段成员",
        "password": "MemberPass123",
        "confirm_password": "MemberPass123",
    }
    payload.update(payload_override)
    for field_name in omitted_fields:
        payload.pop(field_name)

    response = api_client.post("/api/v1/auth/register", payload, format="json")

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"
    assert expected_detail_field in response.data["error"]["details"][0]
    invitation.refresh_from_db()
    assert invitation.status == InvitationCode.Status.UNUSED


def test_register_rejects_used_expired_or_revoked_invitation(api_client, admin_user):
    used_invitation, used_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
    )
    used_invitation.status = InvitationCode.Status.USED
    used_invitation.used_at = timezone.now()
    used_invitation.used_by = admin_user
    used_invitation.save(update_fields=["status", "used_at", "used_by", "updated_at"])

    expired_invitation, expired_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    revoked_invitation, revoked_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
    )
    revoked_invitation.status = InvitationCode.Status.REVOKED
    revoked_invitation.revoked_at = timezone.now()
    revoked_invitation.revoked_by = admin_user
    revoked_invitation.save(update_fields=["status", "revoked_at", "revoked_by", "updated_at"])

    for index, code in enumerate([used_code, expired_code, revoked_code], start=1):
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "invitation_code": code,
                "username": f"blocked_member_{index}",
                "display_name": "受阻成员",
                "password": "MemberPass123",
                "confirm_password": "MemberPass123",
            },
            format="json",
        )
        assert response.status_code == 422
        assert response.data["error"]["code"] == "invalid_invitation_code"


def test_username_conflict_does_not_consume_invitation(api_client, member_user, unused_invitation):
    invitation, plain_code = unused_invitation

    response = api_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": plain_code,
            "username": member_user.username,
            "display_name": "重复账号",
            "password": "MemberPass123",
            "confirm_password": "MemberPass123",
        },
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "username_taken"
    invitation.refresh_from_db()
    assert invitation.status == InvitationCode.Status.UNUSED


def test_admin_revoke_unused_invitation_and_used_invitation_is_conflict(admin_client, unused_invitation, admin_user):
    invitation, plain_code = unused_invitation

    revoke_response = admin_client.post(f"/api/v1/invitations/{invitation.id}/revoke")
    assert revoke_response.status_code == 200
    assert revoke_response.data["data"]["status"] == "revoked"

    register_response = admin_client.post(
        "/api/v1/auth/register",
        {
            "invitation_code": plain_code,
            "username": "revoked_member",
            "display_name": "作废成员",
            "password": "MemberPass123",
            "confirm_password": "MemberPass123",
        },
        format="json",
    )
    assert register_response.status_code == 422

    used_invitation, used_code = InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
    )
    created_user = UserAccount.objects.create_user(
        username="already_registered",
        display_name="已注册",
        password=TEST_PASSWORD,
        role=UserAccount.Role.MEMBER,
    )
    used_invitation.status = InvitationCode.Status.USED
    used_invitation.used_by = created_user
    used_invitation.used_at = timezone.now()
    used_invitation.save(update_fields=["status", "used_by", "used_at", "updated_at"])

    conflict_response = admin_client.post(f"/api/v1/invitations/{used_invitation.id}/revoke")
    assert conflict_response.status_code == 409
    assert conflict_response.data["error"]["code"] == "invitation_already_used"
