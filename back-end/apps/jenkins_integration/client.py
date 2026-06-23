from dataclasses import dataclass
from urllib.parse import quote

import requests
from django.conf import settings


@dataclass(frozen=True)
class JenkinsConfig:
    base_url: str
    username: str = ""
    api_token: str = ""
    default_job: str = ""

    @classmethod
    def from_settings(cls):
        return cls(
            base_url=getattr(settings, "JENKINS_BASE_URL", ""),
            username=getattr(settings, "JENKINS_USERNAME", ""),
            api_token=getattr(settings, "JENKINS_API_TOKEN", ""),
            default_job=getattr(settings, "JENKINS_DEFAULT_JOB", ""),
        )


class JenkinsClient:
    def __init__(self, config: JenkinsConfig | None = None, session=None):
        self.config = config or JenkinsConfig.from_settings()
        if not self.config.base_url or not self.config.username or not self.config.api_token:
            raise ValueError("Jenkins configuration is incomplete")
        self.base_url = self.config.base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.auth = (self.config.username, self.config.api_token)

    def list_jobs(self) -> list[dict]:
        response = self.session.get(f"{self.base_url}/api/json")
        response.raise_for_status()
        return response.json().get("jobs", [])

    def list_builds(self, job_name: str) -> list[dict]:
        response = self.session.get(f"{self._job_url(job_name)}/api/json")
        response.raise_for_status()
        return response.json().get("builds", [])

    def get_build(self, job_name: str, build_number: int) -> dict:
        response = self.session.get(f"{self._job_url(job_name)}/{int(build_number)}/api/json")
        response.raise_for_status()
        payload = response.json()
        return {
            "number": payload.get("number"),
            "building": payload.get("building"),
            "result": payload.get("result"),
            "url": payload.get("url"),
            "timestamp": payload.get("timestamp"),
            "duration": payload.get("duration"),
        }

    def get_console_log(self, job_name: str, build_number: int) -> str:
        response = self.session.get(f"{self._job_url(job_name)}/{int(build_number)}/consoleText")
        response.raise_for_status()
        return response.text

    def trigger_build(self, job_name: str, parameters: dict) -> dict:
        response = self.session.post(
            f"{self._job_url(job_name)}/buildWithParameters",
            data=parameters,
        )
        response.raise_for_status()
        return {
            "queued": response.status_code in {200, 201, 202},
            "status_code": response.status_code,
        }

    def _job_url(self, job_name: str) -> str:
        quoted_name = quote(str(job_name), safe="")
        return f"{self.base_url}/job/{quoted_name}"
