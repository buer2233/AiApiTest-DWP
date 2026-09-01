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
        # Author:dengwanpeng
        # Create Date:2026-08-12
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
        # Author:dengwanpeng
        # Create Date:2026-08-12
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
        # Author:dengwanpeng
        # Create Date:2026-08-12
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
        # Author:dengwanpeng
        # Create Date:2026-08-12
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
        # Author:dengwanpeng
        # Create Date:2026-08-12
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

    @allure.step("接口：获取已办基础信息")
    def get_done_base_info(self, status_code=200, **kwargs):
        """获取已办事项页面基础信息（条件列表、页面标题、树形数据）。

        Returns:
            dict: 包含 conditioninfo、pagetitle、treedata、countcfg 等字段。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/workflow/reqlist/doneBaseInfo"
        error_msg = kwargs.pop("error_msg", "获取已办基础信息")
        form_data = self._build_form_data(actiontype="baseinfo", viewScope="done", **kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取已办统计信息")
    def get_done_count_info(self, status_code=200, **kwargs):
        """获取已办事项各状态数量统计及 Tab 列表。

        Returns:
            dict: 包含 totalcount、topTab、treecount、allCount 等字段。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/workflow/reqlist/doneCountInfo"
        error_msg = kwargs.pop("error_msg", "获取已办统计信息")
        form_data = self._build_form_data(actiontype="countinfo", viewScope="done", **kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：获取可创建流程列表")
    def get_create_workflow_list(self, status_code=200, **kwargs):
        """获取当前用户可创建（发起）的流程模板列表。

        Returns:
            list: ApiWorkflowBaseInfo 数组，元素含 workflowId/workflowName/
                workflowTypeId/workflowTypeName/formId 字段。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/workflow/paService/getCreateWorkflowList"
        error_msg = kwargs.pop("error_msg", "获取可创建流程列表")
        return self.post(
            url,
            status_code=status_code,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )

    @allure.step("接口：创建流程（创建即提交流转）")
    def do_create_request(
        self, workflow_id, request_name, main_data, other_params=None, status_code=200, **kwargs
    ):
        """调用公开 API 创建流程，并在 other_params.isnextflow=1 时创建即流转。

        Args:
            workflow_id: 流程模板 ID（对应 ApiWorkflowBaseInfo.workflowId）。
            request_name: 请求标题。
            main_data: 主表字段列表（List[WorkflowRequestTableField]），
                元素键含 fieldId/fieldName/fieldValue 等，必填。
            other_params: 额外参数 dict，创建即提交需传 {"isnextflow": "1"}。
            status_code: 期望 HTTP 状态码。
            **kwargs: 其它 ReqOperateRequestEntity 字段（如 secLevel、remark）。

        Returns:
            dict: PA 响应，code 为 SUCCESS 时 data.requestid 为新建流程 ID。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/workflow/paService/doCreateRequest"
        error_msg = kwargs.pop("error_msg", "创建流程")
        payload = {
            "workflowId": int(workflow_id),
            "requestName": request_name,
            "mainData": main_data if main_data else [],
        }
        if other_params:
            payload["otherParams"] = other_params
        payload.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            json=payload,
            headers=self._browser_headers(
                origin=True,
                accept="application/json, text/javascript, */*; q=0.01",
            ),
            error_msg=error_msg,
        )

    @allure.step("接口：提交流程")
    def submit_request(self, request_id, remark="", other_params=None, status_code=200, **kwargs):
        """调用公开 API 提交指定流程（会签提交、审批通过均为提交）。

        会签节点由多人会签时，各会签人依次调用本接口提交，引擎在集齐
        全部会签人后自动流转到下一节点。

        Args:
            request_id: 流程请求 ID。
            remark: 签字意见，可空。
            other_params: 额外参数 dict，提交为 {"src": "submit"}。
            status_code: 期望 HTTP 状态码。
            **kwargs: 其它 ReqOperateRequestEntity 字段。

        Returns:
            dict: PA 响应，code 为 SUCCESS 表示提交成功。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/workflow/paService/submitRequest"
        error_msg = kwargs.pop("error_msg", "提交流程")
        payload = {"requestId": int(request_id), "remark": remark}
        if other_params:
            payload["otherParams"] = other_params
        payload.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            json=payload,
            headers=self._browser_headers(
                origin=True,
                accept="application/json, text/javascript, */*; q=0.01",
            ),
            error_msg=error_msg,
        )

    @allure.step("接口：获取可创建流程的表单定义")
    def get_create_workflow_request_info(self, workflow_id, status_code=200, **kwargs):
        """获取指定流程模板的可创建表单定义（主表字段、必填项等）。

        Args:
            workflow_id: 流程模板 ID。
            status_code: 期望 HTTP 状态码。
            **kwargs: 其它请求参数。

        Returns:
            dict: PA 响应，code 为 SUCCESS 时 data 为 WorkflowRequestInfo，
                含 workflowMainTableInfo.requestRecords[].workflowRequestTableFields[]
                （每个字段含 fieldName/fieldValue/fieldHtmlType/isMand 等），
                用于运行时构造 mainData。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/workflow/paService/getCreateWorkflowRequestInfo"
        error_msg = kwargs.pop("error_msg", "获取可创建流程的表单定义")
        params = {"workflowId": int(workflow_id)}
        params.update(kwargs)
        return self.get(
            url,
            status_code=status_code,
            params=params,
            headers=self._browser_headers(
                accept="application/json, text/javascript, */*; q=0.01",
            ),
            error_msg=error_msg,
        )

    @allure.step("接口：查询流程状态")
    def get_request_status(self, request_id, status_code=200, **kwargs):
        """查询流程当前状态、当前节点、当前操作人等信息。

        Args:
            request_id: 流程请求 ID。
            status_code: 期望 HTTP 状态码。
            **kwargs: 其它请求参数。

        Returns:
            dict: PA 响应，code 为 SUCCESS 时 data 为 RequestInfoEntity，
                含 currentNodeId/currentNodeName/currentNodeType/status 等字段。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-25
        # IsAI: True
        url = "/api/workflow/paService/getRequestStatus"
        error_msg = kwargs.pop("error_msg", "查询流程状态")
        params = {"requestId": int(request_id)}
        params.update(kwargs)
        return self.get(
            url,
            status_code=status_code,
            params=params,
            headers=self._browser_headers(
                accept="application/json, text/javascript, */*; q=0.01",
            ),
            error_msg=error_msg,
        )

    @allure.step("接口：流程强制归档")
    def do_force_over(self, request_id, remark="", status_code=200, **kwargs):
        """调用公开 API 强制归档指定流程。

        Args:
            request_id: 流程请求 ID。
            remark: 签字意见，可空。
            status_code: 期望 HTTP 状态码。
            **kwargs: 可传 other_params（监控归档等）及其余 JSON 字段。

        Returns:
            dict: PA 响应，含 code（SUCCESS / PARAM_ERROR / NO_PERMISSION 等）。
        """
        # Author:dengwanpeng
        # Create Date:2026-08-13
        # IsAI: True
        url = "/api/workflow/paService/doForceOver"
        error_msg = kwargs.pop("error_msg", "流程强制归档")
        other_params = kwargs.pop("other_params", None)
        payload = {
            "requestId": int(request_id),
            "remark": remark,
        }
        if other_params is not None:
            payload["otherParams"] = other_params
        payload.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            json=payload,
            headers=self._browser_headers(
                origin=True,
                accept="application/json, text/javascript, */*; q=0.01",
            ),
            error_msg=error_msg,
        )

    @allure.step("接口：加载流程表单")
    def load_form(self, request_id, workflow_id, status_code=200, **kwargs):
        """加载指定流程的表单（loadForm）。

        后端实现 ``RequestFormAction.loadForm``（类级 ``@Path("/workflow/reqform")``
        → ``@Path("/loadForm")``）→ ``LoadParamCmd.execute``：加载表单时经
        ``secLevelBiz.getSecLevelByRequestId(requestid)`` 取密级，密级无权限时把
        ``HrmClassifiedProtectionBiz.getResourceClassificationTip`` 返回的提示
        写入 ``params.secretMsg``（r349134 变更点透出位置）；未开启分级保护时
        正常返回表单参数。

        Args:
            request_id: 流程请求 ID。
            workflow_id: 流程模板 ID。
            status_code: 期望 HTTP 状态码，默认 200。

        Returns:
            dict: 接口响应 JSON，含 ``status`` 与 ``params``（含可选 ``secretMsg``）。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-26
        # IsAI: True
        url = "/api/workflow/reqform/loadForm"
        error_msg = kwargs.pop("error_msg", "加载流程表单")
        form_data = {
            "requestid": str(request_id),
            "workflowid": str(workflow_id),
        }
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )
