"""Jenkins 集成 API 测试。
本文件使用 fake Jenkins client 验证后端接口行为，避免测试依赖真实 Jenkins 服务。
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db


class FakeJenkinsClient:
    """用于 API 测试的 Jenkins client 替身。
    记录每次调用参数，并返回固定结构，方便断言视图层参数传递是否正确。
    """

    calls = []

    @classmethod
    def reset(cls):
        """清空调用记录，保证每个测试互不影响。"""
        cls.calls = []

    def list_jobs(self):
        """模拟 Jenkins job 列表响应。"""
        self.calls.append(("list_jobs",))
        return [
            {"name": "api-test", "url": "http://jenkins.local/job/api-test/"},
            {"name": "nightly", "url": "http://jenkins.local/job/nightly/"},
        ]

    def list_builds(self, job_name):
        """模拟 Jenkins build 列表响应。"""
        self.calls.append(("list_builds", job_name))
        return [
            {"number": 12, "url": f"http://jenkins.local/job/{job_name}/12/"},
            {"number": 11, "url": f"http://jenkins.local/job/{job_name}/11/"},
        ]

    def get_build(self, job_name, build_number):
        """模拟 Jenkins build 详情响应。"""
        self.calls.append(("get_build", job_name, build_number))
        return {
            "number": build_number,
            "building": False,
            "result": "SUCCESS",
            "url": f"http://jenkins.local/job/{job_name}/{build_number}/",
            "timestamp": 1710000000000,
            "duration": 3210,
        }

    def get_console_log(self, job_name, build_number):
        """模拟 Jenkins 控制台日志响应。"""
        self.calls.append(("get_console_log", job_name, build_number))
        return "pytest output\nallure output\n"

    def trigger_build(self, job_name, parameters):
        """模拟 Jenkins 参数化构建触发响应。"""
        self.calls.append(("trigger_build", job_name, parameters))
        return {"queued": True, "status_code": 201}


def create_user(username="stage7-user", role="member"):
    """创建 Jenkins API 测试用户。"""
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        password="local-test-pass",
        role=role,
    )


@pytest.fixture(autouse=True)
def fake_jenkins_client(monkeypatch):
    """自动把视图层 Jenkins client 替换为 fake 实现。"""
    FakeJenkinsClient.reset()
    monkeypatch.setattr(
        "apps.jenkins_integration.views.build_jenkins_client",
        lambda: FakeJenkinsClient(),
    )


def authenticated_client():
    """返回已认证的 DRF APIClient。"""
    client = APIClient()
    client.force_authenticate(user=create_user())
    return client


def test_jobs_endpoint_returns_jobs():
    """验证 job 列表接口返回 Jenkins job 数据。"""
    client = authenticated_client()

    response = client.get("/api/jenkins/jobs/")

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["results"][0]["name"] == "api-test"
    assert FakeJenkinsClient.calls == [("list_jobs",)]


def test_builds_endpoint_returns_builds_for_job():
    """验证 build 列表接口把 job_name 传给 Jenkins client。"""
    client = authenticated_client()

    response = client.get("/api/jenkins/jobs/api-test/builds/")

    assert response.status_code == 200
    assert response.data["count"] == 2
    assert response.data["results"][0]["number"] == 12
    assert FakeJenkinsClient.calls == [("list_builds", "api-test")]


def test_build_detail_endpoint_returns_build_status():
    """验证 build 详情接口返回指定构建状态。"""
    client = authenticated_client()

    response = client.get("/api/jenkins/jobs/api-test/builds/12/")

    assert response.status_code == 200
    assert response.data["number"] == 12
    assert response.data["result"] == "SUCCESS"
    assert FakeJenkinsClient.calls == [("get_build", "api-test", 12)]


def test_console_endpoint_returns_text_payload():
    """验证 console 接口返回指定构建的日志文本。"""
    client = authenticated_client()

    response = client.get("/api/jenkins/jobs/api-test/builds/12/console/")

    assert response.status_code == 200
    assert response.data == {
        "job_name": "api-test",
        "build_number": 12,
        "console": "pytest output\nallure output\n",
    }
    assert FakeJenkinsClient.calls == [("get_console_log", "api-test", 12)]


def test_trigger_build_endpoint_passes_pipeline_parameters():
    """验证触发构建接口会转换并传递 Jenkins Pipeline 参数。"""
    client = authenticated_client()
    payload = {
        "case_path": "test_case/test_gbif_case",
        "pytest_node_ids": ["case1", "case2"],
        "retry_mode": "selected",
        "retry_count": 1,
        "clean_allure": True,
        "open_report": False,
    }

    response = client.post(
        "/api/jenkins/jobs/api-test/build/",
        payload,
        format="json",
    )

    assert response.status_code == 201
    assert response.data == {
        "queued": True,
        "status_code": 201,
        "job_name": "api-test",
    }
    assert FakeJenkinsClient.calls == [
        (
            "trigger_build",
            "api-test",
            {
                "CASE_PATH": "test_case/test_gbif_case",
                "PYTEST_NODE_IDS": "case1\ncase2",
                "RETRY_MODE": "selected",
                "RETRY_COUNT": "1",
                "CLEAN_ALLURE": "true",
                "OPEN_REPORT": "false",
            },
        )
    ]
