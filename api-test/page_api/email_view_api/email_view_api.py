# -*- coding: utf-8 -*-
"""E9 邮件（email）查看模块接口封装。

对应后端 ``com.api.email.web.EmailViewAction``（类级 ``@Path("/email/view")``），
提供邮件查看权限判定、邮件查看、邮件正文获取等只读接口。

r349134（no.4956160 新增工作秘密的需求）在该 Action 的沙箱密级提示链路上
新增了兜底逻辑：
- ``hasMailViewRights``：``classificationRight == 0`` 时经
  ``getSandboxTipWhenNoClassificationRight`` 调用被修改的
  ``HrmClassifiedProtectionBiz.getResourceClassificationTip``，把沙箱无权限
  提示写入响应的 ``msg`` 字段；
- ``mailView``：``EmailViewService.mailView`` 内部在沙箱模式且密级为沙箱内部
  数据时，把提示写入 ``viewBean.classificationTip``；
- ``mailContentView``：``classificationRight == 0`` 时把提示写入
  ``classificationTip`` 字段。

本封装用于 r349134 沙箱工作秘密无权限提示链路的回归验证。
"""
import allure

from page_api.public.base_api import BaseAPI


class EmailViewAPI(BaseAPI):
    """E9 邮件（email）查看接口。

    对应后端 ``EmailViewAction``，类级 ``@Path("/email/view")``。
    """

    # ------------------------------通用方法----------------------------------

    @staticmethod
    def _permission_summary(response):
        """生成不含敏感字段的邮件权限响应摘要，供断言失败信息使用。"""
        if not isinstance(response, dict):
            return {"response_type": type(response).__name__}
        return {
            "status": response.get("status"),
            "viewRight": response.get("viewRight"),
            "classificationRight": response.get("classificationRight"),
            "classificationTamper": response.get("classificationTamper"),
            "has_msg": bool(response.get("msg")),
            "has_classificationTip": bool(response.get("classificationTip")),
        }

    # ------------------------------接口方法----------------------------------

    @allure.step("接口：判断当前用户是否有权限查看指定邮件")
    def has_mail_view_rights(self, mail_id=None, status_code=200, **kwargs):
        """判断当前用户是否有权限查看指定邮件（hasMailViewRights）。

        后端实现 ``EmailViewAction.hasMailViewRights``：读取请求参数 ``mailId``，
        经 ``EmailCommonUtils.hasMailViewRight`` 判定查看权限与密级权限；当
        ``classificationRight == 0`` 时调用
        ``getSandboxTipWhenNoClassificationRight``，若邮件密级属于沙箱内部数据，
        则把 ``HrmClassifiedProtectionBiz.getResourceClassificationTip`` 返回的
        提示写入响应 ``msg`` 字段（r349134 新增空值兜底后，密级 key 反查为空
        时返回多语言标签 549160 文案）。

        Args:
            mail_id: 邮件 id（后端参数 ``mailId``），必填；传 0/缺省用于边界探测。
            status_code: 期望的 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.get 的其它参数。

        Returns:
            dict: 接口响应的 JSON 字典，形如
                ``{"status": "1", "viewRight": 0|1,
                   "classificationRight": 0|1, "classificationTamper": 0|1,
                   "msg": "<沙箱无权限提示，仅无密级权限时出现>"}``
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/email/view/hasMailViewRights"
        error_msg = kwargs.pop("error_msg", "判断邮件查看权限")
        params = {"mailId": mail_id if mail_id is not None else 0}
        return self.get(
            url,
            status_code=status_code,
            params=params,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：获取邮件查看完整对象")
    def mail_view(self, mail_id=None, status_code=200, **kwargs):
        """获取邮件查看完整对象（mailView）。

        后端实现 ``EmailViewAction.mailView`` → ``EmailViewService.mailView``：
        读取请求参数 ``mailId``，有查看权限时返回 ``viewBean``；沙箱模式且邮件
        密级为沙箱内部数据时，把提示写入 ``viewBean.classificationTip``。
        密级无权限时返回 ``viewBean`` 中 viewRight/classificationRight 标识。

        Args:
            mail_id: 邮件 id（必填）；传 0/缺省用于边界探测。
            status_code: 期望的 HTTP 状态码，默认 200。

        Returns:
            dict: 接口响应 JSON，含 ``status`` 与可选的 ``viewBean``（含
                classificationTip / classification / classificationRight 等）。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/email/view/mailView"
        error_msg = kwargs.pop("error_msg", "获取邮件查看完整对象")
        params = {"mailId": mail_id if mail_id is not None else 0}
        return self.get(
            url,
            status_code=status_code,
            params=params,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：获取收件箱邮件列表")
    def all_list(self, status_code=200, **kwargs):
        """获取收件箱邮件列表（allList）。

        后端实现 ``EmailListAction.allList``（类级 ``@Path("/email/list")`` →
        ``@Path("/allList")``）→ ``EmailListService.getEmailList``，返回当前用户
        可查看的邮件列表（``MailResource`` canview=1）。

        Returns:
            dict: 接口响应 JSON，含 ``status`` 与邮件列表数据。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/email/list/allList"
        error_msg = kwargs.pop("error_msg", "获取收件箱邮件列表")
        return self.get(
            url,
            status_code=status_code,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：打开写信页（获取发信会话与表单初始化信息）")
    def email_add(self, status_code=200, **kwargs):
        """打开写信页，返回发信会话 UUID 与表单初始化信息（emailAdd）。

        后端实现 ``EmailAddAction.emailAdd``（类级 ``@Path("/email/add")`` →
        ``@Path("/emailAdd")``）：返回收件人/密级等初始化信息，并生成
        ``email_sendsessionUUid`` 用于后续 ``send`` 接口的防重校验。

        Returns:
            dict: 接口响应 JSON，含 ``status`` 与 ``email_sendsessionUUid``。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/email/add/emailAdd"
        error_msg = kwargs.pop("error_msg", "打开写信页获取发信会话")
        return self.get(
            url,
            status_code=status_code,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：发送内部邮件")
    def send(self, status_code=200, **kwargs):
        """发送邮件（内部邮件落库），返回 mailId（send）。

        后端实现 ``EmailBaseAction.send``（类级 ``@Path("/email/base")`` →
        ``@Path("/send")``）→ ``MailSend.sendMail``：写 ``MailResource`` 表并返回
        ``mailId``；内部邮件 ``isInternal=1`` 时密级由 ``classification`` 参数
        指定（机密1/秘密2/内部3/公开4），并需 ``sessionUUid`` 防重。

        Args:
            status_code: 期望的 HTTP 状态码，默认 200。
            **kwargs: 透传的表单参数，常用键：
                ``sessionUUid``、``isInternal``、``classification``、
                ``savesend``、``subject``、``mouldtext``、``internaltonew``、
                ``internalccnew``、``internalbccnew``、``savedraft``、
                ``priority``、``texttype``。

        Returns:
            dict: 接口响应 JSON，形如 ``{"status": "1", "isSend": "...",
                "mailId": <新邮件id>, "savedraft": "...", "mailaccid": ...}``
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/email/base/send"
        error_msg = kwargs.pop("error_msg", "发送内部邮件")
        form_data = {}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取邮件正文内容")
    def mail_content_view(self, mail_id=None, status_code=200, **kwargs):
        """获取邮件正文内容（mailContentView）。

        后端实现 ``EmailViewAction.mailContentView``：读取请求参数 ``mailId``，
        有查看权限且密级有权限时返回 ``mailContent``；当 ``classificationRight
        == 0`` 时经 ``getSandboxTipWhenNoClassificationRight`` 把沙箱无权限提示
        写入 ``classificationTip`` 字段（r349134 兜底文案链路）。

        Args:
            mail_id: 邮件 id（必填）；传 0/缺省用于边界探测。
            status_code: 期望的 HTTP 状态码，默认 200。

        Returns:
            dict: 接口响应 JSON，形如
                ``{"status": "1", "viewRight": 0|1, "classificationRight": 0|1,
                   "mailContent": "...", "classificationTip": "<可选沙箱提示>"}``
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/email/view/mailContentView"
        error_msg = kwargs.pop("error_msg", "获取邮件正文内容")
        params = {"mailId": mail_id if mail_id is not None else 0}
        return self.get(
            url,
            status_code=status_code,
            params=params,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )