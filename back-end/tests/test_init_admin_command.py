import pytest
from django.core.management import call_command

from accounts.models import UserAccount


pytestmark = pytest.mark.command


def test_init_admin_command_creates_admin_from_environment(db, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_USERNAME", "admin_user")
    monkeypatch.setenv("INITIAL_ADMIN_DISPLAY_NAME", "平台管理员")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "TestPass123")

    call_command("init_admin")

    user = UserAccount.objects.get(username="admin_user")
    assert user.role == UserAccount.Role.ADMIN
    assert user.display_name == "平台管理员"
    assert user.check_password("TestPass123")


def test_init_admin_command_is_idempotent(db, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_USERNAME", "admin_user")
    monkeypatch.setenv("INITIAL_ADMIN_DISPLAY_NAME", "平台管理员")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "TestPass123")

    call_command("init_admin")
    call_command("init_admin")

    assert UserAccount.objects.filter(username="admin_user").count() == 1


def test_init_admin_command_fails_without_required_environment(db, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_USERNAME", "admin_user")
    monkeypatch.delenv("INITIAL_ADMIN_DISPLAY_NAME", raising=False)
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)

    with pytest.raises(Exception, match="INITIAL_ADMIN_DISPLAY_NAME, INITIAL_ADMIN_PASSWORD"):
        call_command("init_admin")

    assert UserAccount.objects.count() == 0
