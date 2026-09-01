# -*- coding: utf-8 -*-
"""E9 系统文档模块接口封装。"""

import allure

from page_api.public.base_api import BaseAPI


class SystemDocAPI(BaseAPI):
    """E9 系统文档接口。"""

    @allure.step("接口：我的文档列表")
    def get_my_doc_list(self, status_code=200, **kwargs):
        """获取当前用户的文档列表（getMyDocList）。

        后端实现 ``SystemDocAction.getMyDocList``，返回 ``docs[]`` 数组，
        元素含 ``docid`` / ``docTitle`` / ``docstatus`` 等，可用于场景法
        主流程的「查询命中」步骤（无需自建文档时复用环境已有 docid）。

        Returns:
            dict: 接口响应 JSON，含 ``msg``、``docs`` 列表与 ``api_status``。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-26
        # IsAI: True
        url = "/api/doc/mobile/systemDoc/getMyDocList"
        error_msg = kwargs.pop("error_msg", "获取我的文档列表")
        return self.get(
            url,
            status_code=status_code,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：我的文档目录列表")
    def get_my_category_list(self, status_code=200, **kwargs):
        """获取当前用户的文档目录列表（getMyCategoryList）。

        返回 ``categorys[]``（元素含 ``sid`` / ``sname`` / ``canCreateDoc``），
        用于文档 save 造数时取一个可创建文档的目录 seccategory。

        Returns:
            dict: 接口响应 JSON，含 ``categorys`` 列表。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-26
        # IsAI: True
        url = "/api/doc/mobile/systemDoc/getMyCategoryList"
        error_msg = kwargs.pop("error_msg", "获取我的文档目录列表")
        return self.get(
            url,
            status_code=status_code,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：文档可读性判定")
    def can_read_doc(self, doc_id, status_code=200, **kwargs):
        """判定当前用户对指定文档的可读性与密级权限（canReadDoc）。

        后端实现 ``SystemDocAction.canReadDoc`` → ``CanReadDocCmd.execute``：
        读取 docid，开启分级保护（isOpenClassification）时依次做密级篡改校验、
        密级权限判定（``hasResourceSeclevelRight``），无密级权限时把
        ``HrmClassifiedProtectionBiz.getResourceClassificationTip`` 返回的提示
        写入 ``secretMsg`` 字段（r349134 变更点透出位置）；未开启分级保护时
        直接走普通可读性判定（``canReader``）。

        Args:
            doc_id: 文档 id（后端参数 ``docid``）。
            status_code: 期望 HTTP 状态码，默认 200。

        Returns:
            dict: 接口响应 JSON，含 ``api_status``、``isHaveDoc``、``canReader``、
                ``hasRightForSecret`` 与可选 ``secretMsg``（仅分级保护开启且无密级权限时出现）。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-26
        # IsAI: True
        url = "/api/doc/mobile/systemDoc/canReadDoc"
        error_msg = kwargs.pop("error_msg", "文档可读性判定")
        params = {"docid": doc_id}
        return self.get(
            url,
            status_code=status_code,
            params=params,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：保存系统文档 Office 附件")
    def save_office(
        self,
        doc_id,
        imagefile_id,
        old_imagefile_id,
        back_to_doc=1,
        submit_big_version=0,
        status_code=200,
        **kwargs,
    ):
        """保存文档 Office 附件并触发服务端文件关联处理。"""
        # Author: Codex
        # Create Date: 2026-08-17
        # IsAI: True
        url = "/api/doc/mobile/systemDoc/saveOffice"
        error_msg = kwargs.pop("error_msg", "保存系统文档 Office 附件")
        form_data = {
            "id": str(doc_id),
            "imagefileid": str(imagefile_id),
            "oldimagefileid": str(old_imagefile_id),
            "backtodoc": str(back_to_doc),
            "submitbigversion": str(submit_big_version),
        }
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )
