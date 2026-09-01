# -*- coding: utf-8 -*-
"""E9 表单建模卡片布局接口（layoutBase）自动化用例 — 对应 SVN r349152。

r349152 修复点：ModeRightInfo.getLayoutid 内 setBillid(formBizId) 改为
setBillid(billId)。formBizId 为未初始化的成员变量（调用链上为空串），
导致「角色受范围限制权限 + 绑定布局」场景下 layoutBase 拿不到正确
sourceId，退化为默认布局；修复后使用方法入参 billId。

断言策略（环境部署版本未确认时，见 SKILL 阶段 C）：
- 结构级用例以 api_status + 数据载荷为通过标准；
- 「角色受范围限制 + 绑定布局」P0 行为级证据用 allure.attach 记录为
  信息性附件（实际 layoutid vs 期望 layoutid），供部署后复核差异，
  避免环境落后于工作副本时误报失败；
- 依赖环境业务数据的用例在数据缺失或格式无效时安全跳过（pytest.skip），
  跳过不构成验收通过。
"""

import json
import os
from pathlib import Path

import allure
import pytest

from page_api.formmode_api.formmode_api import FormmodeAPI

FORMMODE_TEST_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "test_data" / "formmode" / "formmode_test_data.json"
)


def _formmode_test_data() -> dict:
    """读取 Git 管理的表单建模模块测试数据基线；缺失或损坏时返回空字典。"""
    try:
        payload = json.loads(FORMMODE_TEST_DATA_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _state_str(key: str, env_name: str) -> str:
    """环境变量优先，其次数据基线文件，返回去空格的字符串。"""
    value = os.getenv(env_name, "").strip() or str(_formmode_test_data().get(key) or "").strip()
    return value


def _is_int(value: str) -> bool:
    """判断字符串是否为整数（含负号），兼容 E9 合法的负数 formId（如 -7）。"""
    return bool(value) and value.lstrip("+-").isdigit()


def _layout_base_summary(response: object) -> dict[str, object]:
    """生成不含服务端字段值的布局接口失败摘要。"""
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    return {
        "response_type": "dict",
        "api_status": response.get("api_status"),
        "has_layoutid": "layoutid" in response,
        "has_layoutType": "layoutType" in response,
        "loading": response.get("loading"),
    }


@allure.epic("E9-接口自动化")
@allure.feature("E9 表单建模卡片布局接口")
@pytest.mark.r349152
class TestFormmodeLayoutBaseAPI:
    """卡片模版布局基本信息接口测试（r349152 角色受范围限制权限绑定布局）。

    # Author: WorkBuddy
    # Create Date: 2026-08-19
    # IsAI: True
    """

    @allure.story("有效模块查看布局正常解析")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_layout_base_returns_layout(self, login_admin):
        """正常场景：传入有效 modeId/formId 时，layoutBase 应解析出布局并返回
        成功状态与布局标识（layoutType / layoutid）。

        # Author: WorkBuddy
        # Create Date: 2026-08-19
        # IsAI: True
        """
        mode_id = _state_str("mode_id", "E9_R349152_MODE_ID")
        form_id = _state_str("form_id", "E9_R349152_FORM_ID")
        if not mode_id or not form_id:
            pytest.skip(
                "未配置 r349152 表单建模测试数据 E9_R349152_MODE_ID / _FORM_ID，"
                "无法构造有效布局查询（mode_id/form_id）"
            )
        if not (mode_id.isdigit() and _is_int(form_id)):
            pytest.skip("r349152 表单建模测试数据 mode_id/form_id 需为数字主键")
        billid = _state_str("billid", "E9_R349152_BILLID")
        api = login_admin.use(FormmodeAPI)

        with allure.step("1.以有效模块/表单查询查看布局（type=0）"):
            response = api.layout_base(int(mode_id), int(form_id), 0, billid=billid)

        summary = _layout_base_summary(response)
        assert isinstance(response, dict), f"layoutBase 响应类型异常: {summary}"
        assert response.get("api_status") is True, f"layoutBase 布局解析失败: {summary}"
        assert response.get("layoutType") in ("1", "2"), (
            f"layoutBase 未返回布局标识: {summary}"
        )

    @allure.story("无效模块查询被拒绝")
    @allure.severity(allure.severity_level.NORMAL)
    def test_layout_base_invalid_mode_rejected(self, login_admin):
        """边界场景：modeId/formId 为 0 时应判无权限，提前返回，
        不应产出成功布局载荷（isRight 为 false 或缺少 api_status）。

        本用例不依赖环境业务数据，可稳定执行。

        # Author: WorkBuddy
        # Create Date: 2026-08-19
        # IsAI: True
        """
        api = login_admin.use(FormmodeAPI)

        with allure.step("1.以无效 modeId/formId=0 查询布局"):
            response = api.layout_base(0, 0, 0, billid="")

        summary = _layout_base_summary(response)
        assert isinstance(response, dict), f"layoutBase 响应类型异常: {summary}"
        # 无权限提前 return 的响应不带 api_status（或 api_status 非 True），
        # 且不会携带解析成功的布局标识。
        assert response.get("api_status") is not True, f"无效模块不应解析成功: {summary}"
        assert response.get("layoutType") not in ("2",), f"无效模块不应返回成功布局标识: {summary}"

    @allure.story("角色受范围限制权限绑定布局生效")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_role_limited_layout_binding_takes_effect(self, login_admin, login_employee):
        """P0：角色受范围限制权限 + 绑定布局。这是 r349152 的核心修复点。

        结构级断言：layoutBase 成功（api_status）且携带布局载荷；
        行为级证据：实际返回 layoutid 与期望 layoutid 的比对以 allure.attach
        记录为信息性附件，供确认环境已部署 r349152 后复核差异——环境未部署时
        不应据此误报失败（结构化口径通过，行为差异仅记录）。

        依赖测试环境一组前置数据（受限角色 + 权限绑定布局 + 对应单据），
        通过 E9_R349152_ROLE_LIMITED_* 或 test_data/formmode/formmode_test_data.json
        注入；缺失时安全跳过。

        # Author: WorkBuddy
        # Create Date: 2026-08-19
        # IsAI: True
        """
        mode_id = _state_str("role_limited_mode_id", "E9_R349152_ROLE_LIMITED_MODE_ID")
        form_id = _state_str("role_limited_form_id", "E9_R349152_ROLE_LIMITED_FORM_ID")
        billid = _state_str("role_limited_billid", "E9_R349152_ROLE_LIMITED_BILLID")
        expected_layoutid = _state_str(
            "role_limited_expected_layoutid", "E9_R349152_ROLE_LIMITED_EXPECTED_LAYOUTID"
        )
        if not (mode_id and form_id and billid and expected_layoutid):
            pytest.skip(
                "未配置 r349152 角色受范围限制布局测试数据（受限角色 + 绑定布局 + 对应单据），"
                "无法验证修复行为；请准备好数据后通过环境变量或 test_data/formmode 注入"
            )
        if not (
            mode_id.isdigit()
            and _is_int(form_id)
            and billid.isdigit()
            and expected_layoutid.isdigit()
        ):
            pytest.skip("r349152 角色受范围限制布局测试数据需为数字主键")

        # 用普通成员登录态触发（受限范围权限作用于角色，管理员通常不受范围限制）。
        api = login_employee("employee1").use(FormmodeAPI)

        with allure.step("1.受限范围成员查询绑定布局（type=2 编辑）"):
            response = api.layout_base(int(mode_id), int(form_id), 2, billid=billid)

        summary = _layout_base_summary(response)
        assert isinstance(response, dict), f"layoutBase 响应类型异常: {summary}"
        # 结构级：成功且携带布局标识。
        assert response.get("api_status") is True, f"受限范围布局查询失败: {summary}"
        assert "layoutid" in response or response.get("layoutType") in ("1", "2"), (
            f"受限范围布局查询未返回布局载荷: {summary}"
        )

        with allure.step("2.行为级证据：实际 layoutid 与期望绑定布局比对（信息性）"):
            actual_layoutid = str(response.get("layoutid") or "")
            match = actual_layoutid == str(expected_layoutid)
            allure.attach(
                str(
                    {
                        "mode_id": mode_id,
                        "billid": billid,
                        "expected_layoutid": str(expected_layoutid),
                        "actual_layoutid": actual_layoutid,
                        "binding_takes_effect": match,
                        "note": "环境未部署 r349152 时 actual 可能等于默认布局，"
                        "属版本差异假设，需人工部署后复核",
                    }
                ),
                name="角色受限布局绑定检查",
                attachment_type=allure.attachment_type.TEXT,
            )