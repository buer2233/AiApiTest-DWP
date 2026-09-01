# -*- coding: utf-8 -*-
"""E9 数据中心看板/数据模型接口封装（board 模块主文件）。

r349149 阶段 C 前置数据构建所需：看板分组/创建/删除、数据模型列表与表元数据。
"""

import allure

from page_api.public.base_api import BaseAPI


class BoardAPI(BaseAPI):
    """E9 数据中心看板与数据模型接口。"""

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：看板分组列表")
    def list_dashboard_groups(self, right=0, status_code=200, **kwargs):
        """查询看板（数据面板）分组，right=0 不校验权限点。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = f"/api/board/dashboard/group/list/{right}"
        error_msg = kwargs.pop("error_msg", "查询看板分组列表")
        return self.get(
            url,
            status_code=status_code,
            params=kwargs,
            headers=self._browser_headers(),
            error_msg=error_msg,
        )

    @allure.step("接口：创建看板")
    def create_dashboard(self, name, groupid="", status_code=200, **kwargs):
        """创建看板（数字面板容器），返回主键 id。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/dashboard/create"
        error_msg = kwargs.pop("error_msg", "创建看板")
        form_data = {"name": name, "groupid": str(groupid)}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：删除看板")
    def delete_dashboard(self, board_id, status_code=200, **kwargs):
        """按 id 删除看板。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/dashboard/delete"
        error_msg = kwargs.pop("error_msg", "删除看板")
        return self.get(
            url,
            status_code=status_code,
            params={"id": str(board_id), **kwargs},
            headers=self._browser_headers(),
            error_msg=error_msg,
        )

    @allure.step("接口：数据模型全量列表（带分组）")
    def list_all_data_models(self, status_code=200, **kwargs):
        """查询全部数据模型（分组 + 模型 id/名称）。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/dm/listAll"
        error_msg = kwargs.pop("error_msg", "查询数据模型列表")
        return self.get(
            url,
            status_code=status_code,
            params=kwargs,
            headers=self._browser_headers(),
            error_msg=error_msg,
        )

    @allure.step("接口：数据模型表元数据")
    def list_table_meta(self, model_id, status_code=200, **kwargs):
        """查询数据模型的表与字段元数据。"""
        # Author: Claude
        # Create Date: 2026-08-18
        # IsAI: True
        url = "/api/board/dm/tableMeta/list"
        error_msg = kwargs.pop("error_msg", "查询数据模型表元数据")
        return self.get(
            url,
            status_code=status_code,
            params={"id": str(model_id), **kwargs},
            headers=self._browser_headers(),
            error_msg=error_msg,
        )
