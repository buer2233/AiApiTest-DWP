"""F6 用例同步接口测试（AC6.1-AC6.4 + 权限/幂等）。"""
import textwrap
from pathlib import Path

import pytest

from apps.testcases.models import TestCaseSnapshot

SYNC_URL = "/api/testcases/sync/"


def _make_cases(root: Path):
    """在 root/test_case 下构造一个带 allure 装饰的用例。"""
    d = root / "test_case" / "test_login_case"
    d.mkdir(parents=True, exist_ok=True)
    (d / "test_login.py").write_text(
        textwrap.dedent(
            '''
            import allure

            @allure.story("登录")
            @allure.severity(allure.severity_level.CRITICAL)
            def test_login_ok():
                """登录成功"""
                pass
            '''
        ),
        encoding="utf-8",
    )


@pytest.mark.django_db
class TestSync:
    def test_admin_sync_creates_records(self, admin_client, settings, tmp_path):
        # AC6.1
        _make_cases(tmp_path)
        settings.API_TEST_ROOT = str(tmp_path)
        resp = admin_client.post(SYNC_URL)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["scanned"] >= 1
        assert data["created"] >= 1
        for key in ["scanned", "created", "updated", "deactivated", "synced_at"]:
            assert key in data
        obj = TestCaseSnapshot.objects.get(function_name="test_login_ok")
        assert obj.story == "登录"
        assert obj.severity == "critical"

    def test_member_sync_forbidden(self, auth_client):
        # AC6.3
        resp = auth_client.post(SYNC_URL)
        assert resp.status_code == 403
        assert resp.json()["code"] == 1201

    def test_unauthenticated_sync(self, api_client):
        # 鉴权先于权限
        resp = api_client.post(SYNC_URL)
        assert resp.status_code == 401

    def test_invalid_root(self, admin_client, settings, tmp_path):
        # AC6.4
        settings.API_TEST_ROOT = str(tmp_path / "nonexistent")
        resp = admin_client.post(SYNC_URL)
        assert resp.status_code == 400
        assert resp.json()["code"] == 1202

    def test_soft_delete_and_restore(self, admin_client, settings, tmp_path):
        # AC6.2
        _make_cases(tmp_path)
        settings.API_TEST_ROOT = str(tmp_path)
        admin_client.post(SYNC_URL)
        case_file = tmp_path / "test_case" / "test_login_case" / "test_login.py"
        case_file.unlink()
        resp = admin_client.post(SYNC_URL)
        assert resp.json()["data"]["deactivated"] >= 1
        obj = TestCaseSnapshot.objects.get(function_name="test_login_ok")
        assert obj.is_active is False
        # 恢复文件再同步 → is_active 复原
        _make_cases(tmp_path)
        admin_client.post(SYNC_URL)
        obj.refresh_from_db()
        assert obj.is_active is True

    def test_upsert_idempotent(self, admin_client, settings, tmp_path):
        # TC-SYNC-008
        _make_cases(tmp_path)
        settings.API_TEST_ROOT = str(tmp_path)
        admin_client.post(SYNC_URL)
        count1 = TestCaseSnapshot.objects.count()
        r2 = admin_client.post(SYNC_URL)
        count2 = TestCaseSnapshot.objects.count()
        assert count1 == count2
        assert r2.json()["data"]["created"] == 0
