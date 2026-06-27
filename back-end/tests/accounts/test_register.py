"""F1 用户注册测试（AC1.1-AC1.4 + 异常/边界）。"""
import pytest
from django.contrib.auth import get_user_model

from tests.factories import TEST_PASSWORD, UserFactory

User = get_user_model()
REGISTER_URL = "/api/auth/register/"


def _payload(**over):
    data = {
        "username": "tester_new",
        "email": "tester_new@example.test",
        "password": TEST_PASSWORD,
        "password_confirm": TEST_PASSWORD,
    }
    data.update(over)
    return data


@pytest.mark.django_db
class TestRegister:
    def test_success_creates_pending_user(self, api_client):
        # AC1.1
        resp = api_client.post(REGISTER_URL, _payload(), format="json")
        assert resp.status_code == 201
        body = resp.json()
        assert body["code"] == 0
        assert "token" not in body["data"]
        assert body["data"]["status"] == "pending"
        assert body["data"]["role"] == "member"
        u = User.objects.get(username="tester_new")
        assert u.is_active is False

    def test_duplicate_username(self, api_client):
        # AC1.2
        UserFactory(username="tester_exist")
        resp = api_client.post(
            REGISTER_URL, _payload(username="tester_exist", email="other@example.test"), format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 1001

    def test_duplicate_email(self, api_client):
        # AC1.3
        UserFactory(email="dup@example.test")
        resp = api_client.post(
            REGISTER_URL, _payload(username="newname", email="dup@example.test"), format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 1002

    def test_password_mismatch(self, api_client):
        # AC1.4
        resp = api_client.post(REGISTER_URL, _payload(password_confirm="Mismatch#2026"), format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == 1003

    def test_weak_password_numeric(self, api_client):
        # TC-REG-005：纯数字弱密码
        resp = api_client.post(
            REGISTER_URL, _payload(password="12345678", password_confirm="12345678"), format="json"
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 1004

    def test_invalid_email_format(self, api_client):
        # TC-REG-006
        resp = api_client.post(REGISTER_URL, _payload(email="not-an-email"), format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == 1004

    def test_missing_username(self, api_client):
        # TC-REG-007
        data = _payload()
        data.pop("username")
        resp = api_client.post(REGISTER_URL, data, format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == 1004

    def test_username_too_short(self, api_client):
        # TC-REG-008：低于下界 3
        resp = api_client.post(REGISTER_URL, _payload(username="ab"), format="json")
        assert resp.status_code == 400

    def test_username_min_boundary_ok(self, api_client):
        # TC-REG-008：下界 3 通过
        resp = api_client.post(
            REGISTER_URL, _payload(username="abc", email="abc@example.test"), format="json"
        )
        assert resp.status_code == 201

    def test_integrity_error_maps_to_business_code_not_500(self, api_client):
        # 审查补充：唯一性预检查通过后并发竞态导致 save 抛 IntegrityError，
        # 应兜底为 400 业务码而非 500。
        from unittest.mock import patch

        from django.db import IntegrityError

        with patch(
            "apps.accounts.serializers.RegisterSerializer.save",
            side_effect=IntegrityError(),
        ):
            resp = api_client.post(REGISTER_URL, _payload(), format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] in (1001, 1002)
