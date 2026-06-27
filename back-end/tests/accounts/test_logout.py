"""F3 用户登出测试（AC3.1 + 异常）。"""
import pytest
from rest_framework.authtoken.models import Token

LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"


@pytest.mark.django_db
class TestLogout:
    def test_logout_invalidates_token(self, api_client, active_user):
        # AC3.1：登出后旧 token 失效
        token = Token.objects.create(user=active_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        resp = api_client.post(LOGOUT_URL)
        assert resp.status_code == 200
        # 旧 token 再访问鉴权接口 → 401
        resp2 = api_client.get(ME_URL)
        assert resp2.status_code == 401

    def test_logout_without_token(self, api_client):
        resp = api_client.post(LOGOUT_URL)
        assert resp.status_code == 401
