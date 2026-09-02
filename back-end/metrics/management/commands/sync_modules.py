from __future__ import annotations

import os
from pathlib import Path

import yaml
from django.db import transaction
from django.core.management.base import BaseCommand, CommandError

from metrics.module_metadata import REQUIRED_MODULE_METADATA_FIELDS, package_module_yaml_path
from metrics.models import ModuleSnapshot, TestEnvironment, TestModule


class Command(BaseCommand):
    help = "从 api-test/utils/package_module.yaml 幂等同步模块元数据。"

    def add_arguments(self, parser):
        parser.add_argument("--source", dest="source", help="模块 YAML 路径；默认读取仓库内 api-test/utils/package_module.yaml。")
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help="停用 YAML 中已删除的模块，避免数据库保留历史模块。",
        )

    def handle(self, *args, **options):
        source = options.get("source") or os.getenv("PACKAGE_MODULE_YAML_PATH")
        source_path = Path(source) if source else package_module_yaml_path()
        if not source_path.exists():
            raise CommandError(f"package_module.yaml 不存在: {source_path}")

        raw_data = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw_data, dict):
            raise CommandError("package_module.yaml 顶层必须是对象。")
        if options.get("reconcile") and not raw_data:
            raise CommandError("package_module.yaml 模块清单不能为空，未执行 reconcile。")

        success = 0
        failed = 0
        seen_packages: set[str] = set()
        normalized_keys: set[str] = set()
        valid_entries: list[tuple[str, dict]] = []
        for raw_package_name, module_config in raw_data.items():
            package_name = str(raw_package_name).strip()
            if (
                not package_name
                or package_name in normalized_keys
                or package_name in {".", ".."}
                or "/" in package_name
                or "\\" in package_name
                or Path(package_name).is_absolute()
                or Path(package_name).drive
            ):
                raise CommandError("package_module.yaml 包名为空、重复或包含非法路径语义。")
            normalized_keys.add(package_name)
            missing_fields = [
                field_name
                for field_name in REQUIRED_MODULE_METADATA_FIELDS
                if not isinstance(module_config, dict) or not module_config.get(field_name)
            ]
            if missing_fields:
                failed += 1
                self.stdout.write(f"skip package={package_name} missing={','.join(missing_fields)}")
                continue
            seen_packages.add(package_name)
            valid_entries.append((package_name, module_config))

        if options.get("reconcile") and failed:
            raise CommandError("package_module.yaml 存在缺少必填字段的模块，未执行 reconcile。")

        with transaction.atomic():
            for package_name, module_config in valid_entries:
                module, _ = TestModule.objects.update_or_create(
                    package_name=package_name,
                    defaults={
                        "case_path": f"test_case/{package_name}",
                        "module_name": str(module_config["module_name"]),
                        "module_dev": str(module_config["module_dev"]),
                        "module_test": str(module_config["module_test"]),
                        "is_active": True,
                    },
                )
                # 同步配置后为每个启用环境建立空快照，使模块页立即展示 YAML 中的模块。
                for environment in TestEnvironment.objects.filter(is_active=True).only("id"):
                    ModuleSnapshot.objects.get_or_create(environment=environment, module=module)
                success += 1

            if options.get("reconcile"):
                TestModule.objects.exclude(package_name__in=seen_packages).filter(is_active=True).update(is_active=False)

        self.stdout.write(f"sync_modules success={success} failed={failed}")
