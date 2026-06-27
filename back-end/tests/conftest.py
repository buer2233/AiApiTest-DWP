"""pytest 公共 fixtures。"""
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from tests.factories import TEST_PASSWORD, UserFactory


@pytest.fixture
def password():
    return TEST_PASSWORD


@pytest.fixture
def api_client():
    """未认证的 DRF API 客户端。"""
    return APIClient()


@pytest.fixture
def active_user(db):
    """已激活的 member 用户。"""
    return UserFactory(status="active", role="member")


@pytest.fixture
def pending_user(db):
    """待审批用户。"""
    return UserFactory(status="pending", role="member")


@pytest.fixture
def disabled_user(db):
    """已停用用户。"""
    return UserFactory(status="disabled", role="member")


@pytest.fixture
def admin_user(db):
    """管理员用户（active + admin + is_staff）。"""
    return UserFactory(status="active", role="admin", is_staff=True)


@pytest.fixture
def auth_client(api_client, active_user):
    """携带有效 Token 的普通用户客户端。"""
    token, _ = Token.objects.get_or_create(user=active_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """携带有效 Token 的管理员客户端。"""
    token, _ = Token.objects.get_or_create(user=admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client
