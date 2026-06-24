"""账户认证与角色权限测试。
本文件覆盖登录 token、当前用户、登出、角色保存、超级管理员默认角色和权限入口。
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.permissions import IsPlatformAdmin, PlatformAccessPermission


pytestmark = pytest.mark.django_db


def create_user(username: str, role: str, password: str = "local-test-pass"):
    """创建测试用户。
    Args:
        username: 测试用户名。
        role: 平台角色。
        password: 测试密码。
    Returns:
        User: 已创建的测试用户。
    """
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        password=password,
        role=role,
    )


def test_user_can_login_receive_token_read_current_user_and_logout():
    """验证用户可完成登录、读取当前用户和登出完整流程。"""
    user_model = get_user_model()
    user = create_user("stage5-admin", user_model.Role.ADMIN)
    client = APIClient()

    response = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "local-test-pass"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["token"]
    assert response.data["user"] == {
        "id": user.id,
        "username": "stage5-admin",
        "role": user_model.Role.ADMIN,
    }

    token = response.data["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    me_response = client.get("/api/auth/me/")

    assert me_response.status_code == 200
    assert me_response.data["username"] == "stage5-admin"
    assert me_response.data["role"] == user_model.Role.ADMIN

    logout_response = client.post("/api/auth/logout/")

    assert logout_response.status_code == 204
    assert not Token.objects.filter(key=token).exists()


def test_admin_and_member_roles_can_be_saved():
    """验证 admin/member 两种平台角色可以被正确保存。"""
    user_model = get_user_model()

    admin = create_user("role-admin", user_model.Role.ADMIN)
    member = create_user("role-member", user_model.Role.MEMBER)

    assert admin.role == user_model.Role.ADMIN
    assert member.role == user_model.Role.MEMBER
    assert set(user_model.Role.values) == {"admin", "member"}


def test_create_superuser_defaults_to_admin_role():
    """验证命令行创建超级管理员时默认写入 admin 角色。"""
    user_model = get_user_model()

    admin = user_model.objects.create_superuser(
        username="created-superuser",
        password="local-test-pass",
    )

    assert admin.role == user_model.Role.ADMIN
    assert admin.is_staff
    assert admin.is_superuser


@pytest.mark.parametrize("role", ["admin", "member"])
def test_admin_and_member_can_access_platform_api_with_same_permissions(role):
    """验证第一版 admin 和 member 都能访问平台基础 API。"""
    user = create_user(f"platform-{role}", role)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/auth/me/")

    assert response.status_code == 200
    assert response.data["role"] == role


def test_permissions_keep_admin_only_entrypoint():
    """验证权限模块保留管理员专属判断入口。"""
    user_model = get_user_model()
    admin = create_user("permission-admin", user_model.Role.ADMIN)
    member = create_user("permission-member", user_model.Role.MEMBER)
    factory = APIRequestFactory()

    admin_request = factory.get("/api/auth/me/")
    admin_request.user = admin
    member_request = factory.get("/api/auth/me/")
    member_request.user = member

    assert PlatformAccessPermission().has_permission(admin_request, None)
    assert PlatformAccessPermission().has_permission(member_request, None)
    assert IsPlatformAdmin().has_permission(admin_request, None)
    assert not IsPlatformAdmin().has_permission(member_request, None)
