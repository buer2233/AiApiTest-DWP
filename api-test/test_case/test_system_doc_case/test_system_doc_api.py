# -*- coding: utf-8 -*-
"""E9 系统文档接口自动化用例。"""

import os

import allure
import pytest

from page_api.system_doc_api.system_doc_api import SystemDocAPI


def _save_office_response_summary(response: object) -> dict[str, object]:
    """生成不含服务端字段值的保存接口失败摘要。"""
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    return {
        "response_type": "dict",
        "api_status": response.get("api_status") is True,
        "url_present": bool(response.get("url")),
    }


def _disposable_save_office_data() -> dict[str, int]:
    """读取经过人工确认、可安全写入的系统文档测试数据。"""
    field_names = {
        "doc_id": "E9_R349094_DOC_ID",
        "imagefile_id": "E9_R349094_IMAGE_FILE_ID",
        "old_imagefile_id": "E9_R349094_OLD_IMAGE_FILE_ID",
    }
    values = {field: os.getenv(environment_name, "").strip() for field, environment_name in field_names.items()}
    if not all(values.values()):
        pytest.skip("未配置 r349094 可回收文档与附件测试数据")
    if not all(value.isdigit() and int(value) > 0 for value in values.values()):
        pytest.skip("r349094 文档与附件测试数据格式无效")
    return {field: int(value) for field, value in values.items()}


@allure.epic("E9-接口自动化")
@allure.feature("E9 系统文档接口")
@pytest.mark.r349094
class TestSystemDocSaveOfficeAPI:
    """系统文档 Office 保存接口测试。

    # Author: Codex
    # Create Date: 2026-08-17
    # IsAI: True
    """

    @allure.story("保存 Office 附件后保持文档附件关联")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_save_office_copies_document_files(self, login_admin):
        """验证 r349094 保存 Office 附件后的成功响应。

        # Author: Codex
        # Create Date: 2026-08-17
        # IsAI: True
        """
        data = _disposable_save_office_data()
        api = login_admin.use(SystemDocAPI)

        with allure.step("保存人工确认的可回收文档附件"):
            response = api.save_office(**data)

        summary = _save_office_response_summary(response)
        assert isinstance(response, dict), f"保存 Office 附件响应类型异常: {summary}"
        assert response.get("api_status") is True, f"保存 Office 附件失败: {summary}"
        assert response.get("url"), f"保存 Office 附件未返回文档地址: {summary}"
