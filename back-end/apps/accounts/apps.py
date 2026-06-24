"""accounts 应用配置模块。
本模块声明 Django 加载账户应用时使用的 AppConfig、应用路径和迁移标签。
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """账户应用配置。
    使用固定 label，保证自定义 User 模型迁移和 settings.AUTH_USER_MODEL 引用稳定。
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
