import pytest

import config


def pytest_addoption(parser):
    """注册 pytest 命令行参数。
    这些参数用于在不修改 config.py 的情况下覆盖运行环境配置，
    适合本地调试、CI 多环境执行或临时切换被测站点。
    """
    # --base-url 用于临时覆盖 config.base_url，常用于切换测试环境域名。
    parser.addoption("--base-url", action="store", default=None, help="override config.base_url")

    # --website-name 用于覆盖 Allure 报告中的网站/项目名称展示。
    parser.addoption("--website-name", action="store", default=None, help="override Allure epic website name")


@pytest.fixture(scope="session")
def base_url(request):
    """返回当前测试会话使用的 base_url。
    优先级：
    1. pytest 命令行传入的 --base-url。
    2. config.py 中配置的 base_url。
    返回前会调用 config.validate_base_url 校验 URL 必须包含协议和域名。
    """
    # pytest 命令行参数优先级高于配置文件，便于同一套用例在不同环境执行。
    return config.validate_base_url(request.config.getoption("--base-url") or config.base_url)


@pytest.fixture(scope="session")
def website_name(request, base_url):
    """返回 Allure 报告中使用的网站名称。
    优先级：
    1. pytest 命令行传入的 --website-name。
    2. config.py 中配置的 website_name。
    3. 从 base_url 中解析出的域名。
    """
    # base_url 作为兜底输入，保证未显式配置网站名称时仍能生成可读的报告标题。
    return config.get_website_name(request.config.getoption("--website-name"), base_url)
