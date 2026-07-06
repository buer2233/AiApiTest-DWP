"""按需安装 requirements.txt 中尚未满足的依赖。

Jenkins 每次构建都会复用 api-test 下的虚拟环境；本脚本先读取当前虚拟环境已安装包，
再和 requirements.txt 对比，只安装缺失或固定版本不一致的依赖，减少重复安装耗时。
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path


PACKAGE_NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
EXACT_VERSION_PATTERN = re.compile(r"^\s*[A-Za-z0-9_.-]+\s*==\s*([^;\s]+)")
NORMALIZE_PATTERN = re.compile(r"[-_.]+")
PLATFORM_MARKER_PATTERN = re.compile(
    r"""^platform_system\s*(==|!=)\s*['"]([^'"]+)['"]$""",
    re.IGNORECASE,
)


def normalize_package_name(name: str) -> str:
    """按 Python 包名规范做最小归一化，兼容 requests / Requests / requests_test。"""
    return NORMALIZE_PATTERN.sub("-", name).lower()


def _strip_inline_comment(line: str) -> str:
    """去除不在 URL 片段中的行内注释，满足当前 requirements.txt 的简单格式。"""
    return line.split(" #", 1)[0].strip()


def marker_applies(marker: str) -> bool:
    """判断简单环境 marker 是否适用于当前平台。

    当前 requirements.txt 只使用 `platform_system == "Windows"`。遇到未知 marker 时保守返回 True，
    交给 pip 自己处理，避免误跳过后续新增的合法依赖。
    """
    marker = marker.strip()
    match = PLATFORM_MARKER_PATTERN.match(marker)
    if not match:
        return True

    operator, expected_platform = match.groups()
    current_platform = platform.system()
    if operator == "==":
        return current_platform == expected_platform
    return current_platform != expected_platform


def parse_requirement_line(line: str) -> tuple[str, str, str | None] | None:
    """解析单行依赖，返回原始安装规格、归一化包名和固定版本。"""
    cleaned = _strip_inline_comment(line)
    if not cleaned or cleaned.startswith("#"):
        return None

    requirement_part, separator, marker = cleaned.partition(";")
    if separator and not marker_applies(marker):
        return None

    name_match = PACKAGE_NAME_PATTERN.match(requirement_part)
    if not name_match:
        return None

    version_match = EXACT_VERSION_PATTERN.match(requirement_part)
    expected_version = version_match.group(1).strip() if version_match else None
    return cleaned, normalize_package_name(name_match.group(1)), expected_version


def read_requirements(requirements_file: Path) -> list[tuple[str, str, str | None]]:
    """读取当前平台适用的 requirements 条目。"""
    return [
        parsed
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if (parsed := parse_requirement_line(line)) is not None
    ]


def get_installed_packages() -> dict[str, str]:
    """查询当前 Python 环境已安装包版本。"""
    command = [sys.executable, "-m", "pip", "list", "--format=json"]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(
            f"Failed to query installed Python packages with pip list: {detail}"
        ) from exc

    try:
        installed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("pip list returned invalid JSON; cannot compare requirements.") from exc

    return {
        normalize_package_name(package["name"]): package["version"]
        for package in installed
        if "name" in package and "version" in package
    }


def collect_missing_requirements(
    requirements_file: Path,
    installed_packages: dict[str, str],
) -> list[str]:
    """返回缺失或固定版本不一致的依赖安装规格。"""
    missing: list[str] = []
    for raw_requirement, package_name, expected_version in read_requirements(requirements_file):
        installed_version = installed_packages.get(package_name)
        if installed_version is None:
            missing.append(raw_requirement)
            continue
        if expected_version is not None and installed_version != expected_version:
            missing.append(raw_requirement)
    return missing


def install_missing_requirements(requirements_file: Path) -> list[str]:
    """只安装 requirements.txt 中当前环境未满足的依赖。"""
    missing = collect_missing_requirements(requirements_file, get_installed_packages())
    if not missing:
        print("All requirements already satisfied; skip pip install.")
        return []

    print("Installing missing requirements: " + ", ".join(missing))
    subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=True)
    return missing


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install only missing requirements.")
    parser.add_argument(
        "requirements_file",
        nargs="?",
        default="requirements.txt",
        type=Path,
        help="requirements.txt path, relative to current working directory by default",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    install_missing_requirements(args.requirements_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
