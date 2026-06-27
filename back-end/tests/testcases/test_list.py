"""F7 用例列表接口测试（AC7.1-AC7.4 + 边界）。"""
import pytest
from django.utils import timezone

from apps.testcases.models import TestCaseSnapshot

LIST_URL = "/api/testcases/"


def _make_snapshot(node_id, module_key="m1", title="t", fn="test_x", is_active=True):
    return TestCaseSnapshot.objects.create(
        module_key=module_key,
        module_name=module_key,
        case_path=f"test_case/{node_id}",
        node_id=node_id,
        function_name=fn,
        class_name=None,
        case_title=title,
        story="",
        severity="normal",
        is_active=is_active,
        synced_at=timezone.now(),
    )


@pytest.mark.django_db
class TestList:
    def test_list_requires_auth(self, api_client):
        # AC7.4
        resp = api_client.get(LIST_URL)
        assert resp.status_code == 401

    def test_list_returns_active_paginated(self, auth_client):
        # AC7.1
        for i in range(3):
            _make_snapshot(f"test_case/m1/test_a.py::test_{i}", fn=f"test_{i}")
        resp = auth_client.get(LIST_URL)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["count"] == 3
        assert len(data["results"]) == 3
        # 字段齐全
        for field in ["module_key", "node_id", "case_title", "story", "severity"]:
            assert field in data["results"][0]

    def test_filter_by_module_key(self, auth_client):
        # AC7.2
        _make_snapshot("test_case/m1/test_a.py::test_1", module_key="m1", fn="test_1")
        _make_snapshot("test_case/m2/test_b.py::test_2", module_key="m2", fn="test_2")
        resp = auth_client.get(LIST_URL, {"module_key": "m1"})
        data = resp.json()["data"]
        assert data["count"] == 1
        assert data["results"][0]["module_key"] == "m1"

    def test_keyword_matches_node_id(self, auth_client):
        # AC7.3
        _make_snapshot("test_case/m1/test_login.py::test_login", fn="test_login", title="登录")
        _make_snapshot("test_case/m1/test_logout.py::test_logout", fn="test_logout", title="登出")
        resp = auth_client.get(LIST_URL, {"keyword": "login"})
        data = resp.json()["data"]
        assert data["count"] == 1
        assert "login" in data["results"][0]["node_id"]

    def test_only_active_listed(self, auth_client):
        # 数据一致性：软删用例不出现
        _make_snapshot("test_case/m1/test_a.py::test_active", fn="test_active", is_active=True)
        _make_snapshot("test_case/m1/test_a.py::test_inactive", fn="test_inactive", is_active=False)
        resp = auth_client.get(LIST_URL)
        data = resp.json()["data"]
        assert data["count"] == 1
        assert all("inactive" not in r["node_id"] for r in data["results"])

    def test_page_size_cap(self, auth_client):
        # 边界：page_size 超 100 截断（此处用小数据验证不报错且返回正常）
        for i in range(5):
            _make_snapshot(f"test_case/m1/test_a.py::test_{i}", fn=f"test_{i}")
        resp = auth_client.get(LIST_URL, {"page_size": 200})
        data = resp.json()["data"]
        assert len(data["results"]) == 5

    def test_empty_result(self, auth_client):
        # 边界：空集
        resp = auth_client.get(LIST_URL, {"module_key": "nonexistent"})
        data = resp.json()["data"]
        assert data["count"] == 0
        assert data["results"] == []
