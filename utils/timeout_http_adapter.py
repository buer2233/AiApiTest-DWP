"""requests 超时适配器模块。
本模块提供 TimeoutHTTPAdapter，用于给接口自动化框架中的 requests.Session
统一挂载默认超时、SSL 校验、连接池配置和接口异常日志能力。
BaseAPI 会通过该适配器发送请求，从而避免每个接口方法重复处理超时和异常输出逻辑。
"""

import json
import time

from requests.adapters import HTTPAdapter
from requests.exceptions import ReadTimeout
from requests.models import Response

import config


class TimeoutHTTPAdapter(HTTPAdapter):
    """带默认超时、SSL 校验和异常日志能力的 requests HTTPAdapter。
    该适配器会被 BaseAPI 挂载到 requests.Session 上，用于统一控制：
    1. 每个接口请求的默认超时时间。
    2. HTTPS 证书校验开关。
    3. 连接池大小和阻塞策略。
    4. HTTP 状态异常、业务 code 异常、读取超时的日志输出。
    """

    def __init__(
        self,
        *args,
        timeout=None,
        verify_ssl=None,
        log_success=None,
        business_error_rules=None,
        **kwargs,
    ):
        """初始化 HTTP 适配器。
        Args:
            *args: 传给 requests.adapters.HTTPAdapter 的位置参数。
            timeout: 请求默认超时时间；不传时使用 config.timeout。
            verify_ssl: 是否校验 HTTPS 证书；不传时使用 config.verify_ssl。
            log_success: 是否打印成功请求日志；不传时使用 config.is_log_success。
            business_error_rules: 业务错误判断规则；不传时使用 config.business_error_rules。
            **kwargs: 传给 requests.adapters.HTTPAdapter 的其他关键字参数。
        """
        # 请求级别未显式传 timeout 时，统一使用配置文件中的默认超时时间。
        self.timeout = timeout or config.timeout

        # verify_ssl 支持显式传 False，因此需要用 is None 判断是否使用配置默认值。
        self.verify_ssl = config.verify_ssl if verify_ssl is None else verify_ssl

        # 成功日志默认关闭，避免大量接口用例输出过多日志。
        self.log_success = config.is_log_success if log_success is None else log_success

        # 业务错误规则用于识别 HTTP 200 但业务 code 异常的响应。
        self.business_error_rules = business_error_rules or config.business_error_rules

        # 设置连接池参数，提升多接口连续执行时的连接复用能力。
        super().__init__(*args, pool_connections=20, pool_maxsize=20, pool_block=True, **kwargs)

    def send(self, request, **kwargs):
        """发送 HTTP 请求，并在异常场景输出诊断日志。
        Args:
            request: requests 准备好的 PreparedRequest 对象。
            **kwargs: requests 传入的请求执行参数，如 timeout、verify、stream 等。
        Returns:
            Response: requests 响应对象；读取超时时会构造一个 status_code=500 的响应对象。
        """
        # 调用方没有单独指定 timeout 时，使用适配器默认超时时间。
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.timeout

        # 调用方没有单独指定 verify 时，使用适配器默认 SSL 校验配置。
        if kwargs.get("verify") is None:
            kwargs["verify"] = self.verify_ssl

        request_duration = 0
        try:
            # 记录请求耗时，便于异常日志和成功日志展示接口响应时间。
            start_time = time.time()
            response = super().send(request, **kwargs)
            request_duration = round(time.time() - start_time, 2)
        except ReadTimeout:
            # requests 读取超时时没有正常 Response，这里构造一个响应对象方便上层统一处理。
            response = Response()
            response.status_code = 500
            response.url = request.url
            message = (
                f"报错原因:接口:{request.url},响应超过:{self.timeout}秒,"
                f"发生问题客户端时间:{time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            response.reason = message
            response._content = message.encode("utf-8")
            self._print_exception_info(request, response, request_duration)
            return response

        # HTTP 错误或业务错误都打印详细异常信息，便于定位接口问题。
        if response.status_code >= 400 or self._is_business_error(response):
            self._print_exception_info(request, response, request_duration)
        elif self.log_success:
            # 成功日志默认由配置控制，开启后可用于观察接口请求耗时。
            print(f"--通过接口：--url:{request.url}; 响应时间：{request_duration}秒")

        return response

    def _is_business_error(self, response):
        """判断响应是否命中业务错误规则。
        Args:
            response: requests 响应对象。
        Returns:
            bool: True 表示 HTTP 状态正常但业务字段不符合成功规则。
        """
        # 未配置业务规则时，不做业务错误判断。
        if not self.business_error_rules:
            return False
        try:
            # 只有 JSON 响应才支持业务字段判断，非 JSON 响应直接跳过。
            response_data = response.json()
        except ValueError:
            return False

        # 业务规则只面向字典结构响应，列表或纯文本不参与判断。
        if not isinstance(response_data, dict):
            return False

        for field_name, rule in self.business_error_rules.items():
            # 响应中不存在该字段时，跳过当前规则，避免误判。
            if field_name not in response_data:
                continue
            success_values = rule.get("success_values", [])

            # 字段值不在成功值列表中，则认为当前响应存在业务错误。
            if response_data.get(field_name) not in success_values:
                return True
        return False

    def _print_exception_info(self, request, response, request_duration):
        """打印接口异常诊断信息。
        Args:
            request: 当前请求对象。
            response: 当前响应对象或超时时构造的响应对象。
            request_duration: 请求耗时，单位为秒。
        """
        # 输出请求 URL、请求体、响应内容、请求头和耗时，便于失败后快速排查。
        info = (
            f"\n--url:{request.url};"
            f"\n--headers:{dict(response.headers)};"
            f"\n--body:{self._safe_body(request)};"
            f"\n--response:{self._safe_response_text(response)};"
            f"\n--request.headers:{dict(request.headers)};"
            f"\n接口响应时间:{request_duration}秒"
        )
        print(f"\n--[接口异常信息开始]--{info}\n--[接口异常信息结束]--\n")

    @staticmethod
    def _safe_body(request):
        """安全读取请求体内容。
        Args:
            request: 当前请求对象。
        Returns:
            str: 可打印的请求体字符串。
        """
        # 没有请求体时返回空白字符串，避免日志中出现 None。
        body = getattr(request, "body", None)
        if body is None:
            return " "

        # bytes 请求体优先按 UTF-8 解码；解码失败时退回 str(body)。
        if isinstance(body, bytes):
            try:
                return body.decode("utf-8")
            except UnicodeDecodeError:
                return str(body)

        # dict/list 请求体转 JSON 字符串，ensure_ascii=False 保留中文可读性。
        if isinstance(body, (dict, list)):
            return json.dumps(body, ensure_ascii=False)

        # 其他类型统一转字符串，保证日志打印不抛异常。
        return str(body)

    @staticmethod
    def _safe_response_text(response):
        """安全读取响应文本。
        Args:
            response: 当前响应对象。
        Returns:
            str: 可打印的响应文本；读取失败时返回 response.reason。
        """
        try:
            return response.text
        except Exception:
            # 极少数情况下 response.text 读取失败，使用 reason 作为兜底信息。
            return response.reason
