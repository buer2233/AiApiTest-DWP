"""对话式快速测试流程的安全配置辅助工具。"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


QUICK_TEST_TEMPLATE = """测试环境地址: XXX
管理员账号: XXX
管理员账号密码: XXX
普通成员一账号: XXX
普通成员一密码: XXX

可按需继续补充最多5个普通成员账号
"""
EMPLOYEE_LABELS = ("一", "二", "三", "四", "五")


class ConfigValidationError(ValueError):
    """校验失败时抛出，且不回显无效配置值。"""


@dataclass(frozen=True)
class ConfigInspection:
    valid: bool
    requires_template: bool
    source: str
    base_url: str
    admin_username: str
    employee_count: int
    errors: tuple[str, ...] = ()


def default_config_path() -> Path:
    """返回框架使用的工作区级共享配置路径（api-test/config.json）。"""
    return Path(__file__).resolve().parents[1] / "config.json"


def _empty_role() -> dict[str, str]:
    return {"user_name": "", "password": ""}


def _role_values(value: object) -> tuple[str, str]:
    if not isinstance(value, dict):
        return "", ""
    user_name = value.get("user_name", "")
    password = value.get("password", "")
    return (
        user_name.strip() if isinstance(user_name, str) else "",
        password if isinstance(password, str) else "",
    )


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _read_local_config(config_path: Path) -> dict[str, object]:
    try:
        raw = config_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _effective_config(
    local: Mapping[str, object], env: Mapping[str, str]
) -> tuple[dict[str, object], str]:
    data: dict[str, object] = dict(local)
    ci_used = False
    if env.get("E9_BASE_URL"):
        data["base_url"] = env["E9_BASE_URL"]
        ci_used = True
    login_id = env.get("E9_LOGINID", "")
    password = env.get("E9_USERPASSWORD", "")
    if login_id or password:
        data["admin"] = {"user_name": login_id, "password": password}
        ci_used = True
    for index in range(1, 6):
        user_key = f"E9_EMPLOYEE{index}_LOGINID"
        password_key = f"E9_EMPLOYEE{index}_PASSWORD"
        user_name = env.get(user_key, "")
        employee_password = env.get(password_key, "")
        if user_name or employee_password:
            data[f"employee{index}"] = {
                "user_name": user_name,
                "password": employee_password,
            }
            ci_used = True
    return data, "CI 环境变量" if ci_used else "本地配置"


def _inspect_mapping(data: Mapping[str, object], source: str) -> ConfigInspection:
    errors: list[str] = []
    base_url = data.get("base_url", "")
    base_url = base_url.strip() if isinstance(base_url, str) else ""
    if not _is_valid_url(base_url):
        errors.append("测试环境地址必须是合法的 http:// 或 https:// 地址")
    admin_username, admin_password = _role_values(data.get("admin"))
    if not admin_username or not admin_password:
        errors.append("管理员账号和密码必须完整填写")

    employee_count = 0
    for index in range(1, 6):
        user_name, password = _role_values(data.get(f"employee{index}"))
        if bool(user_name) != bool(password):
            errors.append(f"普通成员{index}的账号和密码必须成对填写")
        elif user_name:
            employee_count += 1
    return ConfigInspection(
        valid=not errors,
        requires_template=bool(errors),
        source=source,
        base_url=base_url,
        admin_username=admin_username,
        employee_count=employee_count,
        errors=tuple(errors),
    )


def inspect_config(
    config_path: Path | None = None, *, env: Mapping[str, str] | None = None
) -> ConfigInspection:
    """读取并校验配置，只返回可安全展示的字段。"""
    path = config_path or default_config_path()
    local = _read_local_config(path)
    effective, source = _effective_config(local, env if env is not None else os.environ)
    return _inspect_mapping(effective, source)


def format_summary(inspection: ConfigInspection) -> str:
    """渲染仅含白名单字段、可直接回复用户的配置摘要。"""
    if not inspection.valid:
        return "配置不完整或无效。请按固定模板填写后再继续。"
    source_suffix = "；本次执行实际使用 CI 环境变量" if inspection.source.startswith("CI") else ""
    return (
        f"已发现可用配置：测试环境 `{inspection.base_url}`，管理员 "
        f"`{inspection.admin_username}`，普通成员账号 {inspection.employee_count} 个"
        f"{source_suffix}。是否使用这些配置进行快速测试？"
    )


def _parse_template_lines(template_text: str) -> dict[str, str]:
    expected = {
        "测试环境地址": "base_url",
        "管理员账号": "admin_user_name",
        "管理员账号密码": "admin_password",
    }
    for index, label in enumerate(EMPLOYEE_LABELS, start=1):
        expected[f"普通成员{label}账号"] = f"employee{index}_user_name"
        expected[f"普通成员{label}密码"] = f"employee{index}_password"
    values = {key: "" for key in expected.values()}
    for line in template_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("可按需继续补充"):
            continue
        separator = ":" if ":" in stripped else "：" if "：" in stripped else None
        if separator is None:
            raise ConfigValidationError("模板格式不正确")
        label, value = (part.strip() for part in stripped.split(separator, 1))
        target = expected.get(label)
        if target is None:
            raise ConfigValidationError("模板包含不支持的字段")
        values[target] = value
    return values


def parse_template(template_text: str) -> dict[str, object]:
    """将固定模板转换为完整的含秘密配置映射。"""
    values = _parse_template_lines(template_text)
    data: dict[str, object] = {
        "base_url": values["base_url"],
        "admin": {
            "user_name": values["admin_user_name"],
            "password": values["admin_password"],
        },
    }
    for index in range(1, 6):
        data[f"employee{index}"] = {
            "user_name": values[f"employee{index}_user_name"],
            "password": values[f"employee{index}_password"],
        }
    return data


def write_config_from_template(config_path: Path, template_text: str) -> ConfigInspection:
    """校验后原子替换配置；出错时保持旧文件不变。"""
    data = parse_template(template_text)
    inspection = _inspect_mapping(data, "本地配置")
    if not inspection.valid:
        raise ConfigValidationError("配置校验失败，请检查地址和账号密码是否完整")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{config_path.name}.", suffix=".tmp", dir=config_path.parent, text=True
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_path, config_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return inspection


def main() -> int:
    parser = argparse.ArgumentParser(description="检查或原子写入快速测试配置。")
    parser.add_argument("action", choices=("inspect", "template", "write"))
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--input", type=Path, help="写入操作使用的模板文本文件。")
    args = parser.parse_args()
    if args.action == "template":
        print(QUICK_TEST_TEMPLATE, end="")
        return 0
    if args.action == "inspect":
        inspection = inspect_config(args.config)
        print(format_summary(inspection))
        return 0 if inspection.valid else 1
    if args.input is None:
        parser.error("write 操作必须提供 --input")
    try:
        inspection = write_config_from_template(args.config, args.input.read_text(encoding="utf-8"))
    except ConfigValidationError as exc:
        print(str(exc))
        return 1
    print(format_summary(inspection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
