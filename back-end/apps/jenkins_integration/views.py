from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import PlatformAccessPermission

from .client import JenkinsClient
from .models import JenkinsBuildRecord
from .serializers import TriggerBuildSerializer


def build_jenkins_client():
    return JenkinsClient()


class JenkinsJobsView(APIView):
    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request):
        jobs = build_jenkins_client().list_jobs()
        return Response({"count": len(jobs), "results": jobs})


class JenkinsBuildsView(APIView):
    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request, job_name):
        builds = build_jenkins_client().list_builds(job_name)
        return Response({"count": len(builds), "results": builds})


class JenkinsBuildDetailView(APIView):
    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request, job_name, build_number):
        return Response(build_jenkins_client().get_build(job_name, int(build_number)))


class JenkinsConsoleView(APIView):
    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request, job_name, build_number):
        console = build_jenkins_client().get_console_log(job_name, int(build_number))
        return Response(
            {
                "job_name": job_name,
                "build_number": int(build_number),
                "console": console,
            }
        )


class JenkinsTriggerBuildView(APIView):
    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def post(self, request, job_name):
        serializer = TriggerBuildSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parameters = serializer.to_jenkins_parameters()
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
