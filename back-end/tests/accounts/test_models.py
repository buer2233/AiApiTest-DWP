"""User 模型测试：状态不变式与停用下线（TC-APPROVE-005 模型层保证）。"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from tests.factories import TEST_PASSWORD

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_active_status_sets_is_active_true(self):
        u = User(username="u_active", email="u_active@example.test", status="active")
        u.set_password(TEST_PASSWORD)
        u.save()
        assert u.is_active is True

    def test_pending_status_sets_is_active_false(self):
        u = User(username="u_pending", email="u_pending@example.test", status="pending")
        u.save()
        assert u.is_active is False

    def test_disabled_status_sets_is_active_false(self):
        u = User(username="u_disabled", email="u_disabled@example.test", status="disabled")
        u.save()
        assert u.is_active is False

    def test_disabling_user_deletes_token(self):
        """active 用户被改为 disabled 时，其 Token 被删除（强制下线）。"""
        u = User(username="u_tok", email="u_tok@example.test", status="active")
        u.set_password(TEST_PASSWORD)
        u.save()
        Token.objects.create(user=u)
        u.status = "disabled"
        u.save()
        assert not Token.objects.filter(user=u).exists()

    def test_superuser_forced_active_admin(self):
        su = User.objects.create_superuser(
            username="root", email="root@example.test", password=TEST_PASSWORD
        )
        assert su.status == "active"
        assert su.role == "admin"
        assert su.is_active is True
        assert su.is_staff is True
