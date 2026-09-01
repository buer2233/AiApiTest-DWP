# -*- coding: utf-8 -*-
"""E9 公文（odoc）文件接口自动化用例。

覆盖 r349137 改动点：上传组件 ``UploadFileComponent.js`` 将密级→保密期限
映射 ``resourceValidityInfo`` 由「数组下标取值」改为「按密级 key 取值」，
并新增 ``isShowValidity`` 控制「保密期限」表单项显隐。该改动的正确性依赖
后端接口 ``POST /api/odoc/odocFile/selectSecLevel`` 返回的
``resourceValidityInfo`` 为 map 结构，本用例对该契约做针对性回归。

断言策略（遵循 SKILL 阶段 C）：环境部署版本未确认时，以结构化断言为通过
标准（成功标志 + 数据载荷存在）；行为级证据用 allure.attach 记录为信息性
附件，供环境部署后复核差异。
"""

import allure
import pytest

from page_api.odoc_file_api.odoc_file_api import OdocFileAPI


def _validity_summary(response: object) -> dict:
    """生成不含敏感字段的响应摘要，供断言失败信息使用。"""
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    option_info = response.get("resourceOptionInfo") or {}
    validity = option_info.get("resourceValidityInfo") if isinstance(option_info, dict) else None
    option_list = option_info.get("resourceOptionList") if isinstance(option_info, dict) else None
    return {
        "api_status": response.get("api_status"),
        "isOpenClassification": response.get("isOpenClassification"),
        "validity_type": type(validity).__name__,
        "validity_keys": list(validity.keys()) if isinstance(validity, dict) else None,
        "option_count": len(option_list) if isinstance(option_list, list) else None,
    }


@allure.epic("E9-接口自动化")
@allure.feature("E9 公文（odoc）文件接口")
@pytest.mark.r349137
class TestOdocFileSelectSecLevelAPI:
    """公文密级选项与保密期限映射接口测试（r349137 密级取值契约回归）。

    # Author: WorkBuddy
    # Create Date: 2026-08-21
    # IsAI: True
    """

    @allure.story("密级-保密期限映射返回 map 结构契约")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_select_sec_level_validity_map_contract(self, login_admin):
        """P0：selectSecLevel 返回的 resourceValidityInfo 必须是 map 结构，且能按密级 key 取值。

        这是 r349137 的核心契约点：改造前旧代码 ``Object.values(resourceValidityInfo)``
        把 map 转成数组再按下标取值，若密级顺序与数组下标不一致会导致保密期限错位；
        改造后直接 ``validityInfo[secretLevel]`` 按 key 取值。本用例断言后端返回的
        resourceValidityInfo 是字典（map）而非数组，且其 key 与 resourceOptionList
        的密级 key 存在对应关系，为前端新逻辑提供契约保障。
        """
        api = login_admin.use(OdocFileAPI)

        with allure.step("1.调用 selectSecLevel 查询密级选项与保密期限映射"):
            response = api.select_sec_level()

        summary = _validity_summary(response)
        assert isinstance(response, dict), f"selectSecLevel 响应类型异常: {summary}"
        assert response.get("api_status") is True, f"selectSecLevel 业务失败: {summary}"

        option_info = response.get("resourceOptionInfo")
        assert isinstance(option_info, dict), f"resourceOptionInfo 缺失或类型异常: {summary}"
        option_list = option_info.get("resourceOptionList")
        validity_info = option_info.get("resourceValidityInfo")
        assert isinstance(option_list, list) and option_list, f"resourceOptionList 缺失或为空: {summary}"

        # 核心断言：resourceValidityInfo 必须是 map（dict），键与每个密级 key 对应。
        assert isinstance(validity_info, dict), (
            f"resourceValidityInfo 应为 map 结构（r349137 前端按 key 取值依赖），"
            f"实际类型: {summary}"
        )

        # 契约对应关系：每个密级选项的 key 都应在 map 中存在；value 为保密期限字符串（可空）。
        option_keys = {str(item.get("key")) for item in option_list if isinstance(item, dict)}
        for key in option_keys:
            assert key in validity_info, (
                f"密级 key '{key}' 缺失于 resourceValidityInfo: {summary}"
            )
            assert isinstance(validity_info[key], str), (
                f"密级 key '{key}' 的保密期限应为字符串: {summary}"
            )

        # 行为级证据：密级 key 与保密期限值一一对应（环境部署后复核差异）。
        mapping = {k: validity_info[k] for k in sorted(validity_info)}
        allure.attach(
            str(mapping),
            name="resourceValidityInfo 密级-保密期限映射",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("密级选项列表与映射可正常返回")
    @allure.severity(allure.severity_level.NORMAL)
    def test_select_sec_level_returns_option_list(self, login_admin):
        """P1：selectSecLevel 应正常返回密级选项列表，且每项含 key 与 showname。"""
        api = login_admin.use(OdocFileAPI)

        with allure.step("1.调用 selectSecLevel 查询密级选项"):
            response = api.select_sec_level()

        summary = _validity_summary(response)
        assert isinstance(response, dict), f"selectSecLevel 响应类型异常: {summary}"
        assert response.get("api_status") is True, f"selectSecLevel 业务失败: {summary}"
        option_info = response.get("resourceOptionInfo") or {}
        option_list = option_info.get("resourceOptionList")
        assert isinstance(option_list, list) and option_list, f"密级选项列表缺失或为空: {summary}"
        for item in option_list:
            assert isinstance(item, dict), f"密级选项项类型异常: {summary}"
            assert item.get("key") is not None, f"密级选项缺少 key: {summary}"
            assert item.get("showname"), f"密级选项缺少 showname: {summary}"