# -*- coding: utf-8 -*-
"""E9 表单建模（formmode）模块接口封装。

对应 SVN r349152 修复点：角色受范围限制权限绑定布局不生效。
唯一真实走到该修复代码路径（ModeRightInfo.getLayoutid）的 HTTP 入口为
卡片模版布局基本信息接口 POST /api/formmode/card/layoutBase。
"""

import allure

from page_api.public.base_api import BaseAPI


class FormmodeAPI(BaseAPI):
    """E9 表单建模卡片相关接口。"""

    @allure.step("接口：卡片模版布局基本信息")
    def layout_base(
        self,
        mode_id,
        form_id,
        type_,
        billid="",
        json_str="{}",
        status_code=200,
        **kwargs,
    ):
        """获取卡片模版布局基本信息（layoutBase）。

        该接口在查看（type=0）与编辑（type=2）场景下会经
        ResolveFormMode.initLayoutInfo -> getLayoutIdOfModeright -> ModeRightInfo.getLayoutid
        解析权限布局，即 r349152 的修复路径。

        Args:
            mode_id: 模块 id（modeinfo 主键）。
            form_id: 表单 id（formId）。
            type_: 布局类型：0-查看 1-新建 2-编辑。
            billid: 单据主键；查看/编辑场景传真实 billid 才能触发限定范围权限布局解析。
            json_str: JSONStr 参数，默认空对象 "{}"。
            status_code: 期望 HTTP 状态码。
        """
        # Author: WorkBuddy
        # Create Date: 2026-08-19
        # IsAI: True
        url = "/api/formmode/card/layoutBase"
        error_msg = kwargs.pop("error_msg", "获取卡片模版布局基本信息")
        form_data = {
            "modeId": str(mode_id),
            "formId": str(form_id),
            "type": str(type_),
            "billid": str(billid),
            "JSONStr": json_str,
        }
        form_data.update(kwargs)
        return self.post(
            url,
            status_code=status_code,
            data=form_data,
            headers=self._browser_headers(form=True, origin=True),
            error_msg=error_msg,
        )