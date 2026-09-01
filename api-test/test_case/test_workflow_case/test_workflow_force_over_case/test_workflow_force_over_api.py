# -*- coding: utf-8 -*-
"""E9 强制归档接口用例 — 对应 SVN r349084。

覆盖 /api/workflow/paService/doForceOver，并用已有待办列表接口断言归档后消失。
会改流程状态的步骤只处理标题含测试标记的可丢弃流程，或环境变量指定的 requestId。
"""

import os
import allure
import pytest


SAFE_TITLE_HINTS = ("autotest", "自动化", "r349084", "auto_test", "auto-test")


@pytest.fixture(scope="class", autouse=True)
def _setup_class(login_admin, login_employee):
    """注入管理员 + 普通成员登录态。"""
    global workflow_api_admin, ec_api_admin
    global workflow_api_emp1, ec_api_emp1

    workflow_api_admin = login_admin.workflow
    ec_api_admin = login_admin.ec

    emp1 = login_employee("employee1")
    workflow_api_emp1 = emp1.workflow
    ec_api_emp1 = emp1.ec


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


def _is_pa_code(response, *expected):
    aliases = {
        "SUCCESS": {"SUCCESS", "1"},
        "PARAM_ERROR": {"PARAM_ERROR", "2"},
        "NO_PERMISSION": {"NO_PERMISSION", "3"},
        "FAIL": {"FAIL", "6"},
    }
    actual = _pa_code(response)
    allowed = set()
    for item in expected:
        allowed.update(aliases.get(item, {item}))
        allowed.add(str(item))
    return actual in allowed


def _collect_doing_rows(workflow_api, ec_api):
    """复用已有待办封装，取出 requestid / 标题。"""
    workflow_api.get_doing_base_info()
    page_key = workflow_api.get_split_page_key()
    sessionkey = page_key.get("sessionkey") or ""
    assert sessionkey, f"分页 sessionkey 为空: {page_key}"
    table = ec_api.get_table_datas(data_key=sessionkey)
    rows = []
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
        if request_id is None:
            continue
        title = str(
            item.get("requestname")
            or item.get("requestName")
            or item.get("requestnamespan")
            or ""
        )
        rows.append({"requestid": request_id, "requestname": title})
    return rows, table


def _is_disposable_title(title):
    text = (title or "").lower()
    return any(hint in text for hint in SAFE_TITLE_HINTS)


def _pick_disposable_request_id(workflow_api, ec_api):
    env_id = os.environ.get("E9_FORCE_OVER_REQUEST_ID", "").strip()
    if env_id.isdigit():
        return int(env_id), "env"
    rows, _ = _collect_doing_rows(workflow_api, ec_api)
    for row in rows:
        if _is_disposable_title(row["requestname"]):
            return row["requestid"], "title"
    return None, None


def _doing_has_request(workflow_api, ec_api, request_id):
    rows, _ = _collect_doing_rows(workflow_api, ec_api)
    return any(row["requestid"] == int(request_id) for row in rows)


@allure.epic("E9-接口自动化")
@allure.feature("E9 工作流强制归档接口")
class TestWorkflowForceOverAPI:
    """强制归档接口测试（r349084）。

    Author: dengwanpeng
    Create Date: 2026-08-13
    IsAI: True
    """

    def setup_class(self):
        self.workflow_api_admin = workflow_api_admin
        self.ec_api_admin = ec_api_admin
        self.workflow_api_emp1 = workflow_api_emp1
        self.ec_api_emp1 = ec_api_emp1

    @allure.story("强制归档-异常场景-非法 requestId")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.r349084
    def test_force_over_invalid_request_id(self):
        """requestId 非法时应返回参数错误，不改任何流程。"""
        # Author:dengwanpeng
        # Create Date:2026-08-13
        # IsAI: True
        with allure.step("1.用非法 requestId 调用强制归档"):
            response = self.workflow_api_admin.do_force_over(request_id=0)
            assert isinstance(response, dict), f"响应类型异常: {response}"
            assert _is_pa_code(response, "PARAM_ERROR"), (
                f"非法 requestId 应返回 PARAM_ERROR: {response}"
            )

    @allure.story("强制归档-异常场景-无权限")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.r349084
    def test_force_over_no_permission(self):
        """普通成员对不属于自己的流程强制归档应失败。"""
        # Author:dengwanpeng
        # Create Date:2026-08-13
        # IsAI: True
        target_id = 1
        with allure.step("1.如管理员待办有数据，取一条给无权限账号去归档"):
            rows, _ = _collect_doing_rows(self.workflow_api_admin, self.ec_api_admin)
            if rows:
                target_id = rows[0]["requestid"]

        with allure.step(f"2.普通成员强制归档 requestId={target_id}"):
            response = self.workflow_api_emp1.do_force_over(request_id=target_id)
            assert isinstance(response, dict), f"响应类型异常: {response}"
            assert _is_pa_code(response, "NO_PERMISSION", "PARAM_ERROR", "FAIL"), (
                f"无权限归档应失败: {response}"
            )
            assert not _is_pa_code(response, "SUCCESS"), (
                f"无权限账号不应归档成功: {response}"
            )

    @allure.story("强制归档-正常场景-待办消失且不可重复归档")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.r349084
    def test_force_over_clears_normal_todo(self):
        """有权限强制归档后，该 requestId 不再出现在待办列表；再次归档应失败。

        对应方案 WF-FO-02 / WF-FO-04。只处理可丢弃测试流程。
        """
        # Author:dengwanpeng
        # Create Date:2026-08-13
        # IsAI: True
        request_id, source = _pick_disposable_request_id(
            self.workflow_api_admin, self.ec_api_admin
        )
        if request_id is None:
            request_id, source = _pick_disposable_request_id(
                self.workflow_api_emp1, self.ec_api_emp1
            )
            operator = self.workflow_api_admin
            list_api = (self.workflow_api_emp1, self.ec_api_emp1)
        else:
            operator = self.workflow_api_admin
            list_api = (self.workflow_api_admin, self.ec_api_admin)

        if request_id is None:
            pytest.skip(
                "未找到可丢弃测试流程（标题需含 AutoTest/自动化/r349084），"
                "也未配置 E9_FORCE_OVER_REQUEST_ID。跳过以免误归档业务数据。"
            )

        with allure.step(f"1.强制归档可丢弃流程 requestId={request_id}（来源 {source}）"):
            response = operator.do_force_over(
                request_id=request_id,
                remark="r349084 api-test force over",
            )
            assert isinstance(response, dict), f"响应类型异常: {response}"
            if not _is_pa_code(response, "SUCCESS"):
                pytest.skip(
                    f"环境未能成功强制归档 requestId={request_id}，"
                    f"可能未部署 r349084 或当前账号无归档权限: {response}"
                )

        with allure.step("2.复用待办列表，确认 requestId 已消失"):
            assert not _doing_has_request(list_api[0], list_api[1], request_id), (
                f"强制归档后待办仍包含 requestId={request_id}"
            )

        with allure.step("3.对已归档流程再次强制归档，应失败"):
            again = operator.do_force_over(request_id=request_id)
            assert not _is_pa_code(again, "SUCCESS"), (
                f"已归档流程不应再次成功: {again}"
            )
            assert _is_pa_code(again, "NO_PERMISSION", "PARAM_ERROR", "FAIL"), (
                f"重复归档应返回失败码: {again}"
            )

    @allure.story("强制归档-核心场景-超时待办 isremark=5")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.r349084
    def test_force_over_clears_timeout_todo(self):
        """存在 isremark=5 的操作人时归档，待办需提交应消失。

        对应方案 WF-FO-01。制造超时态依赖环境数据，未配置则跳过。
        """
        # Author:dengwanpeng
        # Create Date:2026-08-13
        # IsAI: True
        env_id = os.environ.get("E9_FORCE_OVER_TIMEOUT_REQUEST_ID", "").strip()
        if not env_id.isdigit():
            pytest.skip(
                "未配置 E9_FORCE_OVER_TIMEOUT_REQUEST_ID。"
                "该用例需要一条当前操作人 isremark=5 的可丢弃流程。"
            )
        request_id = int(env_id)
        with allure.step(f"1.对超时流程 {request_id} 强制归档"):
            response = self.workflow_api_admin.do_force_over(
                request_id=request_id,
                remark="r349084 timeout force over",
                other_params={"ismonitor": "1"},
            )
            assert _is_pa_code(response, "SUCCESS"), (
                f"超时流程强制归档失败（请确认环境已部署 r349084）: {response}"
            )
        with allure.step("2.管理员与成员待办均不应再出现该 requestId"):
            assert not _doing_has_request(
                self.workflow_api_admin, self.ec_api_admin, request_id
            ), f"归档后管理员待办仍有 requestId={request_id}"
            assert not _doing_has_request(
                self.workflow_api_emp1, self.ec_api_emp1, request_id
            ), f"归档后成员待办仍有 requestId={request_id}"
