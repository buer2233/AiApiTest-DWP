# -*- coding: utf-8 -*-
"""E9 系统文档接口 r349134 自动化用例。

覆盖 r349134（no.4956160 新增工作秘密的需求）功能用例清单中的
「文件/文档」模块条目 FC-DOC-0（手机端读取文档 canReadDoc 主流程）。

环境约束：当前测试环境分级保护未开启（canReadDoc 返回 hasRightForSecret=true，
即 isOpenClassification() 为 false，直接短路密级判断），r349134 的「工作秘密
密级提示 549160」行为分支不可达。故本用例按 SKILL 阶段 C「结构化断言 + 信息性
附件」口径：验证 canReadDoc 的文档可读性判定链路、越权拦截与边界降级；
密级提示行为差异以 allure.attach 记录为信息性证据，不据此定性产品缺陷。
"""

import json

import allure
import pytest

from page_api.system_doc_api.system_doc_api import SystemDocAPI


@allure.epic("E9-接口自动化")
@allure.feature("E9 系统文档接口（r349134）")
@pytest.mark.r349134
class TestSystemDocR349134:
    """systemDoc canReadDoc 文档可读性/密级提示链路（FC-DOC-0）。

    # Author: WorkBuddy
    # Create Date: 2026-08-26
    # IsAI: True
    """

    @allure.story("FC-DOC-0 手机端文档可读性判定主流程（本人/越权/边界）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_fc_doc0_can_read_doc_main_flow(self, login_admin, login_employee):
        """FC-DOC-0：场景法核心主流程，覆盖 canReadDoc 三段真实结构。

        - 本人读自己文档：canReader=true、hasRightForSecret=true；
        - 普通成员越权读他人文档：canReader=false（权限拦截，内容不外泄）；
        - docid=0 边界：api_status=false、isHaveDoc=0（安全降级，不抛 5xx）。
        """
        admin_api = login_admin.use(SystemDocAPI)

        # 前置：取一个环境已有文档 docid（复用 myDocList，保证查询非空）
        with allure.step("0.获取环境已有文档列表，取一个 docid"):
            doc_list = admin_api.get_my_doc_list()
            assert isinstance(doc_list, dict), f"getMyDocList 类型异常: {type(doc_list).__name__}"
            docs = doc_list.get("docs") or []
            target_docid = None
            if isinstance(docs, list) and docs:
                target_docid = str(docs[0].get("docid") or "")
            if not target_docid:
                pytest.skip("环境无可用文档，无法执行 canReadDoc 主流程")

        with allure.step("1.本人读自己文档，可读且有密级判定标识"):
            resp_self = admin_api.can_read_doc(target_docid)
            assert isinstance(resp_self, dict), f"canReadDoc 类型异常: {type(resp_self).__name__}"
            assert resp_self.get("api_status") is True, f"本人读文档业务失败: {resp_self}"
            assert resp_self.get("canReader") is True, f"本人读自己文档应有可读权限: {resp_self}"
            assert "hasRightForSecret" in resp_self, f"缺少密级判定标识: {resp_self}"

        with allure.step("2.普通成员越权读他人文档，被拦截"):
            emp_api = login_employee("employee1").use(SystemDocAPI)
            resp_other = emp_api.can_read_doc(target_docid)
            assert isinstance(resp_other, dict), f"越权 canReadDoc 类型异常: {type(resp_other).__name__}"
            assert resp_other.get("canReader") is False, f"普通成员越权读他人文档应被拦截: {resp_other}"

        with allure.step("3.docid=0 边界：安全降级不崩溃"):
            resp_zero = admin_api.can_read_doc(0)
            assert isinstance(resp_zero, dict), f"边界 canReadDoc 类型异常: {type(resp_zero).__name__}"
            assert resp_zero.get("isHaveDoc") == "0", f"docid=0 应返回 isHaveDoc=0: {resp_zero}"

        allure.attach(
            json.dumps(
                {
                    "self_hasRightForSecret": resp_self.get("hasRightForSecret"),
                    "other_hasRightForSecret": resp_other.get("hasRightForSecret"),
                    "self_canReader": resp_self.get("canReader"),
                    "other_canReader": resp_other.get("canReader"),
                    "note": "当前环境分级保护未开启，secretMsg 提示字段不出现;"
                            "r349134 的 549160 密级提示分支需环境中开启分级保护后方可达",
                },
                ensure_ascii=False,
            ),
            name="FC-DOC-0 文档可读性判定链路证据",
            attachment_type=allure.attachment_type.TEXT,
        )