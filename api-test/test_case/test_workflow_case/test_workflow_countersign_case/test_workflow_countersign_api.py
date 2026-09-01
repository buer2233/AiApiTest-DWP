# -*- coding: utf-8 -*-
"""E9 工作流会签审批接口用例 — 审批2 会签 + 审批3 审批流转。

覆盖功能测试用例的完整链路：
    ① 人员01 创建并提交 R1，R1 到审批2（人员02、人员03 会签待办）。
    ② 人员02 登录；【提交前列表校验】查人员02 待办应含 R1。人员02 提交 R1（会签 1/2）。
    ③ 【提交后列表校验】查人员02 已办应含 R1、待办不再含 R1；查人员03 待办仍含 R1；R1 仍在审批2。
    ④ 人员03 登录；【提交前列表校验】查人员03 待办应含 R1。人员03 提交 R1（会签 2/2）。
    ⑤ 【提交后列表校验】查人员03 已办应含 R1；R1 流转到审批3，查人员04、人员05 待办应含 R1。

运行期依赖（代码图谱仅含 Java 源码，不含流程实例/账号配置，故用环境变量优雅降级）：
    - 会签流程模板：优先 E9_CS_WORKFLOW_ID 直接指定 workflowId；其次 E9_CS_WORKFLOW_NAME
      关键字在「可创建流程列表」中动态匹配。两者都缺失则跳过用例。
    - 流程节点名关键字：E9_CS_NODE2_NAME（默认「审批2」）、E9_CS_NODE3_NAME（默认「审批3」），
      用于断言 R1 当前所处节点。
    - 主表数据：优先 E9_CS_MAINDATA（JSON 数组，形如 [{"fieldName":"xxx","fieldValue":"yyy"}]）；
      缺失时从 getCreateWorkflowRequestInfo 的表单定义自动构造（必填字段回填占位值）。
    - 角色账号 employee1~5 对应人员01~05；账号为空时 login_employee 自动 skip。
      （前提：环境中的会签流程模板，其审批2会签人=employee2+employee3，审批3审批人=employee4+employee5。）
"""

import json
import os

import allure
import pytest


# ── 运行期可配置项 ────────────────────────────────────────────────────────────
CS_WORKFLOW_ID = os.environ.get("E9_CS_WORKFLOW_ID", "").strip()
CS_WORKFLOW_NAME = os.environ.get("E9_CS_WORKFLOW_NAME", "").strip()
CS_NODE2_NAME = os.environ.get("E9_CS_NODE2_NAME", "审批2").strip()
CS_NODE3_NAME = os.environ.get("E9_CS_NODE3_NAME", "审批3").strip()
CS_MAINDATA = os.environ.get("E9_CS_MAINDATA", "").strip()

# 占位标题与占位字段值，仅用于创建可丢弃的自动化测试流程。
AUTO_TITLE = "autotest-countersign-r1"


def _pa_code(response):
    """把 PA 接口的 code 规范成字符串（兼容枚举名或 statusCode）。"""
    if not isinstance(response, dict):
        return str(response)
    code = response.get("code")
    if isinstance(code, dict):
        if code.get("name"):
            return str(code.get("name"))
        if code.get("statusCode") is not None:
            return str(code.get("statusCode"))
    return "" if code is None else str(code)


def _is_pa_success(response):
    """判断 PA 响应是否为 SUCCESS（兼容枚举名 / statusCode=1 / name=SUCCESS）。"""
    return _pa_code(response) in {"SUCCESS", "1"}


def _collect_request_ids(workflow_api, ec_api, scope):
    """按 viewScope（doing 待办 / done 已办）取当前账号流程列表的所有 requestId。"""
    if scope == "done":
        workflow_api.get_done_base_info()
        page_key = workflow_api.get_split_page_key(viewScope="done", actiontype="splitpage")
    else:
        workflow_api.get_doing_base_info()
        page_key = workflow_api.get_split_page_key()
    sessionkey = page_key.get("sessionkey") or ""
    assert sessionkey, f"分页 sessionkey 为空: {page_key}"
    table = ec_api.get_table_datas(data_key=sessionkey)
    ids = []
    for item in table.get("datas") or []:
        if not isinstance(item, dict):
            continue
        request_id = None
        for key in ("requestid", "requestId"):
            value = item.get(key)
            if value not in (None, "") and str(value).isdigit():
                request_id = int(value)
                break
        if request_id is None:
            for key, value in item.items():
                if "requestid" in str(key).lower() and str(value).isdigit():
                    request_id = int(value)
                    break
        if request_id is not None:
            ids.append(request_id)
    return ids


def _find_workflow_id(workflow_api):
    """动态定位会签流程模板 workflowId；找不到返回 None。"""
    if CS_WORKFLOW_ID.isdigit():
        return int(CS_WORKFLOW_ID)
    if not CS_WORKFLOW_NAME:
        return None
    wf_list = workflow_api.get_create_workflow_list()
    if isinstance(wf_list, dict):
        wf_list = wf_list.get("data") or wf_list.get("list") or []
    if not isinstance(wf_list, list):
        return None
    for item in wf_list:
        if not isinstance(item, dict):
            continue
        name = str(item.get("workflowName") or "")
        wid = item.get("workflowId")
        if name and CS_WORKFLOW_NAME in name and str(wid).isdigit():
            return int(wid)
    return None


def _build_main_data(workflow_api, workflow_id):
    """构造创建流程所需的 mainData 列表；返回 (main_data, source)。"""
    # 1. 显式指定的 mainData 优先。
    if CS_MAINDATA:
        try:
            data = json.loads(CS_MAINDATA)
            if isinstance(data, list):
                return data, "env"
        except json.JSONDecodeError:
            pass

    # 2. 从表单定义自动构造：必填字段回填占位值，其余跳过。
    info = workflow_api.get_create_workflow_request_info(workflow_id)
    data = info.get("data") if isinstance(info, dict) else None
    if not isinstance(data, dict):
        return [], "auto-empty"
    main_table = data.get("workflowMainTableInfo") or {}
    records = main_table.get("requestRecords") or []
    fields = []
    for record in records:
        if not isinstance(record, dict):
            continue
        fields.extend(record.get("workflowRequestTableFields") or [])
    main_data = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("fieldName")
        if not name:
            continue
        value = field.get("fieldValue")
        # 必填字段填占位值；非必填字段仅在已有默认值时带上。
        if field.get("isMand") is True:
            main_data.append({"fieldName": name, "fieldValue": value or "自动化"})
        elif value not in (None, ""):
            main_data.append({"fieldName": name, "fieldValue": value})
    return main_data, "auto"


@pytest.fixture(scope="class", autouse=True)
def _setup_class(login_admin, login_employee):
    """注入管理员 + 人员01~05 登录态（class 级别仅执行一次）。"""
    global workflow_api_admin
    global wf_emp1, ec_emp1
    global wf_emp2, ec_emp2
    global wf_emp3, ec_emp3
    global wf_emp4, ec_emp4
    global wf_emp5, ec_emp5

    workflow_api_admin = login_admin.workflow

    roles = {}
    for role, tag in (
        ("employee1", "emp1"),
        ("employee2", "emp2"),
        ("employee3", "emp3"),
        ("employee4", "emp4"),
        ("employee5", "emp5"),
    ):
        # 账号为空时 login_employee 内部会 pytest.skip，仅当账号存在才会继续。
        ctx = login_employee(role)
        roles[tag] = ctx

    wf_emp1, ec_emp1 = roles["emp1"].workflow, roles["emp1"].ec
    wf_emp2, ec_emp2 = roles["emp2"].workflow, roles["emp2"].ec
    wf_emp3, ec_emp3 = roles["emp3"].workflow, roles["emp3"].ec
    wf_emp4, ec_emp4 = roles["emp4"].workflow, roles["emp4"].ec
    wf_emp5, ec_emp5 = roles["emp5"].workflow, roles["emp5"].ec


@allure.epic("E9-接口自动化")
@allure.feature("E9 工作流会签审批接口")
class TestWorkflowCountersignAPI:
    """审批2 会签 + 审批3 审批流转端到端用例。

    Author: WorkBuddy
    Create Date: 2026-08-25
    IsAI: True
    """

    def setup_class(self):
        self.workflow_api_admin = workflow_api_admin
        self.wf_emp1, self.ec_emp1 = wf_emp1, ec_emp1
        self.wf_emp2, self.ec_emp2 = wf_emp2, ec_emp2
        self.wf_emp3, self.ec_emp3 = wf_emp3, ec_emp3
        self.wf_emp4, self.ec_emp4 = wf_emp4, ec_emp4
        self.wf_emp5, self.ec_emp5 = wf_emp5, ec_emp5

    @allure.story("审批2会签-多人会签集齐后流转审批3")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_approval2_countersign_flow(self):
        """端到端验证：审批2 两人会签，各提交一次后流转到审批3。

        步骤对应功能用例 ①~⑤；每步先做列表/状态校验再执行提交。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True

        # ── ① 人员01 创建并提交 R1，R1 到审批2 ──────────────────────────────
        workload_id = _find_workflow_id(self.wf_emp1)
        if workload_id is None:
            pytest.skip(
                "未定位到会签流程模板：请配置 E9_CS_WORKFLOW_ID 或 E9_CS_WORKFLOW_NAME。"
            )
        with allure.step(f"①-1 动态定位会签流程 workflowId={workload_id}"):
            assert workload_id > 0

        main_data, main_source = _build_main_data(self.wf_emp1, workload_id)
        with allure.step(f"①-2 构造创建流程主表数据（来源 {main_source}）"):
            pass

        with allure.step("①-3 人员01 创建并提交流程 R1"):
            create_resp = self.wf_emp1.do_create_request(
                workflow_id=workload_id,
                request_name=AUTO_TITLE,
                main_data=main_data,
                other_params={"isnextflow": "1"},
            )
            assert _is_pa_success(create_resp), (
                f"创建流程失败（请确认环境已部署会签流程模板且表单字段有效）: {create_resp}"
            )
            request_id = int((create_resp.get("data") or {}).get("requestid"))
            assert request_id > 0, f"创建流程未返回 requestid: {create_resp}"

        with allure.step("①-4 校验 R1 已流转到审批2"):
            status = self.wf_emp1.get_request_status(request_id)
            assert _is_pa_success(status), f"查询流程状态失败: {status}"
            node_name = str((status.get("data") or {}).get("currentNodeName") or "")
            assert CS_NODE2_NAME in node_name, (
                f"R1 应处于「{CS_NODE2_NAME}」，实际当前节点「{node_name}」: {status}"
            )

        # ── ② 人员02 提交 R1（会签 1/2） ────────────────────────────────────
        with allure.step(f"②-1 提交前校验：人员02 待办含 R1(requestId={request_id})"):
            emp2_doing = _collect_request_ids(self.wf_emp2, self.ec_emp2, "doing")
            assert request_id in emp2_doing, (
                f"人员02 待办应含 R1(requestId={request_id})，实际待办 {emp2_doing}"
            )

        with allure.step("②-2 人员02 提交 R1（会签 1/2）"):
            sub2 = self.wf_emp2.submit_request(
                request_id=request_id, other_params={"src": "submit"}
            )
            assert _is_pa_success(sub2), f"人员02 会签提交失败: {sub2}"

        # ── ③ 人员02 提交后列表校验 ──────────────────────────────────────────
        with allure.step("③-1 提交后：人员02 已办含 R1"):
            emp2_done = _collect_request_ids(self.wf_emp2, self.ec_emp2, "done")
            assert request_id in emp2_done, (
                f"人员02 已办应含 R1(requestId={request_id})，实际已办 {emp2_done}"
            )

        with allure.step("③-2 提交后：人员02 待办不再含 R1"):
            emp2_doing_after = _collect_request_ids(self.wf_emp2, self.ec_emp2, "doing")
            assert request_id not in emp2_doing_after, (
                f"人员02 提交后待办不应再含 R1(requestId={request_id})，实际待办 {emp2_doing_after}"
            )

        with allure.step("③-3 提交后：人员03 待办仍含 R1"):
            emp3_doing = _collect_request_ids(self.wf_emp3, self.ec_emp3, "doing")
            assert request_id in emp3_doing, (
                f"人员03 待办应仍含 R1(requestId={request_id})，实际待办 {emp3_doing}"
            )

        with allure.step("③-4 提交后：R1 仍在审批2"):
            status = self.wf_emp1.get_request_status(request_id)
            assert _is_pa_success(status), f"查询流程状态失败: {status}"
            node_name = str((status.get("data") or {}).get("currentNodeName") or "")
            assert CS_NODE2_NAME in node_name, (
                f"会签未集齐时 R1 应仍处于「{CS_NODE2_NAME}」，实际当前节点「{node_name}」: {status}"
            )

        # ── ④ 人员03 提交 R1（会签 2/2） ────────────────────────────────────
        with allure.step("④-1 提交前校验：人员03 待办含 R1"):
            emp3_doing = _collect_request_ids(self.wf_emp3, self.ec_emp3, "doing")
            assert request_id in emp3_doing, (
                f"人员03 待办应含 R1(requestId={request_id})，实际待办 {emp3_doing}"
            )

        with allure.step("④-2 人员03 提交 R1（会签 2/2）"):
            sub3 = self.wf_emp3.submit_request(
                request_id=request_id, other_params={"src": "submit"}
            )
            assert _is_pa_success(sub3), f"人员03 会签提交失败: {sub3}"

        # ── ⑤ 人员03 提交后列表校验 ──────────────────────────────────────────
        with allure.step("⑤-1 提交后：人员03 已办含 R1"):
            emp3_done = _collect_request_ids(self.wf_emp3, self.ec_emp3, "done")
            assert request_id in emp3_done, (
                f"人员03 已办应含 R1(requestId={request_id})，实际已办 {emp3_done}"
            )

        with allure.step("⑤-2 提交后：R1 流转到审批3"):
            status = self.wf_emp1.get_request_status(request_id)
            assert _is_pa_success(status), f"查询流程状态失败: {status}"
            node_name = str((status.get("data") or {}).get("currentNodeName") or "")
            assert CS_NODE3_NAME in node_name, (
                f"会签集齐后 R1 应流转到「{CS_NODE3_NAME}」，实际当前节点「{node_name}」: {status}"
            )

        with allure.step("⑤-3 提交后：人员04 待办含 R1"):
            emp4_doing = _collect_request_ids(self.wf_emp4, self.ec_emp4, "doing")
            assert request_id in emp4_doing, (
                f"人员04 待办应含 R1(requestId={request_id})，实际待办 {emp4_doing}"
            )

        with allure.step("⑤-4 提交后：人员05 待办含 R1"):
            emp5_doing = _collect_request_ids(self.wf_emp5, self.ec_emp5, "doing")
            assert request_id in emp5_doing, (
                f"人员05 待办应含 R1(requestId={request_id})，实际待办 {emp5_doing}"
            )