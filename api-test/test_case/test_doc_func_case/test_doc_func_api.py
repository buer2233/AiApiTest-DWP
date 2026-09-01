# -*- coding: utf-8 -*-
"""E9 文档功能（采知连）接口自动化用例。

覆盖 r349155 修复点：开启采知连非标后，文档/文件夹下载遇到无后缀附件文件
不再因 ``substring(0, -1)`` 崩溃提示「无下载文件」。

测试数据读取优先级：环境变量 > ``test_data/doc_func/doc_func_test_data.json``
（Git 管理的模块级数据基线，由 tools/prepare_doc_func_test_data.py 构建）。
"""

import json
import os
from pathlib import Path

import allure
import pytest

from page_api.doc_func_api.doc_func_api import DocFuncAPI

DOC_FUNC_TEST_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "test_data" / "doc_func" / "doc_func_test_data.json"
)


def _doc_func_test_data() -> dict:
    """读取 Git 管理的文档功能模块测试数据基线；缺失或损坏时返回空字典。"""
    try:
        payload = json.loads(DOC_FUNC_TEST_DATA_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _env_or_baseline(env_name: str, state_key: str, purpose: str) -> str:
    """读取可安全查询的测试数据（环境变量优先，其次数据基线文件）。

    docid / imagefileid 为数字主键，统一按字符串返回；缺失或格式无效时安全跳过。
    """
    # Author: WorkBuddy
    # Create Date: 2026-08-20
    # IsAI: True
    value = os.getenv(env_name, "").strip() or str(_doc_func_test_data().get(state_key) or "").strip()
    if not value:
        pytest.skip(f"未配置 r349155 可回收测试数据 {env_name}/test_data.doc_func.{state_key}（{purpose}）")
    if not value.isdigit() or int(value) <= 0:
        pytest.skip(f"r349155 测试数据 {env_name}/{state_key} 格式无效")
    return value


def _zip_response_summary(response: object) -> dict:
    """生成不含敏感字段的下载失败摘要。"""
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    return {
        "response_type": "dict",
        "code": response.get("code"),
        "has_imageFileIds": bool(response.get("imageFileIds")),
    }


@allure.epic("E9-接口自动化")
@allure.feature("E9 文档功能（采知连）接口")
@pytest.mark.r349155
class TestDocFuncGenerateDocZipAPI:
    """采知连文档下载接口测试（r349155 无后缀附件下载修复）。

    # Author: WorkBuddy
    # Create Date: 2026-08-20
    # IsAI: True
    """

    @allure.story("含无后缀附件的文档单文件下载")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_generate_doc_zip_noext_doc_by_docid(self, login_admin):
        """P0：勾选含无后缀附件的文档（docIds）下载，接口应返回成功且携带附件 id。

        这是 r349155 的核心修复点——修复前 getAllFiles 对无后缀文件名调用
        substring(0, lastIndexOf(".")) 会抛 StringIndexOutOfBoundsException，
        服务端返回 -1，前端提示「无下载文件」。

        # Author: WorkBuddy
        # Create Date: 2026-08-20
        # IsAI: True
        """
        doc_id = _env_or_baseline("E9_R349155_DOC_ID", "doc_id", "含无后缀附件的文档")
        api = login_admin.use(DocFuncAPI)

        with allure.step("1.按 docIds 触发单文件下载（含无后缀附件）"):
            response = api.generate_doc_zip(sec_category_ids="", doc_ids=doc_id)

        summary = _zip_response_summary(response)
        assert isinstance(response, dict), f"下载响应类型异常: {summary}"
        assert response.get("code") == 1, f"含无后缀附件下载失败: {summary}"
        assert response.get("imageFileIds"), f"下载成功但未返回附件 id: {summary}"

    @allure.story("含无后缀附件文档的文件夹压缩下载")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_generate_doc_zip_noext_doc_by_category(self, login_admin):
        """P1：勾选含无后缀附件文档所在目录（secCategoryIds）下载，压缩包应正常生成。

        走 generateDocZip 压缩包分支，内部同样调用 getAllFiles 处理附件文件名，
        验证文件夹模式下无后缀附件也不影响打包。

        # Author: WorkBuddy
        # Create Date: 2026-08-20
        # IsAI: True
        """
        sec_category_id = os.getenv("E9_R349155_SEC_CATEGORY_ID", "").strip() or str(
            _doc_func_test_data().get("sec_category_id") or ""
        ).strip()
        doc_id = _env_or_baseline("E9_R349155_DOC_ID", "doc_id", "含无后缀附件的文档")
        if not sec_category_id or not sec_category_id.isdigit():
            pytest.skip("未配置 r349155 测试目录 sec_category_id")
        api = login_admin.use(DocFuncAPI)

        with allure.step("1.按 secCategoryIds 触发文件夹压缩下载"):
            response = api.generate_doc_zip(sec_category_ids=sec_category_id, doc_ids=doc_id)

        summary = _zip_response_summary(response)
        assert isinstance(response, dict), f"文件夹下载响应类型异常: {summary}"
        assert response.get("code") == 1, f"文件夹压缩下载失败: {summary}"
        assert response.get("imageFileIds"), f"文件夹下载成功但未返回附件 id: {summary}"

    @allure.story("空选下载返回无下载文件提示")
    @allure.severity(allure.severity_level.NORMAL)
    def test_generate_doc_zip_empty_selection_is_rejected(self, login_admin):
        """P2：无目录无文档时下载，接口应返回 code=0 与「无下载文件」提示，不崩溃。"""
        api = login_admin.use(DocFuncAPI)

        with allure.step("1.空 secCategoryIds 与 docIds 触发下载"):
            response = api.generate_doc_zip(sec_category_ids="", doc_ids="")

        summary = _zip_response_summary(response)
        assert isinstance(response, dict), f"空选下载响应类型异常: {summary}"
        assert response.get("code") == 0, f"空选下载不应成功: {summary}"

    @allure.story("不存在的文档下载被拒绝")
    @allure.severity(allure.severity_level.NORMAL)
    def test_generate_doc_zip_nonexistent_doc_is_rejected(self, login_admin):
        """异常场景：不存在的 docId 不应返回成功下载结果。"""
        api = login_admin.use(DocFuncAPI)

        with allure.step("1.以不存在的 docId 触发下载"):
            response = api.generate_doc_zip(sec_category_ids="", doc_ids="999999999")

        summary = _zip_response_summary(response)
        assert isinstance(response, dict), f"不存在文档下载响应类型异常: {summary}"
        assert response.get("code") != 1, f"不存在的文档不应下载成功: {summary}"