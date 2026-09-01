# -*- coding: utf-8 -*-
"""E9 系统导出（systemExport）接口封装。

对应后端 ``SystemExportAction``（类级 ``@Path("/systemExpAndImp/systemExport")``）。
该模块是流程导入（workflowImport）主流程的**前置数据来源**：导出指定流程得到
导出包文件（esf 压缩包），产生的 fileid 直接作为导入接口的 fieldId 使用，
形成「导出 → 导入」闭环。r349181-r349184 变更点（流程导入去重）的完整回归依赖此闭环。

导出链路（实测 .27 环境）：
    POST /doSystemExport（异步触发，返回 {"iswwf":"1"}）
    → POST /workflow/workflowImport/getProgress（type=export）轮询
    → flag=success 时返回 filePath（含 fileid）
"""

import allure

from page_api.public.base_api import BaseAPI


class SystemExportAPI(BaseAPI):
    """E9 系统导出（systemExport）接口。"""

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：获取系统导出页面模块树")
    def get_module_tree(self, status_code=200, **kwargs):
        """获取系统导出页面的模块树（流程、表单、矩阵等分类树）。

        Args:
            status_code: 期望 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.get 的其余参数。

        Returns:
            dict: 模块树结构。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/systemExpAndImp/systemExport/getModuleTree"
        error_msg = kwargs.pop("error_msg", "获取系统导出模块树")
        return self.get(
            url,
            status_code=status_code,
            headers=self._browser_headers(accept="application/json, text/javascript, */*; q=0.01"),
            error_msg=error_msg,
        )

    @allure.step("接口：获取可导出流程列表分页 Key")
    def get_right_form_list(self, type_="workflow", status_code=200, **kwargs):
        """获取系统导出右侧列表的分页 sessionkey（type=workflow 即流程列表）。

        后端实现 ``GetSystemExportRightFormListCmd``：返回 ``listSessionkey.sessionkey``，
        后续分页取数接口据此拉取可导出的流程项（含 workflowid/workflowname）。

        Args:
            type_: 导出类型，workflow=流程。
            status_code: 期望 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其余参数。

        Returns:
            dict: 含 listSessionkey.sessionkey。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/systemExpAndImp/systemExport/getSystemExportRightFormList"
        error_msg = kwargs.pop("error_msg", "获取可导出流程列表分页 Key")
        form_data = {"type": str(type_)}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：执行系统导出")
    def do_system_export(self, workflow_id, status_code=200, **kwargs):
        """执行流程导出（异步），产出一个可下载的导出包，fileid 供导入复用。

        后端实现 ``DoSystemExportCmd.doExport``：入参 ``datas`` 为 JSON 数组
        ``[{"type":"workflow","id":"<workflowId>"}]``。导出异步执行，立即返回
        ``{"iswwf":"1"}``；实际进度经 ``getProgress(type=export)`` 轮询。

        Args:
            workflow_id: 要导出的流程 ID（workflow_base.id）。
            status_code: 期望 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其余参数（可传 type/preCheck 等）。

        Returns:
            dict: 含 iswwf 触发标志。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/systemExpAndImp/systemExport/doSystemExport"
        error_msg = kwargs.pop("error_msg", "执行系统导出")
        import json as _json

        datas = _json.dumps([{"type": "workflow", "id": str(workflow_id)}])
        form_data = {"datas": datas}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )