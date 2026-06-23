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
