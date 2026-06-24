"""Jenkins HTTP 客户端模块。
本模块封装 Jenkins job、build、console log 查询和参数化构建触发能力。
凭据只从 Django settings 或测试注入的配置读取，仓库中不写死真实 Jenkins 信息。
"""

from dataclasses import dataclass
from urllib.parse import quote

import requests
from django.conf import settings


@dataclass(frozen=True)
class JenkinsConfig:
    """Jenkins 连接配置。
    使用不可变 dataclass 保存基础 URL、用户名、API Token 和默认 job 名称。
    """

    base_url: str
    username: str = ""
    api_token: str = ""
    default_job: str = ""

    @classmethod
    def from_settings(cls):
        """从 Django settings 构造 Jenkins 配置。
        Returns:
            JenkinsConfig: 当前运行环境中的 Jenkins 连接配置。
        """
        return cls(
            base_url=getattr(settings, "JENKINS_BASE_URL", ""),
            username=getattr(settings, "JENKINS_USERNAME", ""),
            api_token=getattr(settings, "JENKINS_API_TOKEN", ""),
            default_job=getattr(settings, "JENKINS_DEFAULT_JOB", ""),
        )


class JenkinsClient:
    """Jenkins API 客户端。
    该客户端使用 requests.Session 调用 Jenkins REST 接口，并支持测试中注入 fake session。
    """

    def __init__(self, config: JenkinsConfig | None = None, session=None):
        """初始化 Jenkins 客户端。
        Args:
            config: Jenkins 连接配置；不传时从 Django settings 读取。
            session: 可注入的 HTTP session，测试中用于替代真实网络请求。
        Raises:
            ValueError: Jenkins 基础 URL、用户名或 API Token 缺失。
        """
        self.config = config or JenkinsConfig.from_settings()
        if not self.config.base_url or not self.config.username or not self.config.api_token:
            raise ValueError("Jenkins configuration is incomplete")
        self.base_url = self.config.base_url.rstrip("/")
        self.session = session or requests.Session()
        # Jenkins API 使用 HTTP Basic Auth，用户名和 API Token 均来自环境配置。
        self.session.auth = (self.config.username, self.config.api_token)

    def list_jobs(self) -> list[dict]:
        """查询 Jenkins job 列表。
        Returns:
            list[dict]: Jenkins `/api/json` 返回的 jobs 数组。
        """
        response = self.session.get(f"{self.base_url}/api/json")
        response.raise_for_status()
        return response.json().get("jobs", [])

    def list_builds(self, job_name: str) -> list[dict]:
        """查询指定 job 的 build 列表。
        Args:
            job_name: Jenkins job 名称。
        Returns:
            list[dict]: Jenkins job API 返回的 builds 数组。
        """
        response = self.session.get(f"{self._job_url(job_name)}/api/json")
        response.raise_for_status()
        return response.json().get("builds", [])

    def get_build(self, job_name: str, build_number: int) -> dict:
        """查询单个 Jenkins build 摘要。
        Args:
            job_name: Jenkins job 名称。
            build_number: Jenkins build 编号。
        Returns:
            dict: 前端需要展示的 build 核心字段。
        """
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
        """查询单个 Jenkins build 的控制台日志。
        Args:
            job_name: Jenkins job 名称。
            build_number: Jenkins build 编号。
        Returns:
            str: Jenkins consoleText 原始文本。
        """
        response = self.session.get(f"{self._job_url(job_name)}/{int(build_number)}/consoleText")
        response.raise_for_status()
        return response.text

    def trigger_build(self, job_name: str, parameters: dict) -> dict:
        """触发 Jenkins 参数化构建。
        Args:
            job_name: Jenkins job 名称。
            parameters: 与 Jenkinsfile 参数一致的键值对。
        Returns:
            dict: 是否成功进入队列和 HTTP 状态码。
        """
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
        """构造 Jenkins job URL。
        Args:
            job_name: Jenkins job 名称。
        Returns:
            str: URL 编码后的 job API 根路径。
        """
        # job 名称可能包含空格、斜杠等字符，调用 Jenkins API 前必须 URL 编码。
        quoted_name = quote(str(job_name), safe="")
        return f"{self.base_url}/job/{quoted_name}"
