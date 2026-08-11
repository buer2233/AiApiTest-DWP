# -*- coding: utf-8 -*-
"""E9 登录相关接口封装。

接口字段和调用顺序依据 E9 真实 HAR 抓包整理；所有请求复用 BaseAPI 的
Session，以便自动接收并携带登录过程中由服务端下发的 Cookie。
"""

import time
from urllib.parse import urlparse

import allure

from page_api.public.base_api import BaseAPI


class LoginAPI(BaseAPI):
    """E9 人力登录及登录态校验接口。"""

    @staticmethod
    def _timestamp():
        """生成毫秒级时间戳，匹配抓包中的 ts/__random__ 参数格式。"""
        return time.time_ns() // 1_000_000

    def _browser_headers(self, *, form=False, origin=False, accept="*/*"):
        """按 HAR 约定构造可迁移的 Ajax 请求头。"""
        parsed_base_url = urlparse(self.base_url)
        origin_url = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"
        headers = {
            "Accept": accept,
            "Referer": f"{self.base_url.rstrip('/')}/wui/index.html",
            "X-Requested-With": "XMLHttpRequest",
        }
        if form:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"
        if origin:
            headers["Origin"] = origin_url
        return headers

    @allure.step("接口：获取 E9 RSA 登录配置")
    def get_rsa_info(self, status_code=200, ts=None, **kwargs):
        """获取 E9 登录页 RSA 配置。"""
        error_msg = kwargs.pop("error_msg", "获取 E9 RSA 登录配置")
        params = {"ts": self._timestamp() if ts is None else ts}
        params.update(kwargs)
        return self.get(
            "/rsa/weaver.rsa.GetRsaInfo",
            status_code=status_code,
            params=params,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：E9 账号密码登录")
    def check_login(self, loginid, userpassword, status_code=200, **kwargs):
        """提交 E9 登录表单。

        E9 当前抓包显示密码以明文表单字段传输；调用方应从本地私有账号文件
        读取，不得将账号或密码写入代码、日志或 Allure 附件。
        """
        error_msg = kwargs.pop("error_msg", "E9 账号密码登录")
        form_data = {
            "islanguid": "7",
            "loginid": loginid,
            "userpassword": userpassword,
            "dynamicPassword": "",
            "tokenAuthKey": "",
            "validatecode": "",
            "validateCodeKey": "",
            "logintype": "1",
            "messages": "",
            "isie": "false",
            "appid": "",
            "service": "",
            "isRememberPassword": "false",
        }
        form_data.update(kwargs)
        return self.post(
            "/api/hrm/login/checkLogin",
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：E9 登录提醒")
    def remind_login(self, status_code=200, **kwargs):
        """确认登录提醒状态。"""
        error_msg = kwargs.pop("error_msg", "E9 登录提醒")
        form_data = {"logintype": "1", "appid": "", "service": ""}
        form_data.update(kwargs)
        return self.post(
            "/api/hrm/login/remindLogin",
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：E9 检查弱密码")
    def is_weak_password(self, password, status_code=200, **kwargs):
        """检查登录密码是否为弱口令。"""
        error_msg = kwargs.pop("error_msg", "E9 检查弱密码")
        form_data = {"password": password}
        form_data.update(kwargs)
        return self.post(
            "/api/hrm/password/isWeakPassword",
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=False),
            error_msg=error_msg,
        )

    @allure.step("接口：获取 E9 登录后系统信息")
    def get_os_info(self, status_code=200, random_value=None, **kwargs):
        """获取登录后系统信息并携带动态随机参数。"""
        error_msg = kwargs.pop("error_msg", "获取 E9 登录后系统信息")
        params = {"__random__": self._timestamp() if random_value is None else random_value}
        params.update(kwargs)
        return self.get(
            "/api/system/info/getOSinfo",
            status_code=status_code,
            params=params,
            headers=self._browser_headers(form=True, origin=False),
            error_msg=error_msg,
        )
