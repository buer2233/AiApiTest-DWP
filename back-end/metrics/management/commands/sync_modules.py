from __future__ import annotations

import os
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from metrics.models import TestModule


REQUIRED_FIELDS = ("module_name", "module_dev", "module_test")


class Command(BaseCommand):
    help = "从 api-test/utils/package_module.yaml 幂等同步模块元数据。"

    def add_arguments(self, parser):
        parser.add_argument("--source", dest="source", help="模块 YAML 路径；默认读取仓库内 api-test/utils/package_module.yaml。")

    def handle(self, *args, **options):
        source = options.get("source") or os.getenv("PACKAGE_MODULE_YAML_PATH")
        source_path = Path(source) if source else settings.REPO_ROOT / "api-test" / "utils" / "package_module.yaml"
        if not source_path.exists():
            raise CommandError(f"package_module.yaml 不存在: {source_path}")

        raw_data = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw_data, dict):
            raise CommandError("package_module.yaml 顶层必须是对象。")

        success = 0
        failed = 0
        for package_name, module_config in raw_data.items():
            missing_fields = [
                field_name
                for field_name in REQUIRED_FIELDS
                if not isinstance(module_config, dict) or not module_config.get(field_name)
            ]
            if missing_fields:
                failed += 1
                self.stdout.write(f"skip package={package_name} missing={','.join(missing_fields)}")
                continue

            TestModule.objects.update_or_create(
                package_name=str(package_name),
                defaults={
                    "case_path": f"test_case/{package_name}",
                    "module_name": str(module_config["module_name"]),
                    "module_dev": str(module_config["module_dev"]),
                    "module_test": str(module_config["module_test"]),
                    "is_active": True,
                },
            )
            success += 1

        self.stdout.write(f"sync_modules success={success} failed={failed}")
