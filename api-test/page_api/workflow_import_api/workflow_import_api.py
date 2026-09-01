# -*- coding: utf-8 -*-
"""E9 流程导入（workflowImport）接口封装。

对应后端 ``WorkflowImportAction``（类级 ``@Path("/workflow/workflowImport")``，
继承 ``WorkflowImportListAction``）。该路径下的接口是 r349181-r349184 变更点的
HTTP 透出层：变更的导入策略类 ``WorkflowNodeFormGroupTableAction`` 经
``ImportService`` 在导入执行时反射触发，本封装用于该行为变更的接口回归验证。

透出链路（MCP trace_path 反查）：
    WorkflowNodeFormGroupTableAction（策略子类）
    ← ImportService.doTableActionBeforeInsert/BeforeUpdate（导入引擎）
    ← WorkflowImportOperationCmd / ImportFormCloudStoreCmd / GetImportTypeCmd
    ← WorkflowImportServiceImpl
    ← WorkflowImportListAction（本封装覆盖的 HTTP 入口）
"""

import allure

from page_api.public.base_api import BaseAPI


class WorkflowImportAPI(BaseAPI):
    """E9 流程导入（workflowImport）接口。"""

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：获取新版导入表单")
    def get_import_new_form(self, status_code=200, **kwargs):
        """获取新版导入引导表单（含导入类型/内容/创建新表单等选项配置）。

        后端实现 ``GetImportNewFormCmd``：返回 ``tabInfo``（三步骤提示）、
        ``importType``（新增/更新）、``importContent``（路径/表单）、``createForm``
        等选项，用于确证新版流程导入功能已部署且表单可加载。

        Args:
            status_code: 期望 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其余参数。

        Returns:
            dict: 含 tabInfo/importType/importContent/createForm/optionTitles 等字段。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/workflow/workflowImport/getImportNewForm"
        error_msg = kwargs.pop("error_msg", "获取新版导入表单")
        form_data = dict(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取导入类型（新增/更新）")
    def get_import_type(self, field_id, importcontent="0", status_code=200, return_response=False, **kwargs):
        """获取导入类型判定：1 新增 / 0 更新。

        后端实现 ``GetImportTypeCmd.execute``：解压上传的流程包并解析 XML，经
        ``ImportTypeService.getAllCanUpdateBaseUuids`` 按
        ``workflow_exchange.exist_condition``（本批次 r349181 为
        ``workflow_NodeFormGroup`` 配置 ``nodeid,groupid``）判定目标库是否已存在
        同键数据，返回 ``importtypevalue``（1 新增 / 0 更新）及可更新选项。

        Args:
            field_id: 上传的导出包文件 ID（对应后端 params 的 fieldId）。
            importcontent: 导入内容，0 路径 / 1 表单。
            status_code: 期望 HTTP 状态码，默认 200；传 0 跳过状态码断言。
            return_response: True 时返回原始 Response（供环境未部署 404 等场景探测）。
            **kwargs: 透传 BaseAPI.post 的其余参数。

        Returns:
            dict | requests.Response: 默认返回 JSON 字典；return_response=True
                返回原始 Response。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/workflow/workflowImport/getImportType"
        error_msg = kwargs.pop("error_msg", "获取流程导入类型")
        form_data = {"fieldId": str(field_id), "importcontent": str(importcontent)}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            return_response=return_response,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取导入结果列表信息")
    def get_import_info(self, status_code=200, **kwargs):
        """获取导入成功后显示的列表信息。

        后端实现 ``WorkflowImportOperationCmd.doWorkflowImportOperation``，是实际执行
        导入的命令（触发 ImportService 导入引擎与 TableAction 去重策略）。

        Args:
            status_code: 期望 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其余参数（含表单字段）。

        Returns:
            dict: 导入结果 JSON。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/workflow/workflowImport/getImportInfo"
        error_msg = kwargs.pop("error_msg", "获取流程导入结果列表")
        form_data = dict(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：云商店表单导入")
    def import_form_cloud_store(self, file_id, status_code=200, **kwargs):
        """从云商店导入表单。

        后端实现 ``ImportFormCloudStoreCmd.doWorkflowImportOperation``，是导入执行的
        另一条透出路径（云商店导入）。入参含上传文件标识 fileId。

        Args:
            file_id: 云商店导入源文件 ID。
            status_code: 期望 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其余参数。

        Returns:
            dict: 导入结果 JSON。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/workflow/workflowImport/importFormCloudStore"
        error_msg = kwargs.pop("error_msg", "云商店表单导入")
        form_data = {"fileId": str(file_id)}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：查询导入/导出进度")
    def get_import_progress(self, type_="import", status_code=200, **kwargs):
        """查询导入（或导出）进度信息。

        后端实现 ``WorkflowImportProgressCmd.execute``：按 ``type``（import/export）
        返回进度百分比、描述、标志等字段，用于轮询导入完成状态。

        Args:
            type_: 进度类型，import 导入 / export 导出。
            status_code: 期望 HTTP 状态码，默认 200。
            **kwargs: 透传 BaseAPI.post 的其余参数。

        Returns:
            dict: 含 percent、desc、color、flag、type 等进度字段。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-27
        # IsAI: True
        url = "/api/workflow/workflowImport/getProgress"
        error_msg = kwargs.pop("error_msg", "查询流程导入进度")
        form_data = {"type": str(type_)}
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )