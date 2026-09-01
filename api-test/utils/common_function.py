# -*- coding: utf-8 -*-
"""E9+AI接口自动化测试框架 — 公共方法模块。

本文件存放全框架通用的工具方法，例如读取测试账号、数据构造、通用断言等。
所有用例和接口封装类均可通过 `from utils.common_function import xxx` 引用。
"""

import json
import os
import re
from pathlib import Path

import pytest

# api-test/config.json（统一配置入口）：本地开发机从此读取测试账号，
# 无需把账号写死在代码里；CI 凭据由环境变量注入，优先级更高。
_ROOT_CONFIG = Path(__file__).resolve().parents[1] / "config.json"


def _environment_account(role: str) -> dict[str, str] | None:
    """按角色读取 Jenkins 注入的 E9 凭据；未配置时返回 ``None``。

    管理员沿用 ``E9_LOGINID/E9_USERPASSWORD``，普通成员使用
    ``E9_EMPLOYEE<n>_LOGINID/E9_EMPLOYEE<n>_PASSWORD``，避免所有角色误用同一
    个管理员账号。角色名只接受 employee1 到 employee5，防止把任意字符串拼接
    成环境变量名。
    """
    # Jenkins Secret Text 优先承载完整角色映射，避免为每个员工维护独立凭据绑定。
    secret_payload = os.getenv("E9_ACCOUNTS_JSON")
    if secret_payload:
        try:
            accounts = json.loads(secret_payload)
        except json.JSONDecodeError:
            pytest.fail("E9_ACCOUNTS_JSON 不是合法 JSON")
        account = accounts.get(role) if isinstance(accounts, dict) else None
        if not isinstance(account, dict) or not account.get("user_name") or not account.get("password"):
            pytest.fail(f"E9_ACCOUNTS_JSON 缺少角色 '{role}' 的完整凭据")
        return {"user_name": account["user_name"], "password": account["password"]}

    if role == "admin":
        login_key, password_key = "E9_LOGINID", "E9_USERPASSWORD"
    else:
        match = re.fullmatch(r"employee([1-5])", role)
        if not match:
            return None
        index = match.group(1)
        login_key = f"E9_EMPLOYEE{index}_LOGINID"
        password_key = f"E9_EMPLOYEE{index}_PASSWORD"

    loginid = os.getenv(login_key)
    password = os.getenv(password_key)
    if loginid or password:
        if not loginid or not password:
            pytest.fail(f"{login_key} 与 {password_key} 必须同时配置")
        return {"user_name": loginid, "password": password}
    return None

def _config_account(role: str) -> dict[str, str] | None:
    """从 api-test/config.json 读取指定角色账号；未配置时返回 ``None``。

    角色名沿用 config.json 顶层键：admin、employee1~employee5。
    账号或密码缺失（含空占位）时返回 None，交由调用方按角色语义处理，
    普通成员空凭据仍交由 login_employee fixture 跳过。
    """
    if not _ROOT_CONFIG.exists():
        return None
    try:
        cfg = json.loads(_ROOT_CONFIG.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    account = cfg.get(role) if isinstance(cfg, dict) else None
    if not isinstance(account, dict):
        return None
    if account.get("user_name") and account.get("password"):
        return {"user_name": account["user_name"], "password": account["password"]}
    return None


def load_account(role="admin"):
    """读取 E9 测试账号信息。

    优先级：
    1. Jenkins Secret Text 注入的 E9_ACCOUNTS_JSON 角色映射。
    2. CI 环境变量 E9_LOGINID / E9_USERPASSWORD 或员工角色变量。
    3. api-test/config.json 中指定 role 的账号（本地统一配置入口）。

    Args:
        role: 账号角色，默认 "admin"。可选 "employee1"、"employee2" 等。

    Returns:
        dict: 包含 user_name 和 password 的账号字典。
              例如 {"user_name": "admin_user", "password": "<管理员密码>"}

    Raises:
        pytest.fail: 凭据缺失时直接终止测试。
    """
    # CI 私有环境变量优先，避免本地账号文件残留，并按角色隔离账号。
    environment_account = _environment_account(role)
    if environment_account is not None:
        return environment_account

    # 开发机从 api-test/config.json 读取（统一配置入口，优先级高于账号文件）。
    config_account = _config_account(role)
    if config_account is not None:
        return config_account

    # 未配置任何凭据来源时：普通成员返回空凭据，交由 login_employee fixture
    # 静默跳过；管理员必须配置完整凭据，避免整次会话静默跳过。
    if role != "admin":
        return {"user_name": "", "password": ""}
    pytest.fail(
        f"缺少 '{role}' 账号凭据：请配置 E9 环境变量，"
        "或在 api-test/config.json 中填写账号信息"
    )

