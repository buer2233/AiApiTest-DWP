# -*- coding: utf-8 -*-
"""config.json 统一配置入口的加载契约测试。

对齐 E9 参考框架（api-test-E9/tests/test_config_loading.py）：
- config.base_url 必须从 config.json 读取，且不硬编码任何 IP/域名兜底。
- 环境变量覆盖优先级高于 config.json。
- utils.common_function 必须从 api-test/config.json 按角色读取测试账号。

测试刻意不读取真实 config.json（内含真实账号），而是通过 monkeypatch
把 _ROOT_CONFIG 指向 tmp_path 下的临时文件，只验证「读取逻辑」，不验证「真实凭据值」。
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest


API_TEST_ROOT = Path(__file__).resolve().parents[1]


def load_config_module():
    """重新 exec config.py，返回与已导入模块隔离的独立副本。"""
    module_path = API_TEST_ROOT / "config.py"
    spec = importlib.util.spec_from_file_location("api_test_config_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(API_TEST_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(API_TEST_ROOT))
    return module


def load_common_function_module():
    """重新 exec common_function.py，返回独立副本以便 monkeypatch _ROOT_CONFIG。"""
    module_path = API_TEST_ROOT / "utils" / "common_function.py"
    spec = importlib.util.spec_from_file_location("common_function_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(API_TEST_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(API_TEST_ROOT))
    return module


def _clear_env_url(monkeypatch):
    """清除所有可能覆盖 base_url 的环境变量，让测试回到 config.json 优先路径。"""
    for key in ("E9_BASE_URL", "TARGET_BASE_URL"):
        monkeypatch.delenv(key, raising=False)


def test_missing_root_config_has_no_hard_coded_environment_fallback(monkeypatch, tmp_path):
    """缺少环境变量和 config.json 时，base_url 不得回退到硬编码 IP/域名。"""
    config = load_config_module()
    _clear_env_url(monkeypatch)
    monkeypatch.setattr(config, "_ROOT_CONFIG", tmp_path / "missing-config.json")

    assert config._load_root_base_url() == ""


def test_base_url_reads_from_root_config(monkeypatch, tmp_path):
    """config.json 存在时，base_url 应直接取自其中的 base_url 字段。"""
    config = load_config_module()
    _clear_env_url(monkeypatch)
    root_config = tmp_path / "config.json"
    root_config.write_text('{"base_url": "http://10.12.21.27:8080/"}', encoding="utf-8")
    monkeypatch.setattr(config, "_ROOT_CONFIG", root_config)

    # _load_root_base_url 原样返回 config.json 的 base_url（保留末尾斜杠），
    # 斜杠去除由 validate_base_url 统一负责。
    assert config._load_root_base_url() == "http://10.12.21.27:8080/"


def test_environment_url_overrides_root_config(monkeypatch, tmp_path):
    """环境变量 E9_BASE_URL 优先级必须高于 config.json。"""
    config = load_config_module()
    root_config = tmp_path / "config.json"
    root_config.write_text('{"base_url": "https://config.example"}', encoding="utf-8")
    monkeypatch.setattr(config, "_ROOT_CONFIG", root_config)
    monkeypatch.setenv("E9_BASE_URL", "https://ci.example")

    assert config._load_root_base_url() == "https://ci.example"


def test_target_base_url_environment_alias_overrides_root_config(monkeypatch, tmp_path):
    """TARGET_BASE_URL 作为 Jenkins 参数别名，优先级同样高于 config.json。"""
    config = load_config_module()
    root_config = tmp_path / "config.json"
    root_config.write_text('{"base_url": "https://config.example"}', encoding="utf-8")
    monkeypatch.setattr(config, "_ROOT_CONFIG", root_config)
    monkeypatch.delenv("E9_BASE_URL", raising=False)
    monkeypatch.setenv("TARGET_BASE_URL", "https://jenkins.example/e9")

    assert config._load_root_base_url() == "https://jenkins.example/e9"


def test_account_loader_uses_api_test_root_config():
    """common_function 的统一账号入口必须指向 api-test/config.json。"""
    common_function = load_common_function_module()

    assert common_function._ROOT_CONFIG == API_TEST_ROOT / "config.json"


def test_load_account_reads_role_from_root_config(monkeypatch, tmp_path):
    """无环境变量时，load_account 必须从 config.json 按角色读取账号。"""
    common_function = load_common_function_module()
    root_config = tmp_path / "config.json"
    root_config.write_text(
        json.dumps(
            {
                "admin": {"user_name": "cfg-admin", "password": "cfg-admin-pass"},
                "employee1": {"user_name": "cfg-emp1", "password": "cfg-emp1-pass"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(common_function, "_ROOT_CONFIG", root_config)
    for key in ("E9_ACCOUNTS_JSON", "E9_LOGINID", "E9_USERPASSWORD"):
        monkeypatch.delenv(key, raising=False)

    assert common_function.load_account("admin") == {
        "user_name": "cfg-admin",
        "password": "cfg-admin-pass",
    }


def test_environment_account_still_beats_root_config(monkeypatch, tmp_path):
    """CI 凭据环境变量优先级必须高于 config.json。"""
    common_function = load_common_function_module()
    root_config = tmp_path / "config.json"
    root_config.write_text(
        '{"admin": {"user_name": "cfg-admin", "password": "cfg-admin-pass"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(common_function, "_ROOT_CONFIG", root_config)
    monkeypatch.delenv("E9_ACCOUNTS_JSON", raising=False)
    monkeypatch.setenv("E9_LOGINID", "env-admin")
    monkeypatch.setenv("E9_USERPASSWORD", "env-pass")

    assert common_function.load_account("admin") == {
        "user_name": "env-admin",
        "password": "env-pass",
    }