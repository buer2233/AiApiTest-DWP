"""test_runs 应用配置模块。
本模块声明测试任务应用的 Django AppConfig，用于加载任务、失败用例和报告相关模型。
"""

from django.apps import AppConfig


class TestRunsConfig(AppConfig):
    """测试任务应用配置。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.test_runs"

