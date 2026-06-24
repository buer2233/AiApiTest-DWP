"""jenkins_integration 应用配置模块。
本模块声明 Jenkins 集成应用的 Django AppConfig，用于加载 Jenkins API 和触发记录模型。
"""

from django.apps import AppConfig


class JenkinsIntegrationConfig(AppConfig):
    """Jenkins 集成应用配置。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jenkins_integration"

