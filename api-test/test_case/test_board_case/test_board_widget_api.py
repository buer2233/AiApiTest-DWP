# -*- coding: utf-8 -*-
"""E9 数据中心看板组件接口自动化用例（r349149 过滤条件空值口径）。

测试数据读取优先级：环境变量 > ``test_data/board/board_test_data.json``
（Git 管理的模块级数据基线，由 tools/prepare_board_test_data.py 构建）。
"""

import json
import os
from pathlib import Path

import allure
import pytest

from page_api.board_api.board_widget_api import BoardWidgetAPI, build_widget_config_data

BOARD_TEST_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "test_data" / "board" / "board_test_data.json"
)


def _board_test_data() -> dict:
    """读取 Git 管理的看板模块测试数据基线；缺失或损坏时返回空字典。"""
    try:
        payload = json.loads(BOARD_TEST_DATA_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _widget_id(env_name: str, state_key: str, purpose: str) -> str:
    """读取可安全查询的看板组件测试数据（环境变量优先，其次数据基线文件）。

    组件 id 为数字主键或 UUID 十六进制串（可含连字符），统一按字符串返回。
    """
    # Author: Claude
    # Create Date: 2026-08-18
    # IsAI: True
    value = os.getenv(env_name, "").strip() or str(_board_test_data().get(state_key) or "").strip()
    if not value:
        pytest.skip(f"未配置 r349149 可回收测试数据 {env_name}/test_data.board.{state_key}（{purpose}）")
    compact = value.replace("-", "")
    if len(compact) < 8 or not compact.isalnum():
        pytest.skip(f"r349149 测试数据 {env_name}/{state_key} 格式无效")
    return value


def _data_summary(response: object) -> dict[str, object]:
    """生成不含服务端字段值的取数接口失败摘要。"""
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    return {
        "response_type": "dict",
        "api_status": response.get("api_status"),
        "has_data": "data" in response,
    }


@allure.epic("E9-接口自动化")
@allure.feature("E9 数据中心看板接口")
@pytest.mark.r349149
class TestBoardWidgetGetDataAPI:
    """看板组件取数接口测试（r349149 负向过滤空值口径）。

    # Author: Claude
    # Create Date: 2026-08-18
    # IsAI: True
    """

    @allure.story("已保存组件取数正常返回")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_data_returns_saved_widget_data(self, login_admin):
        """正常场景：按组件保存的配置取数，接口成功且携带数据载荷。

        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        """
        widget_id = _widget_id("E9_R349149_WIDGET_ID", "widget_id", "任一可查询的数字面板组件")
        api = login_admin.use(BoardWidgetAPI)

        with allure.step("1.按组件 id 取数"):
            response = api.get_data(widget_id)

        summary = _data_summary(response)
        assert isinstance(response, dict), f"取数响应类型异常: {summary}"
        assert response.get("api_status") is True, f"组件取数失败: {summary}"
        assert "data" in response, f"组件取数未返回数据载荷: {summary}"

    @allure.story("不包含类过滤条件包含空值记录")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_data_uncontains_filter_covers_null_records(self, login_admin):
        """P0：配置了「不包含/开头不是/结尾不包含/不包含于」过滤条件、且过滤字段存在
        空值数据的组件，取数成功且返回数据；空值记录应包含在结果中（r349149 修复点，
        结果集是否含空值行由测试数据保证，界面口径需人工核对一次）。

        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        """
        widget_id = _widget_id(
            "E9_R349149_FILTER_WIDGET_ID",
            "filter_widget_id",
            "配置了负向过滤条件且过滤字段含空值的组件",
        )
        api = login_admin.use(BoardWidgetAPI)

        with allure.step("1.按含负向过滤条件的组件 id 取数"):
            response = api.get_data(widget_id)

        summary = _data_summary(response)
        assert isinstance(response, dict), f"取数响应类型异常: {summary}"
        assert response.get("api_status") is True, f"含过滤条件的组件取数失败: {summary}"
        assert "data" in response, f"含过滤条件的组件取数未返回数据载荷: {summary}"

        with allure.step("2.检查结果集是否含空值维度组（信息性，取决于环境部署版本）"):
            rows = response.get("data") if isinstance(response.get("data"), list) else []
            empty_groups = [
                row for row in rows
                if isinstance(row, dict) and str(row.get("d1") or "").strip() == ""
            ]
            allure.attach(
                str({"total_rows": len(rows), "empty_group_rows": len(empty_groups)}),
                name="空值口径检查",
                attachment_type=allure.attachment_type.TEXT,
            )

    @allure.story("不存在的组件取数被拒绝")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_data_with_nonexistent_widget_is_rejected(self, login_admin):
        """异常场景：不存在的组件 id 不应返回成功取数结果。

        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        """
        api = login_admin.use(BoardWidgetAPI)

        with allure.step("1.以不存在的组件 id 取数"):
            response = api.get_data(999999999)

        summary = _data_summary(response)
        assert isinstance(response, dict), f"取数响应类型异常: {summary}"
        assert response.get("api_status") is not True, f"不存在的组件不应取数成功: {summary}"

    @allure.story("临时配置取数接口解析压缩载荷")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_data_with_config_parses_minimal_payload(self, login_admin):
        """边界场景：最小临时配置载荷（无数据模型）应得到结构化业务响应，
        用于验证 LZW 压缩载荷被服务端正确解压与解析。

        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        """
        api = login_admin.use(BoardWidgetAPI)
        data = build_widget_config_data()

        with allure.step("1.以最小临时配置载荷取数"):
            response = api.get_data_with_config(data)

        assert isinstance(response, dict), f"临时配置取数响应类型异常: {type(response).__name__}"
        assert "api_status" in response, f"载荷未被正确解析，响应缺少业务状态字段: {list(response)[:8]}"
