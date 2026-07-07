from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import yaml
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


REQUIRED_MODULE_METADATA_FIELDS = ("module_name", "module_dev", "module_test")


def package_module_yaml_path() -> Path:
    """返回模块元数据 YAML 路径，默认使用仓库内相对位置，支持环境变量覆盖。"""
    source = os.getenv("PACKAGE_MODULE_YAML_PATH")
    return Path(source) if source else settings.REPO_ROOT / "api-test" / "utils" / "package_module.yaml"


def load_package_module_metadata(source_path: Path | None = None) -> dict[str, dict[str, str]]:
    """读取 package_module.yaml，并归一化为后端可直接使用的模块元数据。"""
    path = source_path or package_module_yaml_path()
    if not path.exists():
        raise ImproperlyConfigured(f"package_module.yaml 不存在: {path}")

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw_data, dict):
        raise ImproperlyConfigured("package_module.yaml 顶层必须是对象。")

    modules: dict[str, dict[str, str]] = {}
    for package_name, module_config in raw_data.items():
        if not isinstance(module_config, dict):
            continue
        normalized = {
            field_name: str(module_config.get(field_name, "")).strip()
            for field_name in REQUIRED_MODULE_METADATA_FIELDS
        }
        if any(not value for value in normalized.values()):
            continue
        modules[str(package_name).strip()] = {
            "package_name": str(package_name).strip(),
            "case_path": f"test_case/{str(package_name).strip()}",
            **normalized,
        }
    return modules


def build_filter_option_values(values: list[str]) -> list[dict[str, int | str]]:
    counts = Counter(value for value in values if value)
    return [
        {"label": value, "value": value, "count": count}
        for value, count in sorted(counts.items())
    ]


def build_filter_options_from_package_module_yaml() -> dict[str, list[dict[str, int | str]]]:
    modules = list(load_package_module_metadata().values())
    return {
        "module_names": build_filter_option_values([module["module_name"] for module in modules]),
        "package_names": build_filter_option_values([module["package_name"] for module in modules]),
        "module_devs": build_filter_option_values([module["module_dev"] for module in modules]),
        "module_tests": build_filter_option_values([module["module_test"] for module in modules]),
    }
