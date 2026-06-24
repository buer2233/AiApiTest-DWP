"""Jenkins 集成 API 路由模块。
本模块声明 Jenkins job、build、console log 和触发构建接口，统一挂载到 `/api/jenkins/`。
"""

from django.urls import path

from .views import (
    JenkinsBuildDetailView,
    JenkinsBuildsView,
    JenkinsConsoleView,
    JenkinsJobsView,
    JenkinsTriggerBuildView,
)


urlpatterns = [
    path("jobs/", JenkinsJobsView.as_view(), name="jenkins-jobs"),
    path("jobs/<str:job_name>/builds/", JenkinsBuildsView.as_view(), name="jenkins-builds"),
    path(
        "jobs/<str:job_name>/builds/<int:build_number>/",
        JenkinsBuildDetailView.as_view(),
        name="jenkins-build-detail",
    ),
    path(
        "jobs/<str:job_name>/builds/<int:build_number>/console/",
        JenkinsConsoleView.as_view(),
        name="jenkins-console",
    ),
    path(
        "jobs/<str:job_name>/build/",
        JenkinsTriggerBuildView.as_view(),
        name="jenkins-trigger-build",
    ),
]
