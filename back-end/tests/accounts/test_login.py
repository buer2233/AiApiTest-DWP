"""F2 用户登录测试（AC2.1-AC2.4 + 防枚举/幂等）。"""
import pytest

from tests.factories import TEST_PASSWORD

LOGIN_URL = "/api/auth/login/"


@pytest.mark.django_db
class TestLogin:
    def test_active_user_login_success(self, api_client, active_user):
        # AC2.1
        resp = api_client.post(
            LOGIN_URL, {"username": active_user.username, "password": TEST_PASSWORD}, format="json"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["token"]
        assert data["user"]["status"] == "active"
        assert data["user"]["username"] == active_user.username

    def test_unknown_username_unified_error(self, api_client):
        # AC2.2：用户名不存在 → 统一提示
        resp = api_client.post(
            LOGIN_URL, {"username": "nobody_xyz", "password": TEST_PASSWORD}, format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 1101
        assert resp.json()["message"] == "用户名或密码错误"

    def test_wrong_password_unified_error(self, api_client, active_user):
        # AC2.2：密码错误 → 与"用户名不存在"完全相同的响应（防枚举）
        resp = api_client.post(
            LOGIN_URL, {"username": active_user.username, "password": "WrongPass#2026"}, format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 1101
        assert resp.json()["message"] == "用户名或密码错误"

    def test_pending_user_forbidden(self, api_client, pending_user):
        # AC2.3
        resp = api_client.post(
            LOGIN_URL, {"username": pending_user.username, "password": TEST_PASSWORD}, format="json"
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == 1102

    def test_disabled_user_forbidden(self, api_client, disabled_user):
        # AC2.4
        resp = api_client.post(
            LOGIN_URL, {"username": disabled_user.username, "password": TEST_PASSWORD}, format="json"
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == 1103

    def test_missing_password(self, api_client):
        resp = api_client.post(LOGIN_URL, {"username": "x"}, format="json")
        assert resp.status_code == 400

    def test_token_reused_on_multiple_login(self, api_client, active_user):
        # 幂等：多次登录复用同一 token
        r1 = api_client.post(
            LOGIN_URL, {"username": active_user.username, "password": TEST_PASSWORD}, format="json"
        )
        r2 = api_client.post(
            LOGIN_URL, {"username": active_user.username, "password": TEST_PASSWORD}, format="json"
        )
        assert r1.json()["data"]["token"] == r2.json()["data"]["token"]
