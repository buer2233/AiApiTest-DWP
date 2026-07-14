"""Stage13 Task 3B Jenkins API helper fake 状态机测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from platform_bootstrap.jenkins_api import (  # noqa: E402
    JenkinsApiClient,
    JenkinsTriggerConfig,
    encode_job_url,
)
from platform_bootstrap.models import HttpResponse  # noqa: E402


BASE_URL = "https://jenkins.example.invalid"
JOB_NAME = "Folder A/中文 Job"
QUEUE_URL = f"{BASE_URL}/queue/item/12/"
BUILD_URL = f"{BASE_URL}/job/Folder%20A/job/%E4%B8%AD%E6%96%87%20Job/42/"


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class FakeHttpClient:
    def __init__(self, routes):
        self.routes = {key: list(values) for key, values in routes.items()}
        self.calls = []

    def request(self, request):
        self.calls.append(request)
        key = (request.method, request.url)
        if key not in self.routes:
            raise AssertionError(f"unexpected HTTP request: {key}")
        values = self.routes[key]
        value = values.pop(0) if len(values) > 1 else values[0]
        if isinstance(value, Exception):
            raise value
        return value


def response(status, payload=None, headers=None):
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return HttpResponse(status=status, headers=headers or {}, body=body)


def write_env(tmp_path: Path, **overrides) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    values = {
        "JENKINS_API_BASE_URL": BASE_URL,
        "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME": JOB_NAME,
        "JENKINS_USERNAME": "private-user",
        "JENKINS_API_TOKEN": "private-token-value",
        "JENKINS_REQUEST_TIMEOUT_SECONDS": "15",
        "JENKINS_QUEUE_POLL_INTERVAL_SECONDS": "1",
        "JENKINS_BUILD_POLL_INTERVAL_SECONDS": "1",
        "JENKINS_BUILD_POLL_TIMEOUT_SECONDS": "30",
    }
    values.update(overrides)
    path = tmp_path / ".env"
    path.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")
    return path


def make_client(tmp_path, routes, **env_overrides):
    config = JenkinsTriggerConfig.load(write_env(tmp_path, **env_overrides))
    clock = FakeClock()
    http = FakeHttpClient(routes)
    client = JenkinsApiClient(
        config,
        http,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    return client, http, clock, config


def job_urls():
    job_url = encode_job_url(BASE_URL, JOB_NAME)
    return job_url, f"{job_url}/api/json", f"{job_url}/buildWithParameters"


def success_routes():
    _, job_api, trigger_url = job_urls()
    artifact_path = "runtime/platform-bootstrap/42/platform-bootstrap-summary.json"
    return {
        ("GET", job_api): [response(200, {"inQueue": False, "lastBuild": {"building": False}})],
        ("POST", trigger_url): [response(201, headers={"Location": QUEUE_URL})],
        ("GET", f"{QUEUE_URL}api/json"): [
            response(200, {"why": "waiting"}),
            response(200, {"executable": {"url": BUILD_URL, "number": 42}}),
        ],
        ("GET", f"{BUILD_URL}api/json"): [
            response(200, {"building": True, "result": None}),
            response(
                200,
                {
                    "building": False,
                    "result": "SUCCESS",
                    "url": BUILD_URL,
                    "artifacts": [
                        {
                            "fileName": "platform-bootstrap-summary.json",
                            "relativePath": artifact_path,
                        }
                    ],
                },
            ),
        ],
        ("GET", f"{BUILD_URL}artifact/{artifact_path}"): [
            response(200, {"success": True, "diagnostics": [], "addresses": {"frontend": "https://platform.example.invalid"}})
        ],
    }


def test_job_url_encodes_folder_space_and_chinese_per_segment():
    assert encode_job_url(BASE_URL, JOB_NAME) == (
        f"{BASE_URL}/job/Folder%20A/job/%E4%B8%AD%E6%96%87%20Job"
    )


def test_trigger_success_tracks_exact_queue_build_and_summary_without_leaking_credentials(tmp_path):
    client, http, _, _ = make_client(tmp_path, success_routes())

    outcome = client.trigger(build_all=False, run_full_tests=True)

    assert outcome.success is True
    assert outcome.status == "SUCCESS"
    assert outcome.build_url == BUILD_URL
    assert outcome.summary["success"] is True
    post = next(call for call in http.calls if call.method == "POST")
    assert parse_qs(post.body.decode("utf-8")) == {
        "build_all": ["false"],
        "run_full_tests": ["true"],
    }
    serialized = json.dumps(outcome.to_dict(), ensure_ascii=False)
    assert "private-user" not in serialized
    assert "private-token-value" not in serialized


def test_busy_returns_current_state_without_posting_second_build(tmp_path):
    _, job_api, _ = job_urls()
    routes = {
        ("GET", job_api): [
            response(200, {"inQueue": True, "queueItem": {"url": QUEUE_URL}, "lastBuild": {"building": True, "url": BUILD_URL}})
        ]
    }
    client, http, _, _ = make_client(tmp_path, routes)

    outcome = client.trigger(build_all=True, run_full_tests=False)

    assert outcome.success is False
    assert outcome.status == "BUSY"
    assert outcome.build_url == BUILD_URL
    assert all(call.method != "POST" for call in http.calls)


def test_busy_checks_last_build_api_when_job_payload_omits_building_flag(tmp_path):
    _, job_api, _ = job_urls()
    routes = {
        ("GET", job_api): [
            response(200, {"inQueue": False, "lastBuild": {"url": BUILD_URL, "number": 42}})
        ],
        ("GET", f"{BUILD_URL}api/json"): [
            response(200, {"building": True, "result": None, "url": BUILD_URL})
        ],
    }
    client, http, _, _ = make_client(tmp_path, routes)

    outcome = client.trigger(build_all=True, run_full_tests=False)

    assert outcome.status == "BUSY"
    assert outcome.build_url == BUILD_URL
    assert all(call.method != "POST" for call in http.calls)


def test_auth_job_not_found_and_server_failures_are_distinct_and_redacted(tmp_path):
    _, job_api, _ = job_urls()
    outcomes = []
    for status in [401, 403, 404, 503]:
        client, _, _, _ = make_client(
            tmp_path / str(status),
            {("GET", job_api): [response(status, {"message": "private-token-value"})]},
        )
        outcomes.append(client.trigger(build_all=True, run_full_tests=False))

    assert len({item.diagnostics[0].code for item in outcomes}) == 3
    assert outcomes[0].diagnostics[0].code == outcomes[1].diagnostics[0].code
    assert all(not item.success for item in outcomes)
    assert all("private-token-value" not in json.dumps(item.to_dict()) for item in outcomes)


def test_unreachable_queue_lost_cancel_and_aborted_are_distinct(tmp_path):
    _, job_api, trigger_url = job_urls()
    scenarios = [
        {("GET", job_api): [OSError("network unreachable private-token-value")]},
        {
            ("GET", job_api): [response(200, {"inQueue": False, "lastBuild": {"building": False}})],
            ("POST", trigger_url): [response(201, headers={"Location": QUEUE_URL})],
            ("GET", f"{QUEUE_URL}api/json"): [response(404)],
        },
        {
            ("GET", job_api): [response(200, {"inQueue": False, "lastBuild": {"building": False}})],
            ("POST", trigger_url): [response(201, headers={"Location": QUEUE_URL})],
            ("GET", f"{QUEUE_URL}api/json"): [response(200, {"cancelled": True})],
        },
        {
            ("GET", job_api): [response(200, {"inQueue": False, "lastBuild": {"building": False}})],
            ("POST", trigger_url): [response(201, headers={"Location": QUEUE_URL})],
            ("GET", f"{QUEUE_URL}api/json"): [response(200, {"executable": {"url": BUILD_URL}})],
            ("GET", f"{BUILD_URL}api/json"): [response(200, {"building": False, "result": "ABORTED", "artifacts": []})],
        },
    ]

    outcomes = []
    for index, routes in enumerate(scenarios):
        client, _, _, _ = make_client(tmp_path / str(index), routes)
        outcomes.append(client.trigger(build_all=True, run_full_tests=False))

    assert len({item.diagnostics[0].code for item in outcomes}) == 4
    assert all(not item.success for item in outcomes)
    assert outcomes[-1].status == "ABORTED"


def test_total_timeout_and_invalid_timeout_values_use_bounded_defaults(tmp_path):
    _, job_api, trigger_url = job_urls()
    routes = {
        ("GET", job_api): [response(200, {"inQueue": False, "lastBuild": {"building": False}})],
        ("POST", trigger_url): [response(201, headers={"Location": QUEUE_URL})],
        ("GET", f"{QUEUE_URL}api/json"): [response(200, {"why": "still waiting"})],
    }
    client, _, clock, config = make_client(
        tmp_path,
        routes,
        JENKINS_REQUEST_TIMEOUT_SECONDS="invalid",
        JENKINS_QUEUE_POLL_INTERVAL_SECONDS="0",
        JENKINS_BUILD_POLL_INTERVAL_SECONDS="999999",
        JENKINS_BUILD_POLL_TIMEOUT_SECONDS="2",
    )

    outcome = client.trigger(build_all=True, run_full_tests=False)

    assert config.request_timeout_seconds == 15
    assert config.queue_poll_interval_seconds == 5
    assert config.build_poll_interval_seconds == 10
    assert config.total_timeout_seconds == 2
    assert outcome.success is False
    assert outcome.status == "TIMEOUT"
    assert clock.value <= 2


def test_failed_and_aborted_builds_preserve_downloaded_structured_summary(tmp_path):
    _, job_api, trigger_url = job_urls()
    artifact_path = "runtime/platform-bootstrap/42/platform-bootstrap-summary.json"
    for terminal in ["FAILURE", "ABORTED"]:
        routes = {
            ("GET", job_api): [response(200, {"inQueue": False, "lastBuild": {"building": False}})],
            ("POST", trigger_url): [response(201, headers={"Location": QUEUE_URL})],
            ("GET", f"{QUEUE_URL}api/json"): [response(200, {"executable": {"url": BUILD_URL}})],
            ("GET", f"{BUILD_URL}api/json"): [
                response(
                    200,
                    {
                        "building": False,
                        "result": terminal,
                        "artifacts": [{"fileName": "platform-bootstrap-summary.json", "relativePath": artifact_path}],
                    },
                )
            ],
            ("GET", f"{BUILD_URL}artifact/{artifact_path}"): [
                response(
                    200,
                    {
                        "success": False,
                        "diagnostics": [
                            {
                                "stage": "health",
                                "code": "HEALTH_FAILED",
                                "target": "backend-ready",
                                "reason": "not ready",
                                "observed": "status=503",
                                "evidence": ["health.log"],
                                "suggestion": "repair database",
                                "rerun": "rerun build",
                            }
                        ],
                    },
                )
            ],
        }
        client, _, _, _ = make_client(tmp_path / terminal, routes)

        outcome = client.trigger(build_all=True, run_full_tests=False)

        assert outcome.success is False
        assert outcome.status == terminal
        assert outcome.summary["success"] is False
        assert outcome.summary["diagnostics"][0]["evidence"] == ["health.log"]
