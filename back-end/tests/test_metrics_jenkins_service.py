from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone as datetime_timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from django.test import override_settings

from metrics.jenkins_service import (
    JenkinsBuildMatchError,
    JenkinsServiceError,
    _timestamp_matches_date,
    cancel_jenkins_task,
    discover_jenkins_builds,
    fetch_jenkins_task_result,
    trigger_jenkins_build,
)


class FakeJenkinsResponse:
    def __init__(self, payload=None, headers=None):
        self._payload = payload
        self.headers = headers or {}

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class RawJenkinsResponse(FakeJenkinsResponse):
    def __init__(self, payload: bytes):
        super().__init__()
        self._raw_payload = payload

    def read(self):
        return self._raw_payload


@override_settings(TIME_ZONE="Asia/Shanghai")
def test_timestamp_date_filter_uses_django_local_timezone():
    timestamp_ms = 1783706400000
    utc_time = datetime(2026, 7, 10, 18, 0, tzinfo=datetime_timezone.utc)

    with patch("metrics.jenkins_service.datetime") as datetime_class:
        datetime_class.fromtimestamp.return_value = utc_time
        assert _timestamp_matches_date(timestamp_ms, "2026-07-11") is True

    datetime_class.fromtimestamp.assert_called_once_with(timestamp_ms / 1000, tz=datetime_timezone.utc)


def test_fetch_task_result_wraps_invalid_jenkins_json(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setattr(
        "metrics.jenkins_service.urllib.request.urlopen",
        lambda request, timeout: RawJenkinsResponse(b"{invalid-json"),
    )
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=12,
        queue_id="",
        run=SimpleNamespace(run_key="invalid-json-run"),
    )

    with pytest.raises(JenkinsServiceError, match="invalid JSON"):
        fetch_jenkins_task_result(task)


@pytest.mark.parametrize("invalid_build_number", ["invalid", True, 3.5, 0, -1, "1.5"])
def test_discover_builds_wraps_invalid_build_number(monkeypatch, invalid_build_number):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setattr(
        "metrics.jenkins_service.urllib.request.urlopen",
        lambda request, timeout: FakeJenkinsResponse(
            {"builds": [{"number": invalid_build_number, "url": "", "result": "SUCCESS", "building": False}]}
        ),
    )

    with pytest.raises(JenkinsServiceError, match="build number"):
        discover_jenkins_builds(job_full_names=["AiApiTest-DWP-Daily-Full-Module-example"])


def test_fetch_task_result_wraps_invalid_queue_executable_object(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setattr(
        "metrics.jenkins_service.urllib.request.urlopen",
        lambda request, timeout: FakeJenkinsResponse({"executable": "invalid"}),
    )
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=None,
        queue_id="99",
        run=SimpleNamespace(run_key="invalid-executable-run"),
    )

    with pytest.raises(JenkinsServiceError, match="invalid JSON object"):
        fetch_jenkins_task_result(task)


def test_fetch_task_result_wraps_invalid_build_parameter_object(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/queue/item/99/api/json"):
            raise HTTPError(request.full_url, 404, "Not Found", None, None)
        if "/job/AiApiTest-DWP-Module-Rerun/api/json?tree=builds" in request.full_url:
            return FakeJenkinsResponse({"builds": [{"number": 12, "queueId": None, "actions": ["invalid"]}]})
        raise AssertionError(f"Unexpected Jenkins URL: {request.full_url}")

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=None,
        queue_id="99",
        run=SimpleNamespace(run_key="invalid-parameter-run"),
    )

    with pytest.raises(JenkinsServiceError, match="invalid JSON object"):
        fetch_jenkins_task_result(task)


def test_trigger_build_uses_internal_api_url_but_returns_public_queue_url(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "https://ci.example.test")
    requested_urls: list[str] = []

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        return FakeJenkinsResponse(headers={"Location": "http://jenkins:8080/queue/item/99/"})

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)

    result = trigger_jenkins_build(job_full_name="folder/AiApiTest-DWP-Failed-Rerun", parameters={"RETRY_MODE": "selected"})

    assert requested_urls == ["http://jenkins:8080/job/folder/job/AiApiTest-DWP-Failed-Rerun/buildWithParameters"]
    assert result["queue_url"] == "https://ci.example.test/queue/item/99/"
    assert result["queue_id"] == "99"


def test_trigger_build_falls_back_to_public_url_when_internal_api_url_missing(monkeypatch):
    monkeypatch.delenv("JENKINS_API_BASE_URL", raising=False)
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "http://localhost:8080")
    requested_urls: list[str] = []

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        return FakeJenkinsResponse(headers={"Location": "http://localhost:8080/queue/item/101/"})

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)

    result = trigger_jenkins_build(job_full_name="AiApiTest-DWP-Failed-Rerun", parameters={"RETRY_MODE": "selected"})

    assert requested_urls == ["http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/buildWithParameters"]
    assert result["queue_id"] == "101"


def test_fetch_task_result_returns_public_artifact_urls(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "https://ci.example.test")

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/api/json"):
            return FakeJenkinsResponse({"building": False, "result": "SUCCESS"})
        if request.full_url.endswith("/summary.json"):
            return FakeJenkinsResponse({"status": "passed", "total_count": 1, "failed_count": 0})
        if request.full_url.endswith("/failed_nodeids.json"):
            return FakeJenkinsResponse([])
        raise AssertionError(f"Unexpected Jenkins URL: {request.full_url}")

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=12,
        queue_id="",
        run=SimpleNamespace(run_key="module-rerun-12"),
    )

    result = fetch_jenkins_task_result(task)

    assert result["artifact_base_url"] == (
        "https://ci.example.test/job/AiApiTest-DWP-Module-Rerun/12/artifact/api-test/runtime/ci-runs/module-rerun-12"
    )
    assert result["summary_artifact_url"].startswith("https://ci.example.test/")
    assert result["allure_report_url"] == "https://ci.example.test/job/AiApiTest-DWP-Module-Rerun/12/allure/"


def test_fetch_task_result_marks_queue_pending_when_no_executable(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "https://ci.example.test")

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://jenkins:8080/queue/item/99/api/json"
        return FakeJenkinsResponse({})

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(job_full_name="AiApiTest-DWP-Failed-Rerun", build_number=None, queue_id="99", run=None)

    result = fetch_jenkins_task_result(task)

    assert result == {"queue_pending": True}


def test_fetch_task_result_marks_queue_canceled_when_queue_item_was_canceled(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://jenkins:8080/queue/item/99/api/json"
        return FakeJenkinsResponse({"cancelled": True})

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(job_full_name="AiApiTest-DWP-Failed-Rerun", build_number=None, queue_id="99", run=None)

    result = fetch_jenkins_task_result(task)

    assert result == {"canceled": True}


def test_fetch_task_result_recovers_expired_queue_by_queue_id_and_reads_terminal_artifacts(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "https://ci.example.test")
    run_key = "module_rerun-1-1-20260712070705994583"
    timestamp_ms = 1783840035760
    duration_ms = 86000
    requested_urls: list[str] = []

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        if request.full_url == "http://jenkins:8080/queue/item/173/api/json":
            raise HTTPError(request.full_url, 404, "Not Found", None, None)
        if "/job/AiApiTest-DWP-Module-Rerun/api/json?tree=builds" in request.full_url:
            return FakeJenkinsResponse(
                {
                    "builds": [
                        {
                            "number": 28,
                            "queueId": 172,
                            "actions": [{"parameters": [{"name": "RUN_ID", "value": "another-run"}]}],
                        },
                        {
                            "number": 29,
                            "queueId": 173,
                            "actions": [{"parameters": [{"name": "RUN_ID", "value": run_key}]}],
                        },
                    ]
                }
            )
        if request.full_url == "http://jenkins:8080/job/AiApiTest-DWP-Module-Rerun/29/api/json":
            return FakeJenkinsResponse(
                {
                    "building": False,
                    "result": "SUCCESS",
                    "timestamp": timestamp_ms,
                    "duration": duration_ms,
                }
            )
        if request.full_url.endswith("/summary.json"):
            return FakeJenkinsResponse({"status": "passed", "total_count": 1, "failed_count": 0})
        if request.full_url.endswith("/failed_nodeids.json"):
            return FakeJenkinsResponse([])
        raise AssertionError(f"Unexpected Jenkins URL: {request.full_url}")

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=None,
        queue_id="173",
        run=SimpleNamespace(run_key=run_key),
    )

    result = fetch_jenkins_task_result(task)

    expected_started_at = datetime.fromtimestamp(timestamp_ms / 1000, tz=datetime_timezone.utc)
    assert result["build_number"] == 29
    assert result["jenkins_result"] == "SUCCESS"
    assert result["started_at"] == expected_started_at
    assert result["finished_at"] == expected_started_at + timedelta(milliseconds=duration_ms)
    assert any("builds" in url for url in requested_urls)


@pytest.mark.parametrize(
    ("queue_id", "run_key", "match_kind"),
    [
        ("173", "another-run", "queue_id"),
        ("missing-queue", "duplicate-run", "run_id"),
    ],
)
def test_fetch_task_result_rejects_multiple_exact_build_matches(monkeypatch, queue_id, run_key, match_kind):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")

    def fake_urlopen(request, timeout):
        if request.full_url.endswith(f"/queue/item/{queue_id}/api/json"):
            raise HTTPError(request.full_url, 404, "Not Found", None, None)
        if "/job/AiApiTest-DWP-Module-Rerun/api/json?tree=builds" in request.full_url:
            return FakeJenkinsResponse(
                {
                    "builds": [
                        {
                            "number": 28,
                            "queueId": "173" if match_kind == "queue_id" else None,
                            "actions": [{"parameters": [{"name": "RUN_ID", "value": run_key}]}],
                        },
                        {
                            "number": 29,
                            "queueId": "173" if match_kind == "queue_id" else None,
                            "actions": [{"parameters": [{"name": "RUN_ID", "value": run_key}]}],
                        },
                    ]
                }
            )
        raise AssertionError(f"Unexpected Jenkins URL: {request.full_url}")

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=None,
        queue_id=queue_id,
        run=SimpleNamespace(run_key=run_key),
    )

    with pytest.raises(JenkinsBuildMatchError, match="Multiple Jenkins builds matched") as exc_info:
        fetch_jenkins_task_result(task)

    assert exc_info.value.match_kind == match_kind
    assert exc_info.value.match_value == ("173" if match_kind == "queue_id" else run_key)


@pytest.mark.parametrize("invalid_duration", [-1, "invalid", 10**30])
def test_fetch_task_result_does_not_invent_completion_time_for_invalid_duration(monkeypatch, invalid_duration):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    timestamp_ms = 1783840035760

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/api/json"):
            return FakeJenkinsResponse(
                {
                    "building": False,
                    "result": "SUCCESS",
                    "timestamp": timestamp_ms,
                    "duration": invalid_duration,
                }
            )
        if request.full_url.endswith("/summary.json"):
            return FakeJenkinsResponse({"status": "passed", "total_count": 1, "failed_count": 0})
        if request.full_url.endswith("/failed_nodeids.json"):
            return FakeJenkinsResponse([])
        raise AssertionError(f"Unexpected Jenkins URL: {request.full_url}")

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=12,
        queue_id="",
        run=SimpleNamespace(run_key="module-rerun-12-invalid-duration"),
    )

    result = fetch_jenkins_task_result(task)

    assert result["started_at"] == datetime.fromtimestamp(timestamp_ms / 1000, tz=datetime_timezone.utc)
    assert result["finished_at"] is None


def test_fetch_task_result_falls_back_to_exact_run_id_when_queue_id_is_not_in_build_metadata(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    run_key = "module_rerun-1-2-exact-run"

    def fake_urlopen(request, timeout):
        if request.full_url == "http://jenkins:8080/queue/item/172/api/json":
            raise HTTPError(request.full_url, 404, "Not Found", None, None)
        if "/job/AiApiTest-DWP-Module-Rerun/api/json?tree=builds" in request.full_url:
            return FakeJenkinsResponse(
                {
                    "builds": [
                        {
                            "number": 28,
                            "queueId": None,
                            "actions": [{"parameters": [{"name": "RUN_ID", "value": run_key}]}],
                        }
                    ]
                }
            )
        if request.full_url.endswith("/28/api/json"):
            return FakeJenkinsResponse({"building": True, "result": None, "timestamp": 1783840030759})
        raise AssertionError(f"Unexpected Jenkins URL: {request.full_url}")

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=None,
        queue_id="172",
        run=SimpleNamespace(run_key=run_key),
    )

    result = fetch_jenkins_task_result(task)

    assert result["build_number"] == 28
    assert result["building"] is True


def test_fetch_task_result_keeps_queue_pending_when_expired_queue_has_no_matching_build(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")

    def fake_urlopen(request, timeout):
        if request.full_url == "http://jenkins:8080/queue/item/404/api/json":
            raise HTTPError(request.full_url, 404, "Not Found", None, None)
        if "/job/AiApiTest-DWP-Module-Rerun/api/json?tree=builds" in request.full_url:
            return FakeJenkinsResponse({"builds": []})
        raise AssertionError(f"Unexpected Jenkins URL: {request.full_url}")

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(
        job_full_name="AiApiTest-DWP-Module-Rerun",
        build_number=None,
        queue_id="404",
        run=SimpleNamespace(run_key="missing-run"),
    )

    result = fetch_jenkins_task_result(task)

    assert result == {"queue_pending": True, "recovery_pending": True}


def test_cancel_task_sends_jenkins_crumb_for_authenticated_post(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setenv("JENKINS_USERNAME", "local-user")
    monkeypatch.setenv("JENKINS_API_TOKEN", "local-token")
    requested: list[tuple[str, str, str]] = []

    def fake_urlopen(request, timeout):
        requested.append((request.get_method(), request.full_url, request.headers.get("Jenkins-crumb", "")))
        if request.full_url == "http://jenkins:8080/crumbIssuer/api/json":
            return FakeJenkinsResponse({"crumbRequestField": "Jenkins-Crumb", "crumb": "crumb-123"})
        return FakeJenkinsResponse({})

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(job_full_name="AiApiTest-DWP-Failed-Rerun", build_number=9, queue_id="")

    cancel_jenkins_task(task)

    assert requested == [
        ("GET", "http://jenkins:8080/crumbIssuer/api/json", ""),
        ("POST", "http://jenkins:8080/job/AiApiTest-DWP-Failed-Rerun/9/stop", "crumb-123"),
    ]


def test_cancel_queued_task_sends_jenkins_crumb_for_authenticated_post(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setenv("JENKINS_USERNAME", "local-user")
    monkeypatch.setenv("JENKINS_API_TOKEN", "local-token")
    requested: list[tuple[str, str, str]] = []

    def fake_urlopen(request, timeout):
        requested.append((request.get_method(), request.full_url, request.headers.get("Jenkins-crumb", "")))
        if request.full_url == "http://jenkins:8080/crumbIssuer/api/json":
            return FakeJenkinsResponse({"crumbRequestField": "Jenkins-Crumb", "crumb": "crumb-123"})
        return FakeJenkinsResponse({})

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)
    task = SimpleNamespace(job_full_name="AiApiTest-DWP-Failed-Rerun", build_number=None, queue_id="99")

    cancel_jenkins_task(task)

    assert requested == [
        ("GET", "http://jenkins:8080/crumbIssuer/api/json", ""),
        ("POST", "http://jenkins:8080/queue/cancelItem?id=99", "crumb-123"),
    ]


def test_discover_jenkins_builds_reads_daily_jobs_and_build_tag_run_id(monkeypatch):
    monkeypatch.setenv("JENKINS_API_BASE_URL", "http://jenkins:8080")
    monkeypatch.setenv("JENKINS_PUBLIC_BASE_URL", "https://ci.example.test")
    requested_urls: list[str] = []

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        return FakeJenkinsResponse(
            {
                "builds": [
                    {
                        "number": 88,
                        "url": "http://jenkins:8080/job/AiApiTest-DWP-Daily-Full-Module/88/",
                        "result": "SUCCESS",
                        "building": False,
                        "timestamp": 1783252800000,
                        "actions": [{"parameters": [{"name": "TARGET_BASE_URL", "value": "https://qa.example.invalid/api"}]}],
                    },
                    {
                        "number": 77,
                        "url": "http://jenkins:8080/job/AiApiTest-DWP-Daily-Full-Module/77/",
                        "result": "SUCCESS",
                        "building": False,
                        "timestamp": 1783166400000,
                    },
                ]
            }
        )

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)

    result = discover_jenkins_builds(
        job_full_names=["AiApiTest-DWP-Daily-Full-Module"],
        date="2026-07-05",
    )

    assert requested_urls == [
        "http://jenkins:8080/job/AiApiTest-DWP-Daily-Full-Module/api/json?tree=builds[number,url,result,building,timestamp,actions[parameters[name,value]]]{0,50}"
    ]
    assert result == [
        {
            "job_full_name": "AiApiTest-DWP-Daily-Full-Module",
            "build_number": 88,
            "jenkins_build_url": "https://ci.example.test/job/AiApiTest-DWP-Daily-Full-Module/88/",
            "jenkins_result": "SUCCESS",
            "building": False,
            "run_id": "jenkins-AiApiTest-DWP-Daily-Full-Module-88",
            "target_base_url": "https://qa.example.invalid/api",
        }
    ]
