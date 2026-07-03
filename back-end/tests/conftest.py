import pytest
from rest_framework.test import APIClient

from accounts.models import InvitationCode, UserAccount


TEST_PASSWORD = "TestPass123"


@pytest.fixture
def api_client() -> APIClient:
    """提供 DRF 测试客户端，保留 Cookie 以验证浏览器态流程。"""
    return APIClient()


@pytest.fixture
def admin_user(db) -> UserAccount:
    """创建管理人员测试账号。"""
    return UserAccount.objects.create_user(
        username="admin_user",
        display_name="平台管理员",
        password=TEST_PASSWORD,
        role=UserAccount.Role.ADMIN,
    )


@pytest.fixture
def member_user(db) -> UserAccount:
    """创建普通成员测试账号。"""
    return UserAccount.objects.create_user(
        username="member_user",
        display_name="普通成员",
        password=TEST_PASSWORD,
        role=UserAccount.Role.MEMBER,
    )


@pytest.fixture
def admin_client(api_client: APIClient, admin_user: UserAccount) -> APIClient:
    response = api_client.post(
        "/api/v1/auth/login",
        {"username": admin_user.username, "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    return api_client


@pytest.fixture
def member_client(api_client: APIClient, member_user: UserAccount) -> APIClient:
    response = api_client.post(
        "/api/v1/auth/login",
        {"username": member_user.username, "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    return api_client


@pytest.fixture
def unused_invitation(db, admin_user: UserAccount) -> tuple[InvitationCode, str]:
    """返回未使用邀请码记录及仅用于测试的明文邀请码。"""
    return InvitationCode.objects.create_plain_code(
        role=UserAccount.Role.MEMBER,
        created_by=admin_user,
    )
