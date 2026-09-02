from __future__ import annotations

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from metrics.environment_catalog import (
    apply_yaml_catalog_import,
    git_blob_sha,
    initialize_environment_catalog_from_image,
    load_image_catalog,
)
from metrics.models import EnvironmentCatalogState


class Command(BaseCommand):
    help = "从随镜像复制的环境目录幂等初始化测试环境投影。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help="按镜像内环境 YAML 重投影已有环境并停用旧环境。",
        )

    def handle(self, *args, **options):
        source_path = settings.REPO_ROOT / "api-test" / "utils" / "package_environment.yaml"
        if options.get("reconcile"):
            with transaction.atomic():
                catalog = load_image_catalog(source_path)
                apply_yaml_catalog_import(catalog)
                state, _ = EnvironmentCatalogState.objects.get_or_create(
                    catalog_key=EnvironmentCatalogState.CATALOG_KEY
                )
                state.yaml_blob_sha = git_blob_sha(source_path.read_bytes())
                state.status = EnvironmentCatalogState.Status.SYNCED
                state.last_error_code = ""
                state.last_error_summary = ""
                state.save()
            action = "reconciled"
        else:
            initialized = initialize_environment_catalog_from_image(source_path)
            action = "initialized" if initialized else "skipped"
        self.stdout.write(f"seed_environment {action}")
