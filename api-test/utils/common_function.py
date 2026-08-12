# -*- coding: utf-8 -*-
"""E9 接口自动化测试框架 — 公共方法模块。

本文件存放全框架通用的工具方法，例如读取测试账号、数据构造、通用断言等。
所有用例和接口封装类均可通过 `from utils.common_function import xxx` 引用。
"""

import json
import os
from pathlib import Path

import pytest

# 账号文件路径：test_data/account.json
ACCOUNT_FILE = Path(__file__).parents[1] / "test_data" / "account.json"


def load_account(role="admin"):
    """读取 E9 测试账号信息。

    优先级：
    1. CI 环境变量 E9_LOGINID / E9_USERPASSWORD（同时配置时使用）。
    2. 本地 test_data/account.json 中指定 role 的账号。

    Args:
        role: 账号角色，默认 "admin"。可选 "employee1"、"employee2" 等。

    Returns:
        dict: 包含 user_name 和 password 的账号字典。
              例如 {"user_name": "sysadmin", "password": "111aaa###"}

    Raises:
        pytest.fail: 凭据缺失时直接终止测试。
    """
    # CI 私有环境变量优先，避免本地账号文件残留。
    env_loginid = os.getenv("E9_LOGINID")
    env_password = os.getenv("E9_USERPASSWORD")
    if env_loginid or env_password:
        if not env_loginid or not env_password:
            pytest.fail("E9_LOGINID 与 E9_USERPASSWORD 必须同时配置")
        return {"user_name": env_loginid, "password": env_password}

    # 开发机回退到本地账号文件。
    if not ACCOUNT_FILE.exists():
        pytest.fail(
            "缺少 E9 私有凭据：请配置 E9_LOGINID/E9_USERPASSWORD，"
            "或在本地提供被 .gitignore 忽略的 test_data/account.json"
        )
    with ACCOUNT_FILE.open(encoding="utf-8") as account_file:
        accounts = json.load(account_file)

    if role not in accounts:
        pytest.fail(
            f"account.json 中不存在角色 '{role}'，"
            f"可用角色: {list(accounts.keys())}"
        )
    account = accounts[role]
    if not account.get("user_name") or not account.get("password"):
        pytest.fail(
            f"{role} 的账号或密码为空，请填写后重试！"
        )
    return account

