# -*- coding: utf-8 -*-
"""E9 EC 表格数据模块接口封装。

封装 /api/ec/dev/table/ 路径下的表格数据查询接口。
"""

import allure

from page_api.public.base_api import BaseAPI


class EcAPI(BaseAPI):
    """E9 EC 表格数据接口。"""

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：获取 EC 表格数据")
    def get_table_datas(self, data_key, current=1, sort_params="[]", status_code=200, **kwargs):
        """获取 EC 表格数据（待办事项列表）。

        Args:
            data_key: 分页数据 Key，由 splitPageKey 接口返回的 sessionkey 派生。
            current: 当前页码，默认 1。
            sort_params: 排序参数 JSON 字符串，默认 "[]"。
            status_code: 期望 HTTP 状态码。
            **kwargs: 额外表单参数。

        Returns:
            dict: 包含 columns（列定义）、datas（数据行）、rootMap、status 等字段。
        """
        # Author: dengwanpeng
        # Create Date: 2026-08-12
        # IsAI: True
        url = "/api/ec/dev/table/datas"
        error_msg = kwargs.pop("error_msg", "获取 EC 表格数据")
        form_data = {
            "dataKey": data_key,
            "current": str(current),
            "sortParams": sort_params,
        }
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取 EC 表格数据总数")
    def get_table_counts(self, data_key, status_code=200, **kwargs):
        """获取 EC 表格数据总数。

        Args:
            data_key: 分页数据 Key。
            status_code: 期望 HTTP 状态码。
            **kwargs: 额外表单参数。

        Returns:
            dict: 包含 count（数据总数）、status 等字段。
        """
        # Author: dengwanpeng
        # Create Date: 2026-08-12
        # IsAI: True
        url = "/api/ec/dev/table/counts"
        error_msg = kwargs.pop("error_msg", "获取 EC 表格数据总数")
        form_data = {"dataKey": data_key}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )