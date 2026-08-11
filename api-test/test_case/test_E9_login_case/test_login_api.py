# -*- coding: utf-8 -*-
"""E9 登录链路接口自动化用例。"""

import json
import os
from pathlib import Path

import allure
import pytest

from page_api.E9.login_api.login_api import LoginAPI


ACCOUNT_FILE = Path(__file__).parents[2] / "page_api" / "E9" / "login_api" / "account.json"


def load_account():
    """优先读取 CI 私有环境变量，开发机才回退到忽略的本地账号文件。"""
    env_loginid = os.getenv("E9_LOGINID")
    env_password = os.getenv("E9_USERPASSWORD")
    if env_loginid or env_password:
        if not env_loginid or not env_password:
            pytest.fail("E9_LOGINID 与 E9_USERPASSWORD 必须同时配置")
        return {"loginid": env_loginid, "userpassword": env_password}

    if not ACCOUNT_FILE.exists():
        pytest.fail(
            "缺少 E9 私有凭据：请配置 E9_LOGINID/E9_USERPASSWORD，"
            "或在本地提供被 .gitignore 忽略的 account.json"
        )
    with ACCOUNT_FILE.open(encoding="utf-8") as account_file:
        return json.load(account_file)


def _safe_login_fields(response):
    """只保留登录响应中的非敏感诊断字段，避免 token 进入报告。"""
    return {field: response.get(field) for field in ("msgcode", "loginstatus", "userid")}


@allure.epic("E9-接口自动化")
@allure.feature("E9 登录接口")
class TestE9LoginAPI:
    """E9 登录及登录态校验接口测试。"""

    def setup_method(self):
        self.account = load_account()

    @allure.story("账号密码登录并校验登录态")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_login_and_get_os_info(self, base_url):
        """按真实抓包顺序完成登录，并断言登录后系统配置响应。"""
        api = LoginAPI(base_url=base_url)

        with allure.step("1.获取 RSA 登录配置"):
            rsa_response = api.get_rsa_info()
            assert rsa_response.get("rsa_flag") == "``RSA``", f"RSA 标识异常:{rsa_response}"
            assert rsa_response.get("rsa_pub"), f"RSA 公钥为空:{rsa_response}"
            assert rsa_response.get("rsa_code"), f"RSA 编码为空:{rsa_response}"

        with allure.step("2.提交明文账号密码登录"):
            login_response = api.check_login(
                loginid=self.account["loginid"],
                userpassword=self.account["userpassword"],
            )
            assert login_response.get("msgcode") == "0", f"登录业务码异常:{_safe_login_fields(login_response)}"
            assert login_response.get("loginstatus") == "true", f"登录状态异常:{_safe_login_fields(login_response)}"
            assert login_response.get("userid") == 1, f"登录用户异常:{_safe_login_fields(login_response)}"

        with allure.step("3.确认登录提醒状态"):
            remind_response = api.remind_login()
            assert remind_response.get("status") == "1", f"登录提醒状态异常:{remind_response}"

        with allure.step("4.检查登录密码策略"):
            weak_password_response = api.is_weak_password(self.account["userpassword"])
            assert weak_password_response.get("isWeakPassword") is False, (
                f"密码弱口令状态异常:{weak_password_response}"
            )

        with allure.step("5.调用登录后系统信息接口"):
            os_info_response = api.get_os_info()

        with allure.step("6.断言登录后系统信息"):
            # 仅断言登录态生效的关键字段，避免因系统配置字段变更导致用例脆断。
            assert os_info_response.get("code") == 0, f"系统信息 code 异常:{os_info_response}"
            assert os_info_response.get("status") is True, f"系统信息 status 异常:{os_info_response}"
            assert os_info_response.get("resourceid") == 1, f"系统信息 resourceid 异常:{os_info_response}"
