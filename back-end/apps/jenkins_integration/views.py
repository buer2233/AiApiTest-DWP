"""Jenkins 集成 API 视图模块。
本模块提供 Jenkins job 查询、build 查询、console log 查询和参数化构建触发接口。
所有接口都要求平台登录态，真实 Jenkins 通信由 JenkinsClient 统一封装。
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import PlatformAccessPermission

from .client import JenkinsClient
from .models import JenkinsBuildRecord
from .serializers import TriggerBuildSerializer


def build_jenkins_client():
    """创建 Jenkins 客户端。
    Returns:
        JenkinsClient: 基于当前 settings 的 Jenkins API 客户端。
    """
    return JenkinsClient()


class JenkinsJobsView(APIView):
    """Jenkins job 列表查询接口。"""

    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request):
        """返回 Jenkins job 列表。
        Args:
            request: DRF 请求对象。
        Returns:
            Response: 包含 count 和 results 的 job 列表。
        """
        jobs = build_jenkins_client().list_jobs()
        return Response({"count": len(jobs), "results": jobs})


class JenkinsBuildsView(APIView):
    """Jenkins build 列表查询接口。"""

    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request, job_name):
        """返回指定 job 的 build 列表。
        Args:
            request: DRF 请求对象。
            job_name: Jenkins job 名称。
        Returns:
            Response: 包含 count 和 results 的 build 列表。
        """
        builds = build_jenkins_client().list_builds(job_name)
        return Response({"count": len(builds), "results": builds})


class JenkinsBuildDetailView(APIView):
    """Jenkins build 详情查询接口。"""

    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request, job_name, build_number):
        """返回指定 build 的核心状态。
        Args:
            request: DRF 请求对象。
            job_name: Jenkins job 名称。
            build_number: Jenkins build 编号。
        Returns:
            Response: Jenkins build 摘要字段。
        """
        return Response(build_jenkins_client().get_build(job_name, int(build_number)))


class JenkinsConsoleView(APIView):
    """Jenkins build 控制台日志查询接口。"""

    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request, job_name, build_number):
        """返回指定 build 的 consoleText。
        Args:
            request: DRF 请求对象。
            job_name: Jenkins job 名称。
            build_number: Jenkins build 编号。
        Returns:
            Response: job、build 编号和控制台文本。
        """
        console = build_jenkins_client().get_console_log(job_name, int(build_number))
        return Response(
            {
                "job_name": job_name,
                "build_number": int(build_number),
                "console": console,
            }
        )


class JenkinsTriggerBuildView(APIView):
    """Jenkins 参数化构建触发接口。"""

    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def post(self, request, job_name):
        """触发指定 Jenkins job。
        Args:
            request: DRF 请求对象，body 中包含测试执行参数。
            job_name: Jenkins job 名称。
        Returns:
            Response: Jenkins 入队结果和 job 名称。
        """
        serializer = TriggerBuildSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parameters = serializer.to_jenkins_parameters()

        # 触发 Jenkins 前先完成参数转换，确保后端、Jenkinsfile 和 api-test runner 契约一致。
        result = build_jenkins_client().trigger_build(job_name, parameters)
        JenkinsBuildRecord.objects.create(
            job_name=job_name,
            queue_status="queued" if result.get("queued") else "unknown",
            triggered_by=request.user,
            parameters=parameters,
        )
        return Response(
            {
                **result,
                "job_name": job_name,
            },
            status=status.HTTP_201_CREATED,
        )
