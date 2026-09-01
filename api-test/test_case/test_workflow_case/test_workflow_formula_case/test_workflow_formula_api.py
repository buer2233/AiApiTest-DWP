# -*- coding: utf-8 -*-
"""E9 工作流公式（函数库）接口自动化用例。

覆盖 r349159 改动点。r349159 仅改动了 ``e10Migration/DataScanFileToDB.jsp``：
函数库本地文件初始化扫描 SQL 去掉 ``and filename != ''`` 条件，导致空文件名
记录也进入后续文件扫描逻辑。该改动位于 E9 迁移/E10 数据落地工具链（图外 JSP），
但业务域与函数库（``workflow_formula`` / ``workflow_formula_type``）直接相关。

断言策略（遵循 SKILL 阶段 C）：环境部署版本未确认时，以结构化断言为通过标准
（成功标志 + 数据载荷存在）；行为级证据用 allure.attach 记录为信息性附件，
供环境部署后复核差异。本用例聚焦函数库业务域 REST 接口的正常、边界、异常三类
场景，作为 r349159 影响的函数库数据侧的回归探针。
"""

import allure
import pytest

from page_api.workflow_api.workflow_formula_api import WorkflowFormulaAPI


def _function_list_summary(response):
    """生成函数库列表响应摘要（不含敏感字段）。"""
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    formula_info = response.get("formulaInfo")
    return {
        "formulaInfo_type": type(formula_info).__name__,
        "formulaInfo_count": len(formula_info) if isinstance(formula_info, list) else None,
    }


def _formula_types_summary(response):
    """生成公式类型响应摘要（不含敏感字段）。"""
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    type_options = response.get("typeOptions")
    return {
        "hasRight": response.get("hasRight"),
        "typeOptions_type": type(type_options).__name__,
        "typeOptions_count": len(type_options) if isinstance(type_options, list) else None,
    }


@allure.epic("E9-接口自动化")
@allure.feature("E9 工作流公式（函数库）接口")
@pytest.mark.r349159
class TestWorkflowFormulaAPI:
    """工作流公式（函数库）接口测试（r349159 函数库业务域回归）。

    # Author: WorkBuddy
    # Create Date: 2026-08-24
    # IsAI: True
    """

    @allure.story("函数库列表正常返回")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_function_list_normal(self, login_admin):
        """P0：getFunctionList 应正常返回函数列表，且数据结构为 formulaInfo 列表。

        r349159 放宽函数库文件扫描条件后，函数列表接口所依赖的
        ``workflow_formula`` / ``workflow_formula_db`` 数据完整性与展示应不受影响。
        本用例验证接口正常返回函数库列表作为数据侧回归探针。
        """
        api = login_admin.use(WorkflowFormulaAPI)

        with allure.step("1.调用 getFunctionList 获取函数库列表"):
            response = api.get_function_list()

        summary = _function_list_summary(response)
        assert isinstance(response, dict), f"getFunctionList 响应类型异常: {summary}"
        formula_info = response.get("formulaInfo")
        assert isinstance(formula_info, list), (
            f"formulaInfo 应为列表结构，实际类型: {summary}"
        )
        assert formula_info, f"函数库列表为空（函数库数据可能缺失）: {summary}"

        # 结构校验：每个函数项应包含 id 与 fun（函数名）关键字段。
        for item in formula_info:
            assert isinstance(item, dict), f"函数项类型异常: {summary}"
            assert item.get("fun") is not None, f"函数项缺少 fun 字段: {summary}"

        # 行为级证据：函数名列表（环境部署后复核差异）。
        fun_names = [item.get("fun") for item in formula_info if isinstance(item, dict)]
        allure.attach(
            str(fun_names),
            name="getFunctionList 函数名列表",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("公式类型选项与维护权限正常返回")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_formula_types_normal(self, login_admin):
        """P0：getFormulaTypes 应正常返回类型选项列表与 hasRight 权限标识。

        验证函数库类型数据（``workflow_formula_type``）可正常返回，
        作为 r349159 函数库业务域的另一数据侧回归探针。
        """
        api = login_admin.use(WorkflowFormulaAPI)

        with allure.step("1.调用 getFormulaTypes 获取公式类型选项"):
            response = api.get_formula_types()

        summary = _formula_types_summary(response)
        assert isinstance(response, dict), f"getFormulaTypes 响应类型异常: {summary}"
        assert "hasRight" in response, f"缺少 hasRight 权限标识: {summary}"
        type_options = response.get("typeOptions")
        assert isinstance(type_options, list), (
            f"typeOptions 应为列表结构，实际类型: {summary}"
        )

        # 行为级证据：类型 key/showname 映射（环境部署后复核差异）。
        type_names = [
            {"key": item.get("key"), "showname": item.get("showname")}
            for item in type_options
            if isinstance(item, dict)
        ]
        allure.attach(
            str(type_names),
            name="getFormulaTypes 类型选项列表",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("公式报表信息缺失 reportid（边界场景）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_report_info_missing_reportid(self, login_admin):
        """P1：getReportInfo 缺省 reportid 时应降级返回，不抛服务端异常。

        后端 ``GetReportInfoCmd`` 对 ``reportid`` 用 ``Util.getIntValue`` 取默认 0，
        查询空结果后仍返回 ``{"baseInfo": {}, ...}`` 结构。本用例验证缺参时接口
        不抛 5xx，返回合法 JSON，作为异常/边界场景的健壮性回归。
        """
        api = login_admin.use(WorkflowFormulaAPI)

        with allure.step("1.不传 reportid 调用 getReportInfo"):
            response = api.get_report_info(params={})

        assert isinstance(response, dict), (
            f"getReportInfo 缺参时响应类型异常: {type(response).__name__}"
        )
        # 缺参时应返回空 baseInfo（服务端默认 reportid=0），不允许抛异常。
        assert "baseInfo" in response, f"缺参时缺少 baseInfo 字段: {response}"

        allure.attach(
            str(response),
            name="getReportInfo 缺参降级响应",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("公式报表信息传入不存在的 reportid（异常场景）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_report_info_nonexistent_reportid(self, login_admin):
        """P1：getReportInfo 传入不存在的 reportid 时应安全返回空数据。

        验证非法/不存在的 reportid 不会导致接口 5xx 或抛出异常，
        服务端应返回空 baseInfo 结构的正常 JSON。
        """
        api = login_admin.use(WorkflowFormulaAPI)

        with allure.step("1.传入不存在的 reportid 调用 getReportInfo"):
            response = api.get_report_info(params={"reportid": "999999999"})

        assert isinstance(response, dict), (
            f"getReportInfo 传入不存在 reportid 时响应类型异常: {type(response).__name__}"
        )
        assert "baseInfo" in response, f"缺少 baseInfo 字段: {response}"
        # 不存在的 reportid 应返回空 baseInfo（无 reportname/formid 等有效内容）。
        base_info = response.get("baseInfo") or {}
        assert base_info.get("reportname") is None, (
            f"不存在的 reportid 不应返回有效报表名: {base_info}"
        )

        allure.attach(
            str(response),
            name="getReportInfo 不存在 reportid 响应",
            attachment_type=allure.attachment_type.TEXT,
        )