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


def test_init_admin_bootstrap_only_skips_existing_accounts_without_reading_environment(db, monkeypatch):
    existing = UserAccount.objects.create_user(
        username="existing_member",
        display_name="既有成员",
        password="ExistingPass123",
        role=UserAccount.Role.MEMBER,
    )
    for name in ["INITIAL_ADMIN_USERNAME", "INITIAL_ADMIN_DISPLAY_NAME", "INITIAL_ADMIN_PASSWORD"]:
        monkeypatch.delenv(name, raising=False)

    call_command("init_admin", "--bootstrap-only")

    existing.refresh_from_db()
    assert UserAccount.objects.count() == 1
    assert existing.role == UserAccount.Role.MEMBER
    assert existing.display_name == "既有成员"


def test_init_admin_bootstrap_only_creates_the_first_admin_from_environment(db, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_USERNAME", "bootstrap_admin")
    monkeypatch.setenv("INITIAL_ADMIN_DISPLAY_NAME", "首装管理员")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "BootstrapPass123")

    call_command("init_admin", "--bootstrap-only")

    user = UserAccount.objects.get(username="bootstrap_admin")
    assert user.role == UserAccount.Role.ADMIN
    assert user.display_name == "首装管理员"


def test_init_admin_without_bootstrap_only_keeps_existing_update_behavior(db, monkeypatch):
    existing = UserAccount.objects.create_user(
        username="existing_admin",
        display_name="旧显示名",
        password="ExistingPass123",
        role=UserAccount.Role.MEMBER,
    )
    monkeypatch.setenv("INITIAL_ADMIN_USERNAME", "existing_admin")
    monkeypatch.setenv("INITIAL_ADMIN_DISPLAY_NAME", "新显示名")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "BootstrapPass123")

    call_command("init_admin")

    existing.refresh_from_db()
    assert existing.role == UserAccount.Role.ADMIN
    assert existing.display_name == "新显示名"
