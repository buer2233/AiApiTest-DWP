import os
from urllib.parse import urlparse

# Allure 报告中展示的网站名称；为空时会从 base_url 自动解析域名。
website_name = ""

# 被测系统基础地址，必须包含协议和域名，例如：https://www.gbif.org
base_url = "https://www.gbif.org"

# 是否使用 curl_cffi 模拟浏览器 TLS 指纹（绕过 Cloudflare 等 WAF）。
# True: 使用 curl_cffi，需要安装 pip install curl_cffi
# False: 使用标准 requests 库
use_curl_cffi = True

# curl_cffi 模拟的浏览器指纹，可选值："chrome", "firefox", "safari", "edge" 等。
# 仅在 use_curl_cffi=True 时生效。
curl_impersonate = "chrome"

# requests 请求默认超时时间，单位为秒。
timeout = 30

# pytest-rerunfailures 失败重跑次数；0 表示不启用失败重跑。
reruns = 0

# 是否校验 HTTPS 证书；测试自签名证书环境可按需改为 False。
verify_ssl = True

# 默认请求头，会在 BaseAPI 初始化 session 时写入。
default_headers = {
    # 模拟常见浏览器 UA，降低部分站点因缺少 User-Agent 拒绝请求的概率。
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0"
}

# 默认 cookies；通用框架默认不放登录态，避免提交敏感信息。
# GBIF Cloudflare 验证 cookie（浏览器访问后获取）
default_cookies = {
    "cf_clearance": "kl9YjgOjP4.hhI6Byc_keITDHfQq3V2Si2ZTC407xIU-1781076102-1.2.1.1-_X_w9nRHqoW1LIAU.Q4eHYiQp8yKjRCxhSUiAH0sMxH.CG7KoI89LTx9IjvXw36DJ6wAuBpee3_vODlkRb7M7RvDQAe2dsrR76WaMG6yWOA_q3Mc7Mrxkq9PZ.DXvcenCCFBD9lMQW7ifKStxigSLtRLq3fANc1XuHJXxdTIcJw4kQZOBiY8mqAK_2YjDf2YclOsYAEvAzWd5WgoKFMo_KcjP9xk94mU62QSMp8GGCDLbDG43vHbqcB.bRbJxr58T3.ciIW2zL0DHUT9w0kiA1yQpnEFI9eN3UEHonIMoTBWCNZUdH6TYmKPomy2imcVjQjzsSZc6tYaIvhsXLV7_83lwEkt8ZGJszxVGfx8pRrWJqwqK4_1Q0gA3RMG37ljm6TpW1BmYjJIgvSTA9UGZqUIovK_caBFCGCTkwcxp5c"
}

# requests 代理配置；为空表示不走代理。
proxies = {}
# 如需走本地 7890 端口代理，可改为：
# proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

# 是否记录请求成功日志，具体日志行为由 utils 中的日志能力控制。
is_log_success = False

# 业务成功码规则，供需要业务断言或响应分析的工具复用。
business_error_rules = {
    "code": {
        # 响应 JSON 中 code 字段属于这些值时，可视为业务成功。
        "success_values": [0, 200],
    }
}

# 项目根目录，所有相对目录配置都基于当前 config.py 所在目录计算。
base_dir = os.path.dirname(os.path.abspath(__file__))

# pytest 接口用例目录。
test_case_dir = os.path.join(base_dir, "test_case")

# 测试数据目录，框架初始化时可为空，项目接入后按需补充。
test_data_dir = os.path.join(base_dir, "test_data")

# 报告根目录，Allure 原始结果和 HTML 报告都放在该目录下。
report_dir = os.path.join(base_dir, "report")

# Allure 原始结果目录，pytest 执行时通过 --alluredir 写入。
allure_results_dir = os.path.join(report_dir, "allure-results")

# Allure HTML 报告根目录；runpytest.py 会在其下按时间戳生成子目录。
allure_report_dir = os.path.join(report_dir, "allure-report")

# 运行时目录，用于存放抓包、选择结果等临时运行产物。
runtime_dir = os.path.join(base_dir, "runtime")

# 日志目录。
logs_dir = os.path.join(base_dir, "logs")

# 最近一次抓包数据文件路径。
latest_capture_path = os.path.join(runtime_dir, "latest.jsonl")

# 抓包接口选择结果文件路径。
capture_selection_path = os.path.join(runtime_dir, "capture_selection.md")


def validate_base_url(url=None):
    """校验并返回合法的 base_url。
    Args:
        url: 需要校验的 URL；不传时使用全局 base_url。
    Returns:
        str: 去除末尾斜杠后的 URL。
    Raises:
        ValueError: URL 缺少协议或域名时抛出。
    """
    # 未显式传入 URL 时，默认校验 config.py 中配置的 base_url。
    target = url or base_url

    # urlparse 用于拆分协议、域名、路径等部分，避免手写字符串判断。
    parsed = urlparse(target)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("base_url 必须包含协议和域名，例如：https://www.gbif.org")

    # 统一去掉末尾斜杠，避免后续拼接接口路径时出现重复斜杠。
    return target.rstrip("/")


def get_website_name(name=None, url=None):
    """获取 Allure 报告中展示的网站名称。
    Args:
        name: 外部传入的网站名称，优先级最高。
        url: 用于解析域名的 URL；不传时使用全局 base_url。
    Returns:
        str: 网站名称或从 URL 解析出的域名。
    """
    # 调用方显式传入名称时直接使用，通常来自 pytest --website-name。
    if name:
        return name

    # config.py 中配置了 website_name 时作为默认报告名称。
    if website_name:
        return website_name

    # 未配置名称时，从 base_url 解析域名作为兜底展示值。
    parsed = urlparse(validate_base_url(url))
    return parsed.netloc
