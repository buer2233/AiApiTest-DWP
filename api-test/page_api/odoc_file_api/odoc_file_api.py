# -*- coding: utf-8 -*-
"""E9 公文（odoc）文件模块接口封装。

本模块封装公文上传/密级确认相关接口，对应前端组件源码：
- ``src4js/pc4mobx/odoc/components/UploadFileComponent.js``
  - ``getSecretLevelInfo()`` 调用 ``POST /api/odoc/odocFile/selectSecLevel`` 获取密级选项
    与密级→保密期限映射（resourceValidityInfo）。
"""
import allure

from page_api.public.base_api import BaseAPI


class OdocFileAPI(BaseAPI):
    """E9 公文（odoc）文件接口。"""

    @allure.step("接口：查询公文密级选项与保密期限映射")
    def select_sec_level(self, status_code=200, **kwargs):
        """查询密级选项（resourceOptionList）与密级→保密期限映射。

        对应前端 ``UploadFileComponent.getSecretLevelInfo()``。r349137 前端改造
        将该接口返回的 ``resourceValidityInfo`` 由「数组下标取值」改为「按密级
        key 取值」，因此本接口返回的 ``resourceValidityInfo`` 必须是 map 结构
        （key=密级 key，value=保密期限字符串，可为空串）。

        Args:
            status_code: 期望的 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其它参数。

        Returns:
            dict: 接口响应的 JSON 字典，形如
                ``{"api_status": true, "isOpenClassification": true,
                   "resourceOptionInfo": {"resourceOptionList": [...],
                                          "resourceValidityInfo": {"1": "20年", ...}}}``
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-21
        # IsAI: True
        url = "/api/odoc/odocFile/selectSecLevel"
        error_msg = kwargs.pop("error_msg", "查询公文密级选项与保密期限映射")
        form_data = {}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )