from __future__ import annotations

from django.core.management.base import BaseCommand
from django.conf import settings

from metrics.environment_catalog import initialize_environment_catalog_from_image


class Command(BaseCommand):
    help = "从随镜像复制的环境目录幂等初始化测试环境投影。"

    def handle(self, *args, **options):
        source_path = settings.REPO_ROOT / "api-test" / "utils" / "package_environment.yaml"
        initialized = initialize_environment_catalog_from_image(source_path)
        action = "initialized" if initialized else "skipped"
        self.stdout.write(f"seed_environment {action}")
