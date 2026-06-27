from django.apps import AppConfig


class TestcasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.testcases"
    label = "testcases"
    verbose_name = "用例"
