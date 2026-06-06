"""接口请求基类模块。

本模块提供 BaseAPI，作为所有 page_api 接口封装类的公共父类。
它统一处理 base_url 拼接、requests.Session 初始化、默认 headers/cookies/proxies、
HTTP 状态码断言、JSON 响应解析，以及接口用例中常用的多层数据取值能力。
"""

import config
import allure
import requests
from urllib.parse import urlparse
from utils.timeout_http_adapter import TimeoutHTTPAdapter


class BaseAPI:
    """接口封装层公共基类。

    业务接口类应继承该类，并通过 self.get/self.post/self.put/self.delete
    发送请求。这样可以复用统一的超时、代理、证书、断言和响应解析逻辑，
    避免在每个接口方法中重复创建 session 或手写状态码断言。
    """

    def __init__(
        self,
        base_url=None,
        headers=None,
        cookies=None,
        timeout=None,
        verify_ssl=None,
        proxies=None,
    ):
        """初始化接口请求上下文。
        Args:
            base_url: 被测系统基础地址；不传时使用 config.base_url。
            headers: 本接口类额外请求头，会与 config.default_headers 合并。
            cookies: 本接口类额外 cookies，会与 config.default_cookies 合并。
            timeout: 默认请求超时时间；不传时使用 config.timeout。
            verify_ssl: 是否校验 HTTPS 证书；不传时使用 config.verify_ssl。
            proxies: requests 代理配置；不传时使用 config.proxies。
        """
        # 校验并规范化 base_url，保证后续 URL 拼接时基础地址合法。
        self.base_url = config.validate_base_url(base_url or config.base_url)

        # 默认 headers/cookies 作为基础配置，调用方传入的值拥有更高优先级。
        self.headers = {**config.default_headers, **(headers or {})}
        self.cookies = {**config.default_cookies, **(cookies or {})}

        # timeout 支持按接口类覆盖；未覆盖时使用全局配置。
        self.timeout = timeout or config.timeout

        # verify_ssl 支持显式传 False，因此必须用 is None 判断是否采用配置默认值。
        self.verify_ssl = config.verify_ssl if verify_ssl is None else verify_ssl

        # proxies 允许显式传空字典关闭代理，因此使用 is not None 判断。
        self.proxies = proxies if proxies is not None else config.proxies

        # requests.Session 延迟初始化，只有真正发送请求时才创建。
        self.base_request = None

    @classmethod
    def http_timeout(
        cls,
        timeout=None,
        verify_ssl=None,
        headers=None,
        cookies=None,
        proxies=None,
    ):
        """创建带超时适配器的 requests.Session。
        Args:
            timeout: 默认请求超时时间。
            verify_ssl: 是否校验 HTTPS 证书。
            headers: 需要合并到 session 的请求头。
            cookies: 需要合并到 session 的 cookies。
            proxies: requests 代理配置。
        Returns:
            requests.Session: 已挂载 TimeoutHTTPAdapter 的 session。
        """
        # 创建 session 后挂载自定义适配器，统一处理超时、证书和异常日志。
        session = requests.Session()
        adapter = TimeoutHTTPAdapter(timeout=timeout or config.timeout, verify_ssl=verify_ssl)

        # 同时挂载 http/https，保证两种协议都走同一套请求增强逻辑。
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # 先写入全局默认 headers/cookies，再写入调用方传入值实现覆盖。
        session.headers.update(config.default_headers)
        session.headers.update(headers or {})
        session.cookies.update(config.default_cookies)
        session.cookies.update(cookies or {})

        # proxies 显式传入时优先使用；未传入时读取全局代理配置。
        if proxies is not None:
            session.proxies.update(proxies)
        elif config.proxies:
            session.proxies.update(config.proxies)
        return session

    def get_base_request(self):
        """获取当前接口类复用的 requests.Session。
        Returns:
            requests.Session: 当前 BaseAPI 实例持有的 session。
        """
        # session 采用懒加载，避免只实例化接口类但不发请求时创建无用连接对象。
        if self.base_request is None:
            self.base_request = self.http_timeout(
                timeout=self.timeout,
                verify_ssl=self.verify_ssl,
                headers=self.headers,
                cookies=self.cookies,
                proxies=self.proxies,
            )
        return self.base_request

    def build_url(self, path_or_url):
        """根据相对路径或完整 URL 构造最终请求 URL。
        Args:
            path_or_url: 接口相对路径，或已经包含协议和域名的完整 URL。
        Returns:
            str: 可直接用于 requests 请求的完整 URL。
        """
        # 如果传入的是完整 URL，直接返回，便于少量跨域或外部接口场景复用。
        parsed = urlparse(path_or_url)
        if parsed.scheme and parsed.netloc:
            return path_or_url

        # 相对路径场景下统一处理首尾斜杠，避免拼接出重复斜杠。
        base = self.base_url.rstrip("/")
        path = str(path_or_url).lstrip("/")
        return f"{base}/{path}" if path else base

    @allure.step("发送接口请求")
    def request(self, method, path_or_url, status_code=200, return_response=False, error_msg=None, **kwargs):
        """发送接口请求并统一断言 HTTP 状态码。
        Args:
            method: HTTP 方法，如 GET、POST、PUT、DELETE。
            path_or_url: 接口相对路径或完整 URL。
            status_code: 期望 HTTP 状态码，默认 200。
            return_response: 是否返回原始 Response；False 时默认返回 response.json()。
            error_msg: 断言失败或 JSON 解析失败时使用的中文错误说明。
            **kwargs: 传给 requests 的请求参数，如 params、json、data、headers 等。
        Returns:
            dict | list | requests.Response: 默认返回 JSON 解析结果；return_response=True 时返回原始响应。
        """
        # 统一在基类中构造完整 URL，接口方法只需传相对路径即可。
        url = self.build_url(path_or_url)

        # 通过复用 session 发送请求，继承统一 headers、cookies、timeout、proxies 等配置。
        response = self.get_base_request().request(method.upper(), url, **kwargs)

        # error_msg 可由接口方法传入，用于让失败日志更贴近业务接口含义。
        message = error_msg or f"接口<{url}>请求失败"

        # 接口方法层只断言 HTTP 状态码，业务 code 断言应放在 pytest 用例层处理。
        assert response.status_code == status_code, (
            f"{message},接口<{url}>报错-{response.status_code},"
            f"reason:{response.reason},text:{response.text}"
        )

        # 非 JSON、下载、重定向等特殊场景可要求返回原始 response。
        if return_response:
            return response
        try:
            # 默认返回 JSON 结果，方便用例直接基于响应数据做断言。
            return response.json()
        except ValueError as exc:
            # 接口声明应返回 JSON 但实际不是 JSON 时，抛出带响应文本的断言错误。
            raise AssertionError(f"{message},接口<{url}>返回不是合法 JSON,text:{response.text}") from exc

    def get(self, path_or_url, **kwargs):
        """发送 GET 请求。
        Args:
            path_or_url: 接口相对路径或完整 URL。
            **kwargs: 传给 request 的请求参数。
        Returns:
            dict | list | requests.Response: 默认返回 JSON 解析结果。
        """
        return self.request("GET", path_or_url, **kwargs)

    def post(self, path_or_url, **kwargs):
        """发送 POST 请求。
        Args:
            path_or_url: 接口相对路径或完整 URL。
            **kwargs: 传给 request 的请求参数。
        Returns:
            dict | list | requests.Response: 默认返回 JSON 解析结果。
        """
        return self.request("POST", path_or_url, **kwargs)

    def put(self, path_or_url, **kwargs):
        """发送 PUT 请求。
        Args:
            path_or_url: 接口相对路径或完整 URL。
            **kwargs: 传给 request 的请求参数。
        Returns:
            dict | list | requests.Response: 默认返回 JSON 解析结果。
        """
        return self.request("PUT", path_or_url, **kwargs)

    def delete(self, path_or_url, **kwargs):
        """发送 DELETE 请求。
        Args:
            path_or_url: 接口相对路径或完整 URL。
            **kwargs: 传给 request 的请求参数。
        Returns:
            dict | list | requests.Response: 默认返回 JSON 解析结果。
        """
        return self.request("DELETE", path_or_url, **kwargs)

    def get_value(self, data, list_key=None, **kwargs):
        """按路径从嵌套数据中取值。
        Args:
            data: 原始数据，通常为接口响应 JSON。
            list_key: 取值路径；可以是单个 key，也可以是 key/index 组成的列表。
            **kwargs: 可传入 msg 作为断言失败时的额外说明。
        Returns:
            Any: 按路径取出的目标值。
        Raises:
            AssertionError: 路径不存在或取值失败时抛出。
        """
        # 未传 list_key 时，默认按 ["data", "data"] 取值，兼容常见响应结构。
        keys = ["data", "data"] if list_key is None else list_key

        # 单个 key 自动转成列表，统一后续遍历逻辑。
        if not isinstance(keys, list):
            keys = [keys]

        # 保留原始数据和当前 key，便于失败时输出可定位的信息。
        original_data = data
        key = ""
        try:
            for key in keys:
                # key 可以是字典 key，也可以是列表 index，按调用方传入路径逐层取值。
                data = data[key]
            return data
        except Exception as exc:
            # 取值失败时抛 AssertionError，让 pytest 直接展示清晰失败原因。
            msg = f"数据{data}不存在取值'{key}'！原始数据:{original_data};"
            if kwargs.get("msg"):
                msg = f"{kwargs.get('msg')}:{msg}"
            raise AssertionError(msg) from exc
