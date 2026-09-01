# -*- coding: utf-8 -*-
"""E9 工作流公式（函数库）接口封装。

对应后端 ``WorkflowFormulaAction``（类级 ``@Path("/workflow/formula")``），
提供函数库列表、公式类型等只读接口。业务表 ``workflow_formula`` /
``workflow_formula_type`` 与 r349159 改动（``e10Migration/DataScanFileToDB.jsp``
函数库本地文件初始化扫描）同属函数库业务域，本封装用于该业务域的回归验证。
"""

import allure

from page_api.public.base_api import BaseAPI


class WorkflowFormulaAPI(BaseAPI):
    """E9 工作流公式（函数库）接口。"""

    @allure.step("接口：获取函数库列表")
    def get_function_list(self, status_code=200, return_response=False, **kwargs):
        """获取函数库列表（含内置函数与自定义函数）。

        后端实现 ``GetFunctionListCmd.execute`` 返回 ``{"formulaInfo": [...]}``，
        数据来源于 ``workflow_formula``（内置函数）与 ``workflow_formula_db``
        （数据库函数）两张表。

        Args:
            status_code: 期望的 HTTP 状态码，默认 200。
            return_response: True 时返回原始 Response（供未登录等异常场景探测）。
            **kwargs: 透传 BaseAPI.get 的其它参数。

        Returns:
            dict | requests.Response: 默认返回 JSON 字典，形如
                ``{"formulaInfo": [{"id": 1, "fun": "...", ...}]}``。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-24
        # IsAI: True
        url = "/api/workflow/formula/getFunctionList"
        error_msg = kwargs.pop("error_msg", "获取函数库列表")
        return self.get(
            url,
            status_code=status_code,
            return_response=return_response,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：获取公式类型选项")
    def get_formula_types(self, status_code=200, return_response=False, **kwargs):
        """获取公式类型选项及用户维护权限。

        后端实现 ``GetFormulaTypesCmd.execute`` 返回
        ``{"typeOptionsInDB": [...], "typeOptions": [...], "hasRight": 0|1}``。

        Returns:
            dict | requests.Response: 默认返回 JSON 字典，含 typeOptions、hasRight。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-24
        # IsAI: True
        url = "/api/workflow/formula/getFormulaTypes"
        error_msg = kwargs.pop("error_msg", "获取公式类型选项")
        return self.get(
            url,
            status_code=status_code,
            return_response=return_response,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：获取公式报表信息")
    def get_report_info(self, params=None, status_code=200, **kwargs):
        """获取公式报表信息（需请求参数，用于边界/异常场景验证）。

        后端实现 ``GetReportInfoCmd`` 依赖请求参数（如公式 ID 等），
        参数缺失时用于验证接口降级行为。

        Args:
            params: 请求参数字典；不传时模拟「缺参」边界场景。
            status_code: 期望的 HTTP 状态码，默认 200。

        Returns:
            dict: 接口响应的 JSON 字典。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-24
        # IsAI: True
        url = "/api/workflow/formula/getReportInfo"
        error_msg = kwargs.pop("error_msg", "获取公式报表信息")
        return self.get(
            url,
            status_code=status_code,
            params=params or {},
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )