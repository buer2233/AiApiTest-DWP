"""F5 管理员审批测试（AC5.1-AC5.3 + 状态流转 + 强制下线）。

审批走 Django Admin，本测试通过"修改 status 保存 + 登录验证"组合覆盖模型层行为，
并验证非 staff 无法进入后台。
"""
import pytest
from rest_framework.authtoken.models import Token

from tests.factories import TEST_PASSWORD

LOGIN_URL = "/api/auth/login/"
ME_URL = "/api/auth/me/"


@pytest.mark.django_db
class TestAdminApproval:
    def test_approve_pending_to_active_enables_login(self, api_client, pending_user):
        # AC5.1：pending → active，is_active 同步，可登录
        pending_user.status = "active"
        pending_user.save()
        assert pending_user.is_active is True
        resp = api_client.post(
            LOGIN_URL, {"username": pending_user.username, "password": TEST_PASSWORD}, format="json"
        )
        assert resp.status_code == 200

    def test_disable_active_blocks_login(self, api_client, active_user):
        # AC5.2：active → disabled，登录被拒
        active_user.status = "disabled"
        active_user.save()
        assert active_user.is_active is False
        resp = api_client.post(
            LOGIN_URL, {"username": active_user.username, "password": TEST_PASSWORD}, format="json"
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == 1103

    def test_member_cannot_access_admin(self, client, active_user):
        # AC5.3：is_staff=False 的 member 无法进入 Django Admin
        client.login(username=active_user.username, password=TEST_PASSWORD)
        resp = client.get("/admin/")
        assert resp.status_code == 302
        assert "/admin/login" in resp.url

    def test_disabled_to_active_restores_login(self, api_client, disabled_user):
        # 状态流转：disabled → active 恢复登录
        disabled_user.status = "active"
        disabled_user.save()
        resp = api_client.post(
            LOGIN_URL, {"username": disabled_user.username, "password": TEST_PASSWORD}, format="json"
        )
        assert resp.status_code == 200

    def test_disabling_forces_logout(self, api_client, active_user):
        # TC-APPROVE-005：停用即强制下线（旧 token 失效）
        token = Token.objects.create(user=active_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        assert api_client.get(ME_URL).status_code == 200
        active_user.status = "disabled"
        active_user.save()
        assert api_client.get(ME_URL).status_code == 401
