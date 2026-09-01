# -*- coding: utf-8 -*-
"""E9 流程表单接口 r349134 自动化用例。

覆盖 r349134 功能用例清单中「流程表单」模块条目 FC-WF-0
（加载流程表单 loadForm 的 secretMsg 密级提示透出主流程）。

环境约束：当前环境分级保护未开启，loadForm 返回的 params 不含 secretMsg
（r349134 的 549160 密级提示分支不可达）。本用例按 SKILL 阶段 C 口径：
验证「造数（doCreateRequest）→ 加载流程表单（loadForm）」链路走通、
loadForm 返回表单参数结构；密级提示行为差异以 allure.attach 记录为信息性证据。
"""

import json

import allure
import pytest

from page_api.workflow_api.workflow_base_api import WorkflowAPI


@allure.epic("E9-接口自动化")
@allure.feature("E9 流程表单接口（r349134）")
@pytest.mark.r349134
class TestWorkflowFormR349134:
    """流程表单加载 loadForm 密级提示链路（FC-WF-0）。

    # Author: WorkBuddy
    # Create Date: 2026-08-26
    # IsAI: True
    """

    @allure.story("FC-WF-0 创建流程→加载流程表单项 secretMsg 透出主流程")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_fc_wf0_create_and_load_form(self, login_admin):
        """FC-WF-0：场景法核心主流程。

        多步链路：取可创建流程模板 → 构造必填 mainData → doCreateRequest 造数
        取 requestid → loadForm 加载该流程表单 → 断言返回表单参数结构。
        """
        api = login_admin.use(WorkflowAPI)

        with allure.step("1.获取可创建流程模板列表"):
            wf_list = api.get_create_workflow_list()
            assert isinstance(wf_list, list) and wf_list, f"无可创建流程模板: {wf_list}"
            template = wf_list[0]
            workflow_id = str(template.get("workflowId") or "")
            assert workflow_id, f"流程模板缺 workflowId: {template}"

        with allure.step("2.获取表单定义，提取必填字段构造 mainData"):
            info = api.get_create_workflow_request_info(workflow_id)
            assert isinstance(info, dict), f"表单定义类型异常: {type(info).__name__}"
            data = info.get("data") or {}
            records = (data.get("workflowMainTableInfo") or {}).get("requestRecords") or []
            fields = records[0].get("workflowRequestTableFields") if records else []
            main_data = []
            for f in fields:
                if not f.get("mand"):
                    continue
                field_name = f.get("fieldName")
                if field_name in ("requestname", "requestlevel", "messageType"):
                    # requestname 走 requestName 参数；系统保留字段不落 mainData
                    continue
                field_id = f.get("fieldId")
                html_type = f.get("fieldHtmlType")
                select_values = f.get("selectvalues") or []
                value = select_values[0] if select_values else ("自动化造数" if str(html_type) == "1" else "0")
                main_data.append(
                    {"fieldName": field_name, "fieldValue": value,
                     "fieldId": str(field_id), "fieldType": f.get("fieldType") or "1"}
                )

        with allure.step("3.doCreateRequest 创建流程，取 requestid"):
            resp = api.do_create_request(
                workflow_id, "r349134-流程表单自动化造数", main_data,
                other_params={"isnextflow": "1"},
            )
            assert isinstance(resp, dict), f"doCreateRequest 类型异常: {type(resp).__name__}"
            assert resp.get("code") == "SUCCESS", f"流程创建失败: {resp}"
            request_id = (resp.get("data") or {}).get("requestid")
            assert request_id, f"流程创建未返回 requestid: {resp}"

        with allure.step("4.loadForm 加载流程表单，返回表单参数结构"):
            form = api.load_form(request_id, workflow_id)
            assert isinstance(form, dict), f"loadForm 类型异常: {type(form).__name__}"
            params = form.get("params")
            assert isinstance(params, dict), f"loadForm 未返回表单参数 params: {form}"
            assert "currentUserid" in params, f"params 缺当前用户标识: {params}"

        allure.attach(
            json.dumps(
                {
                    "workflowId": workflow_id,
                    "requestid": request_id,
                    "has_secretMsg": "secretMsg" in (form.get("params") or {}),
                    "note": "当前环境分级保护未开启，params 不含 secretMsg;"
                            "r349134 的 549160 密级提示分支需环境中开启分级保护后方可达",
                },
                ensure_ascii=False,
            ),
            name="FC-WF-0 流程表单加载链路证据",
            attachment_type=allure.attachment_type.TEXT,
        )