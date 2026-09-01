# -*- coding: utf-8 -*-
"""E9 文档功能（采知连）接口封装。

本模块封装采知连文档上传/下载/删除相关接口，对应源码：
- ``com.api.customization.doc.controller.FuncController``（下载，@Path("/yd/doc/func")）
- ``com.api.doc.upload.web.FileUploadAction``（上传，@Path("/doc/upload")）
- ``com.api.doc.search.web.DocTableOperateAction``（删除，@Path("/doc/operate")）
"""
import allure

from page_api.public.base_api import BaseAPI


class DocFuncAPI(BaseAPI):
    """E9 文档功能（采知连）接口。"""

    @allure.step("接口：文档批量下载（单文件 / 文件夹压缩）")
    def generate_doc_zip(
        self,
        sec_category_ids="",
        doc_ids="",
        status_code=200,
        **kwargs,
    ):
        """触发采知连文档下载。

        对应 ``FuncController.generateDocZip``，支持两种模式：
        - 单文件模式：sec_category_ids 为空、doc_ids 非空且数量不超过配置上限，
          直接返回各附件编码后的 imageFileIds；
        - 文件夹压缩模式：sec_category_ids 非空（含下级目录）或超出单文件上限，
          服务端打包生成 zip 附件并返回其 imageFileId。

        响应为 JSON：成功 ``{"code": 1, "imageFileIds": "..."}``；
        无下载内容时 ``{"code": 0, "msg": "..."}``。

        Args:
            sec_category_ids: 逗号分隔的目录 id 列表（``secCategoryIds`` 表单字段）。
            doc_ids: 逗号分隔的文档 id 列表（``docIds`` 表单字段）。
            status_code: 期望的 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其它参数。

        Returns:
            dict: 接口响应的 JSON 字典。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-20
        # IsAI: True
        url = "/api/yd/doc/func/generateDocZip"
        error_msg = kwargs.pop("error_msg", "文档批量下载 generateDocZip")
        form_data = {
            "secCategoryIds": sec_category_ids,
            "docIds": doc_ids,
        }
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )