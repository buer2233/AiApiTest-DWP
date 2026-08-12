# -*- coding: utf-8 -*-
"""test_case 层公共 fixture。

本文件定义的 fixture 供所有测试用例目录共享使用。
Fixture 通过 pytest 的 conftest 层级机制自动对子目录生效。

设计要点：
- 框架默认只请求一个 E9 环境（config.base_url），因此 fixture 直接使用
  config.base_url，无需通过 base_url fixture 传参。
- 如需覆盖 base_url，在用例中手动创建 LoginAPI(base_url="http://other") 即可。
- login_admin 和 login_employee 返回 APIContext 而非裸 LoginAPI 实例，
  通过 .use() 工厂方法可创建任意模块的 API 实例并共享登录 Session。
"""

import pytest
from typing import Callable

from page_api.login_api.login_api import LoginAPI
from page_api.public.api_context import APIContext
from utils.common_function import load_account


# ═══════════════════════════════════════════════════════════════════════════════
# 管理员自动登录 fixture（session 级别，自动执行）
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def login_admin():
    """自动登录管理员账号，整个测试会话只执行一次。

    所有用例默认受益于管理员已登录状态，无需在每个用例中重复
    调用登录接口。若管理员登录失败，整个会话直接终止（fail-fast）。

    返回 APIContext 而非裸 LoginAPI：
        - .login 属性 → 访问 LoginAPI 实例（如 .login.get_os_info()）
        - .use(SomeAPI) → 创建任意模块实例，自动共享登录 Session

    Returns:
        APIContext: 包装了已登录 Session 的 API 上下文，
                    作为所有模块接口的统一入口。
    """
    account = load_account("admin")
    api = LoginAPI()
    api._caller = account["user_name"]

    api.get_rsa_info()
    login_response = api.check_login(
        loginid=account["user_name"],
        userpassword=account["password"],
    )
    assert login_response.get("msgcode") == "0", (
        f"Admin 登录业务码异常: {LoginAPI.safe_login_fields(login_response)}"
    )
    assert login_response.get("loginstatus") == "true", (
        f"Admin 登录状态异常: {LoginAPI.safe_login_fields(login_response)}"
    )

    api.remind_login()
    api.is_weak_password(password=account["password"])
    api.get_os_info()

    return APIContext(api, caller=account["user_name"])


# ═══════════════════════════════════════════════════════════════════════════════
# 员工按需登录 fixture（session 级别工厂模式，非自动执行）
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def login_employee() -> Callable[[str], APIContext]:
    """返回一个工厂函数，按需登录任意员工账号（非自动执行）。

    设计思路：
        session 级别的 fixture 只能执行一次，但我们需要在同一个 session
        内登录多个不同员工。解决方案是"工厂模式"——fixture 返回的不是
        登录结果，而是一个可多次调用的工厂函数。

        工厂函数内部自行维护缓存字典：
        - 首次调用 login_employee("employee1") → 登录 → 缓存
        - 再次调用 login_employee("employee1") → 命中缓存，直接返回
        - 调用 login_employee("employee2")   → 新角色，登录 → 缓存

    返回 APIContext 而非裸 LoginAPI：
        - .login 属性 → 访问该员工的 LoginAPI 实例
        - .use(SomeAPI) → 创建任意模块实例，自动共享该员工的登录 Session

    用法:
        from page_api.announce_api.announce_api import AnnounceAPI

        def test_approval_flow(login_admin, login_employee):
            # 管理员自动注入（APIContext）
            admin_api = login_admin

            # 按需登录员工——需要几个就调几个，同一员工自动缓存
            emp1 = login_employee("employee1")  # 返回 APIContext
            emp2 = login_employee("employee2")

            # 通过 .use() 创建任意模块实例，共享登录态
            admin_api.use(AnnounceAPI).get_announce_list()
            emp1.use(AnnounceAPI).get_announce_list()

    Args:
        role: 账号角色名，对应 account.json 中的 key，
              如 "employee1"、"employee2"。

    Returns:
        APIContext: 包装了该员工已登录 Session 的 API 上下文。
    """
    _sessions = {}

    def _login(role="employee1"):
        if role in _sessions:
            return _sessions[role]

        account = load_account(role)

        # 空凭据的账号静默跳过，避免阻塞其他用例
        if not account["user_name"] or not account["password"]:
            pytest.skip(f"账号 '{role}' 未配置凭据，跳过当前用例")

        api = LoginAPI()
        api._caller = account["user_name"]

        api.get_rsa_info()
        login_response = api.check_login(
            loginid=account["user_name"],
            userpassword=account["password"],
        )
        assert login_response.get("msgcode") == "0", (
            f"{role} 登录业务码异常: {LoginAPI.safe_login_fields(login_response)}"
        )
        assert login_response.get("loginstatus") == "true", (
            f"{role} 登录状态异常: {LoginAPI.safe_login_fields(login_response)}"
        )

        api.remind_login()
        api.is_weak_password(password=account["password"])
        api.get_os_info()

        ctx = APIContext(api)
        _sessions[role] = ctx
        return ctx

    return _login