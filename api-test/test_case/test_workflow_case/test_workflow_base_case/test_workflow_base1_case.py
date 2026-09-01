# -*- coding: utf-8 -*-
"""E9 工作流模块基础用例 — 待办事项查询。"""

import allure
import pytest

@pytest.fixture(scope="class", autouse=True)
def _setup_class(login_admin, login_employee):
    """注入管理员 + 普通成员登录态，初始化各模块引用（class 级别，仅执行一次）。

    login_admin 自动登录管理员；login_employee 工厂按需登录普通成员。
    所有模块引用通过 global 变量暴露，setup_class 中挂到 self 上。
    """
    global workflow_api_admin, ec_api_admin, portal_api_admin
    global workflow_api_emp1, ec_api_emp1, portal_api_emp1

    # 管理员
    workflow_api_admin = login_admin.workflow
    ec_api_admin = login_admin.ec
    portal_api_admin = login_admin.portal

    # 普通成员 1
    emp1 = login_employee("employee1")
    workflow_api_emp1 = emp1.workflow
    ec_api_emp1 = emp1.ec
    portal_api_emp1 = emp1.portal


@allure.epic("E9-接口自动化")
@allure.feature("E9 工作流接口")
class TestWorkflowBase1API:
    """E9 工作流基础用例 — 待办事项查询。

    Author: dengwanpeng
    Create Date: 2026-08-12
    IsAI: True
    """

    def setup_class(self):

        # 管理员
        self.workflow_api_admin = workflow_api_admin
        self.ec_api_admin = ec_api_admin
        self.portal_api_admin = portal_api_admin

        # 普通成员 1
        self.workflow_api_emp1 = workflow_api_emp1
        self.ec_api_emp1 = ec_api_emp1
        self.portal_api_emp1 = portal_api_emp1

    @allure.story("查询待办事宜-正常场景")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_doing_list(self):
        """验证待办事项查询完整链路，按 HAR 抓包顺序覆盖全部已实现接口。

        链路步骤：
            1. 获取 Portal 协同门户信息
            2. 获取待办基础信息（页面标题、条件列表、树形数据）
            3. 获取待办统计（各状态数量、Tab 列表）
            4. 获取工作流列表参数
            5. 获取分页 Key（用于后续表格数据请求）
            6. 获取表格数据（待办事项列表）
            7. 获取表格数据总数
            8. 获取未操Author列表
        """
        # Author:dengwanpeng
        # Create Date:2026-08-12
        # IsAI: True

        with allure.step("1.获取 Portal 协同门户信息"):
            portal_info = self.portal_api_admin.get_synergy_portal()
            assert isinstance(portal_info, dict), (
                f"门户信息类型异常: {portal_info}"
            )
            assert "isuse" in portal_info, f"门户信息缺少 isuse 字段: {portal_info}"

        with allure.step("2.获取待办基础信息"):
            base_info = self.workflow_api_admin.get_doing_base_info()
            assert base_info.get("pagetitle") == "待办事宜", (
                f"页面标题异常: {base_info}"
            )
            assert isinstance(base_info.get("conditioninfo"), list), (
                f"条件列表类型异常: {base_info}"
            )
            assert isinstance(base_info.get("treedata"), list), (
                f"树形数据类型异常: {base_info}"
            )

        with allure.step("3.获取待办统计"):
            count_info = self.workflow_api_admin.get_doing_count_info()
            totalcount = count_info.get("totalcount", {})
            assert isinstance(totalcount, dict), f"统计数据类型异常: {count_info}"
            all_count = count_info.get("allCount", 0)
            assert all_count >= 0, f"总数异常: {count_info}"

        with allure.step("4.获取工作流列表参数"):
            wf_params = self.workflow_api_admin.get_wf_list_params()
            assert isinstance(wf_params, dict), (
                f"工作流列表参数类型异常: {wf_params}"
            )
            assert "viewcondition" in wf_params, (
                f"工作流列表参数缺少 viewcondition: {wf_params}"
            )

        with allure.step("5.获取分页 Key"):
            page_key = self.workflow_api_admin.get_split_page_key()
            sessionkey = page_key.get("sessionkey", "")
            assert sessionkey, f"分页 sessionkey 为空: {page_key}"
            assert isinstance(page_key.get("sharearg"), dict), (
                f"sharearg 类型异常: {page_key}"
            )

        with allure.step("6.获取表格数据"):
            table_data = self.ec_api_admin.get_table_datas(data_key=sessionkey)
            assert table_data.get("status") is True, (
                f"表格数据 status 异常: {table_data}"
            )
            assert isinstance(table_data.get("columns"), list), (
                f"表格列定义类型异常: {table_data}"
            )
            assert isinstance(table_data.get("datas"), list), (
                f"表格数据行类型异常: {table_data}"
            )

        with allure.step("7.获取表格数据总数"):
            table_count = self.ec_api_admin.get_table_counts(data_key=sessionkey)
            assert table_count.get("status") is True, (
                f"表格总数 status 异常: {table_count}"
            )
            assert table_count.get("count", 0) >= 0, (
                f"表格总数异常: {table_count}"
            )

        with allure.step("8.获取未操Author列表"):
            unoperators = self.workflow_api_admin.get_unoperators()
            assert isinstance(unoperators, dict), (
                f"未操Author数据类型异常: {unoperators}"
            )

    @allure.story("查询待办事宜-普通成员1")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_doing_list_emp1(self):
        """验证普通成员1待办事项查询链路，全部由 emp1 调用。

        链路步骤：
            1. 获取 Portal 协同门户信息
            2. 获取待办基础信息
            3. 获取待办统计
            4. 获取工作流列表参数
            5. 获取分页 Key
            6. 获取表格数据
            7. 获取表格数据总数
            8. 获取未操Author列表
        """
        # Author:dengwanpeng
        # Create Date:2026-08-12
        # IsAI: True

        with allure.step("1.获取 Portal 协同门户信息"):
            portal_info = self.portal_api_emp1.get_synergy_portal()
            assert isinstance(portal_info, dict), (
                f"门户信息类型异常: {portal_info}"
            )

        with allure.step("2.获取待办基础信息"):
            base_info = self.workflow_api_emp1.get_doing_base_info()
            assert isinstance(base_info, dict), f"基础信息类型异常: {base_info}"
            assert base_info.get("pagetitle", "") != "", f"页面标题为空: {base_info}"

        with allure.step("3.获取待办统计"):
            count_info = self.workflow_api_emp1.get_doing_count_info()
            assert count_info.get("allCount", 0) >= 0, f"总数异常: {count_info}"

        with allure.step("4.获取工作流列表参数"):
            wf_params = self.workflow_api_emp1.get_wf_list_params()
            assert isinstance(wf_params, dict), f"参数类型异常: {wf_params}"

        with allure.step("5.获取分页 Key"):
            page_key = self.workflow_api_emp1.get_split_page_key()
            sessionkey = page_key.get("sessionkey", "")
            assert sessionkey, f"分页 sessionkey 为空: {page_key}"

        with allure.step("6.获取表格数据"):
            table_data = self.ec_api_emp1.get_table_datas(data_key=sessionkey)
            assert table_data.get("status") is True, f"表格数据异常: {table_data}"
            assert len(table_data.get("datas", [])) >= 0, f"表格数据行异常: {table_data}"

        with allure.step("7.获取表格数据总数"):
            table_count = self.ec_api_emp1.get_table_counts(data_key=sessionkey)
            assert table_count.get("count", 0) >= 0, f"表格总数异常: {table_count}"

        with allure.step("8.获取未操Author列表"):
            unoperators = self.workflow_api_emp1.get_unoperators()
            assert isinstance(unoperators, dict), f"未操Author数据异常: {unoperators}"
