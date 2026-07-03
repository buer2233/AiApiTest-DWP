from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "用户权限底座"

    def ready(self) -> None:
        # 导入 drf-spectacular 扩展，确保自定义 Cookie 鉴权能进入 OpenAPI securitySchemes。
        from accounts import schema  # noqa: F401
