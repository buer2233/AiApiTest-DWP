import pytest
from django.test import override_settings

from apps.jenkins_integration.client import JenkinsClient, JenkinsConfig


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self):
        self.auth = None
        self.headers = {}
        self.calls = []
        self.routes = {}

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.routes[("GET", url)]

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.routes[("POST", url)]


def make_client():
    session = FakeSession()
    client = JenkinsClient(
        JenkinsConfig(
            base_url="http://jenkins.local/",
            username="local-user",
            api_token="local-token",
            default_job="api-test",
        ),
        session=session,
    )
    return client, session


def test_client_config_can_be_loaded_from_django_settings():
    with override_settings(
        JENKINS_BASE_URL="http://jenkins.local",
        JENKINS_USERNAME="settings-user",
        JENKINS_API_TOKEN="settings-token",
        JENKINS_DEFAULT_JOB="settings-job",
    ):
        config = JenkinsConfig.from_settings()

    assert config.base_url == "http://jenkins.local"
    assert config.username == "settings-user"
    assert config.api_token == "settings-token"
    assert config.default_job == "settings-job"


def test_client_lists_jobs():
    client, session = make_client()
    session.routes[("GET", "http://jenkins.local/api/json")] = FakeResponse(
        payload={
            "jobs": [
                {"name": "api-test", "url": "http://jenkins.local/job/api-test/"},
                {"name": "nightly", "url": "http://jenkins.local/job/nightly/"},
            ]
        }
    )

    jobs = client.list_jobs()

    assert jobs == [
        {"name": "api-test", "url": "http://jenkins.local/job/api-test/"},
        {"name": "nightly", "url": "http://jenkins.local/job/nightly/"},
    ]
    assert session.auth == ("local-user", "local-token")


def test_client_lists_builds_for_job():
    client, session = make_client()
    session.routes[("GET", "http://jenkins.local/job/api-test/api/json")] = FakeResponse(
        payload={
            "builds": [
                {"number": 12, "url": "http://jenkins.local/job/api-test/12/"},
                {"number": 11, "url": "http://jenkins.local/job/api-test/11/"},
            ]
        }
    )

    builds = client.list_builds("api-test")

    assert builds == [
        {"number": 12, "url": "http://jenkins.local/job/api-test/12/"},
        {"number": 11, "url": "http://jenkins.local/job/api-test/11/"},
    ]


def test_client_gets_build_status():
    client, session = make_client()
    session.routes[
        ("GET", "http://jenkins.local/job/api-test/12/api/json")
    ] = FakeResponse(
        payload={
            "number": 12,
            "building": False,
            "result": "SUCCESS",
            "url": "http://jenkins.local/job/api-test/12/",
            "timestamp": 1710000000000,
            "duration": 3210,
        }
    )

    build = client.get_build("api-test", 12)

    assert build == {
        "number": 12,
        "building": False,
        "result": "SUCCESS",
        "url": "http://jenkins.local/job/api-test/12/",
        "timestamp": 1710000000000,
        "duration": 3210,
    }


def test_client_gets_console_log():
    client, session = make_client()
    session.routes[
        ("GET", "http://jenkins.local/job/api-test/12/consoleText")
    ] = FakeResponse(text="pytest output\nallure output\n")

    console = client.get_console_log("api-test", 12)

    assert console == "pytest output\nallure output\n"


def test_client_triggers_parameterized_build_with_pipeline_parameters():
    client, session = make_client()
    trigger_url = "http://jenkins.local/job/api-test/buildWithParameters"
    session.routes[("POST", trigger_url)] = FakeResponse(
        status_code=201,
        payload={},
    )

    result = client.trigger_build(
        "api-test",
        parameters={
            "CASE_PATH": "test_case/test_gbif_case",
            "PYTEST_NODE_IDS": "case1\ncase2",
            "RETRY_MODE": "selected",
            "RETRY_COUNT": "1",
            "CLEAN_ALLURE": "true",
            "OPEN_REPORT": "false",
        },
    )

    assert result == {"queued": True, "status_code": 201}
    assert session.calls[-1] == (
        "POST",
        trigger_url,
        {
            "data": {
                "CASE_PATH": "test_case/test_gbif_case",
                "PYTEST_NODE_IDS": "case1\ncase2",
                "RETRY_MODE": "selected",
                "RETRY_COUNT": "1",
                "CLEAN_ALLURE": "true",
                "OPEN_REPORT": "false",
            }
        },
    )


def test_client_rejects_missing_credentials():
    with pytest.raises(ValueError, match="Jenkins configuration is incomplete"):
        JenkinsClient(JenkinsConfig(base_url="", username="", api_token=""))
