"""F4 当前用户信息测试（AC4.1-AC4.2）。"""
import pytest

ME_URL = "/api/auth/me/"


@pytest.mark.django_db
class TestMe:
    def test_me_with_valid_token(self, auth_client, active_user):
        # AC4.1
        resp = auth_client.get(ME_URL)
        assert resp.status_code == 200
        data = resp.json()["data"]
        for field in ["id", "username", "email", "role", "status", "date_joined", "last_login"]:
            assert field in data
        assert data["username"] == active_user.username

    def test_me_without_token(self, api_client):
        # AC4.2
        resp = api_client.get(ME_URL)
        assert resp.status_code == 401
