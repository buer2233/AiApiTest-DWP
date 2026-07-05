from __future__ import annotations

import json
from types import SimpleNamespace

from metrics.jenkins_service import discover_jenkins_builds, fetch_jenkins_task_result, trigger_jenkins_build


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
    assert result["allure_report_url"].startswith("https://ci.example.test/")


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
                        "url": "http://jenkins:8080/job/AiApiTest-DWP-Daily-Full-Module-Species/88/",
                        "result": "SUCCESS",
                        "building": False,
                        "timestamp": 1783252800000,
                    },
                    {
                        "number": 77,
                        "url": "http://jenkins:8080/job/AiApiTest-DWP-Daily-Full-Module-Species/77/",
                        "result": "SUCCESS",
                        "building": False,
                        "timestamp": 1783166400000,
                    },
                ]
            }
        )

    monkeypatch.setattr("metrics.jenkins_service.urllib.request.urlopen", fake_urlopen)

    result = discover_jenkins_builds(
        job_full_names=["AiApiTest-DWP-Daily-Full-Module-Species"],
        date="2026-07-05",
    )

    assert requested_urls == [
        "http://jenkins:8080/job/AiApiTest-DWP-Daily-Full-Module-Species/api/json?tree=builds[number,url,result,building,timestamp]{0,50}"
    ]
    assert result == [
        {
            "job_full_name": "AiApiTest-DWP-Daily-Full-Module-Species",
            "build_number": 88,
            "jenkins_build_url": "https://ci.example.test/job/AiApiTest-DWP-Daily-Full-Module-Species/88/",
            "jenkins_result": "SUCCESS",
            "building": False,
            "run_id": "jenkins-AiApiTest-DWP-Daily-Full-Module-Species-88",
        }
    ]
