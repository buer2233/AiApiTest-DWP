# -*- coding: utf-8 -*-
"""E9 Portal 门户模块接口封装。"""

import allure

from page_api.public.base_api import BaseAPI


class PortalAPI(BaseAPI):
    """E9 Portal 门户相关接口。"""

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：获取 E9 Portal 协同门户信息")
    def get_synergy_portal(self, path="/workflow/search/WFSearchResult.jsp", pathparam="scope=doing", status_code=200, **kwargs):
        """获取协同门户信息，用于判断首页模块是否启用。

        Args:
            path: JSP 路径。
            pathparam: 路径参数。
            status_code: 期望 HTTP 状态码。
            **kwargs: 额外查询参数。

        Returns:
            dict: 包含 isuse、hpid、defaultExpand、width 等字段。
        """
        # Author:dengwanpeng
        # Create Date:2026-08-12
        # IsAI: True
        url = "/api/portal/synergy/getSynergyPortal"
        error_msg = kwargs.pop("error_msg", "获取 E9 Portal 协同门户信息")
        params = {
            "path": path,
            "pathparam": pathparam,
            "workflowid": "-1",
            "nodeid": "-1",
            "requestid": "-1",
            "secid": "-1",
            "docid": "-1",
            "__random__": self._timestamp(),
        }
        params.update(kwargs)
        return self.get(
            url,
            status_code=status_code,
            params=params,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )
