# -*- coding: utf-8 -*-
"""E9 工作流模块接口封装。

封装 /api/workflow/reqlist/ 路径下的待办事项相关接口，
作为流程模块的基础接口类。
"""

import allure

from page_api.public.base_api import BaseAPI


class WorkflowAPI(BaseAPI):
    """E9 工作流（待办事项）接口。"""

    # --------------------------------通用方法---------------------------------------

    def _build_form_data(self, **kwargs):
        """构造待办事项列表接口的公共表单参数。

        所有 /api/workflow/reqlist/* 接口共用这些基础参数，
        各接口方法通过 actiontype 区分具体操作。
        """
        form_data = {
            "method": "all",
            "offical": "",
            "officalType": "-1",
            "hideNoDataTab": "false",
            "viewScope": "doing",
            "complete": "0",
            "menuIds": "1,13",
            "menuPathIds": "1,13",
        }
        form_data.update(kwargs)
        return form_data

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：获取待办基础信息")
    def get_doing_base_info(self, status_code=200, **kwargs):
        """获取待办事项页面基础信息（条件列表、页面标题、树形数据）。

        Returns:
            dict: 包含 conditioninfo、pagetitle、treedata、countcfg 等字段。
        """
        # Author: dengwanpeng
        # Create Date: 2026-08-12
        # IsAI: True
        url = "/api/workflow/reqlist/doingBaseInfo"
        error_msg = kwargs.pop("error_msg", "获取待办基础信息")
        form_data = self._build_form_data(actiontype="baseinfo", **kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取待办统计信息")
    def get_doing_count_info(self, status_code=200, **kwargs):
        """获取待办事项各状态数量统计及 Tab 列表。

        Returns:
            dict: 包含 totalcount、topTab、treecount、allCount 等字段。
        """
        # Author: dengwanpeng
        # Create Date: 2026-08-12
        # IsAI: True
        url = "/api/workflow/reqlist/doingCountInfo"
        error_msg = kwargs.pop("error_msg", "获取待办统计信息")
        form_data = self._build_form_data(actiontype="countinfo", **kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取工作流列表参数")
    def get_wf_list_params(self, status_code=200, **kwargs):
        """获取工作流列表配置参数。

        Returns:
            dict: 工作流列表参数配置。
        """
        # Author: dengwanpeng
        # Create Date: 2026-08-12
        # IsAI: True
        url = "/api/workflow/reqlist/getWfListParams"
        error_msg = kwargs.pop("error_msg", "获取工作流列表参数")
        form_data = self._build_form_data(loadDefTab="true", **kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取待办分页 Key")
    def get_split_page_key(self, status_code=200, **kwargs):
        """获取分页数据 Key，后续表格数据请求需要此 Key。

        Returns:
            dict: 包含 sessionkey、isQueryByNewTable、sharearg 等字段。
        """
        # Author: dengwanpeng
        # Create Date: 2026-08-12
        # IsAI: True
        url = "/api/workflow/reqlist/splitPageKey"
        error_msg = kwargs.pop("error_msg", "获取待办分页 Key")
        form_data = self._build_form_data(
            actiontype="splitpage",
            viewcondition="0",
            defaultTabVal="0",
            loadDefTab="true",
            **kwargs,
        )
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取未操作者列表")
    def get_unoperators(self, status_code=200, **kwargs):
        """获取待办事项的未操作者信息。

        Returns:
            dict: 未操作者数据。
        """
        # Author: dengwanpeng
        # Create Date: 2026-08-12
        # IsAI: True
        url = "/api/workflow/reqlist/getUnoperators"
        error_msg = kwargs.pop("error_msg", "获取未操作者列表")
        form_data = self._build_form_data(**kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )