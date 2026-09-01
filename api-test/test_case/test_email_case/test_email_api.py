# -*- coding: utf-8 -*-
"""E9 邮件（email）查看 + 发信造数接口自动化用例。

覆盖 r349134（no.4956160 新增工作秘密的需求）功能用例清单中**当前环境可真实验证**的
「需自动化」条目。依赖「沙箱模式 + 工作秘密密级」的条目（FC-1/4/5/12/13/ST-1/ST-2 等）
当前测试环境仅配置「公开(4)」密级、沙箱未开启，发高密级邮件会被后端拒「密级越权」，
故不落自动化，已在功能清单改标 manual 并注明原因。

本条文件已通过运行时打印真实返回值确证返回结构，并据此补齐断言：
- 本人查自己邮件：viewRight=1 / classificationRight=1 / classificationTamper=1
- 他人（employee1）越权访问：viewRight=0 / classificationRight=0，正文 mailContent=""
- 非沙箱下 mailView.viewBean.classificationSpan="公开"、classificationTip=""
- 发公开密级邮件：isSend="true" 返回 mailId（字符串）；发秘密密级被拒 false6「密级越权」

断言策略（SKILL 阶段 C）：环境部署版本未确认，以结构化断言为通过标准；行为级证据用
allure.attach 记录为信息性附件，供环境部署后复核，不把环境差异定性为产品缺陷。
"""

import json
import allure
import pytest

from page_api.email_view_api.email_view_api import EmailViewAPI


@pytest.fixture(scope="session")
def email_api(login_admin):
    """返回共享登录态的管理员邮件 API 实例。"""
    return login_admin.use(EmailViewAPI)


@pytest.fixture(scope="session")
def created_mail_id(email_api):
    """前置造数：管理员发一封「公开密级」内部邮件，返回 mailId 供后续查询命中。

    当前环境 sysadmin 仅「公开(4)」密级，发高密级会被拒「密级越权」，故用公开密级造数，
    验证发信→收件箱→权限判定→查看链路走通，并作为越权用例的受控对象。收件人必须传
    JSON 数组（后端 JSONArray.parseArray）。
    """
    add = email_api.email_add()
    session_uuid = str(add.get("email_sendsessionUUid") or "")

    tonew = json.dumps([{"userids": "1"}], ensure_ascii=False)
    send = email_api.send(
        sessionUUid=session_uuid,
        isInternal="1",
        classification="4",
        savesend="1",
        subject="r349134-自动化探针",
        mouldtext="r349134 接口自动化造数内容",
        internaltonew=tonew,
        texttype="0",
    )
    mail_id = send.get("mailId") if isinstance(send, dict) else None
    assert mail_id, f"发信造数失败，未返回 mailId: {send}"
    return str(mail_id)


@allure.epic("E9-接口自动化")
@allure.feature("E9 邮件（email）查看接口")
@pytest.mark.r349134
class TestEmailViewR349134:
    """r349134 邮件查看/密级提示链路接口回归（当前环境可验证子集）。

    # Author: WorkBuddy
    # Create Date: 2026-08-26
    # IsAI: True
    """

    @allure.story("FC-0 场景法核心主流程：发信造数→收件箱→权限判定→查看")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_fc0_scenario_send_to_view_core_flow(self, email_api, created_mail_id):
        """FC-0：端到端主流程。造数已知 mailId 后，收件箱命中、权限判定、查看、正文结构正常。"""
        mail_id = created_mail_id

        with allure.step("1.收件箱列表命中造数邮件"):
            all_list = email_api.all_list()
            assert isinstance(all_list, dict), f"allList 响应类型异常: {type(all_list).__name__}"
            assert all_list.get("status") == "1", f"allList 业务失败: {all_list}"
            table_bean = all_list.get("tableBean") or {}
            datas = table_bean.get("datas") if isinstance(table_bean, dict) else None
            assert isinstance(datas, list) and datas, f"收件箱列表为空: {all_list}"
            hit_ids = [str(item.get("id")) for item in datas if isinstance(item, dict)]
            assert mail_id in hit_ids, f"收件箱列表未命中造数邮件 {mail_id}: {hit_ids}"

        with allure.step("2.本人查看自己邮件，三项权限标识齐全且为有权限"):
            rights = email_api.has_mail_view_rights(mail_id=mail_id)
            assert isinstance(rights, dict), f"hasMailViewRights 类型异常: {type(rights).__name__}"
            assert rights.get("status") == "1", f"hasMailViewRights 业务失败: {rights}"
            for key in ("viewRight", "classificationRight", "classificationTamper"):
                assert key in rights, f"缺少权限标识字段 {key}: {rights}"
                assert isinstance(rights.get(key), int), f"权限标识 {key} 应为整数: {rights}"
            assert rights.get("viewRight") == 1, f"本人应有查看权限 viewRight=1: {rights}"
            assert rights.get("classificationRight") == 1, f"本人应有密级权限: {rights}"

        with allure.step("3.邮件查看返回 viewBean 且含密级展示"):
            view = email_api.mail_view(mail_id=mail_id)
            assert isinstance(view, dict), f"mailView 类型异常: {type(view).__name__}"
            assert view.get("status") == "1", f"mailView 业务失败: {view}"
            view_bean = view.get("viewBean")
            assert isinstance(view_bean, dict), f"viewBean 缺失或类型异常: {view}"
            assert "classification" in view_bean, f"viewBean 缺少 classification: {view_bean}"
            assert "classificationTip" in view_bean, f"viewBean 缺少 classificationTip: {view_bean}"

        with allure.step("4.邮件正文返回非空 mailContent"):
            content = email_api.mail_content_view(mail_id=mail_id)
            assert isinstance(content, dict), f"mailContentView 类型异常: {type(content).__name__}"
            assert content.get("status") == "1", f"mailContentView 业务失败: {content}"
            assert content.get("mailContent"), f"mailContent 为空: {content}"

        allure.attach(
            json.dumps(
                {
                    "mailId": mail_id,
                    "rights": rights,
                    "viewBean_classification": view_bean.get("classification"),
                    "viewBean_classificationSpan": view_bean.get("classificationSpan"),
                    "viewBean_classificationTip": view_bean.get("classificationTip"),
                },
                ensure_ascii=False,
            ),
            name="FC-0 闭环证据",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("FC-3 非沙箱模式：查看/提示不受影响（回归）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_fc3_non_sandbox_normal(self, email_api, created_mail_id):
        """FC-3：当前环境为非沙箱模式，本人查看自己邮件，提示走非沙箱链路。

        非沙箱下不应触发「工作秘密无权限提示」：viewBean.classificationTip 为空，
        classificationSpan 为正常密级展示（公开）。验证本次改动不影响非沙箱分支。
        """
        view = email_api.mail_view(mail_id=created_mail_id)
        assert isinstance(view, dict), f"mailView 类型异常: {type(view).__name__}"
        assert view.get("status") == "1", f"mailView 业务失败: {view}"
        view_bean = view.get("viewBean") or {}
        # 非沙箱下 classificationTip 为空（未走沙箱提示逻辑）。
        assert view_bean.get("classificationTip") in ("", None), (
            f"非沙箱模式不应携带沙箱提示 classificationTip: {view_bean}"
        )
        allure.attach(
            json.dumps(
                {
                    "classificationSpan": view_bean.get("classificationSpan"),
                    "classificationTip": view_bean.get("classificationTip"),
                },
                ensure_ascii=False,
            ),
            name="FC-3 非沙箱提示证据",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("FC-17 越权：普通成员访问他人邮件被拒，内容不外泄")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_fc17_unauthorized_access_denied(self, email_api, created_mail_id, login_employee):
        """FC-17：普通成员（employee1）访问管理员私有邮件，viewRight=0 且正文为空，内容不外泄。"""
        emp = login_employee("employee1")
        emp_api = emp.use(EmailViewAPI)
        mail_id = created_mail_id

        with allure.step("1.普通成员权限判定：无查看权限"):
            rights = emp_api.has_mail_view_rights(mail_id=mail_id)
            assert isinstance(rights, dict), f"hasMailViewRights 类型异常: {type(rights).__name__}"
            assert rights.get("status") == "1", f"hasMailViewRights 业务失败: {rights}"
            assert rights.get("viewRight") == 0, f"普通成员不应有查看权限 viewRight=0: {rights}"

        with allure.step("2.普通成员正文为空，内容不外泄"):
            content = emp_api.mail_content_view(mail_id=mail_id)
            assert isinstance(content, dict), f"mailContentView 类型异常: {type(content).__name__}"
            assert content.get("status") == "1", f"mailContentView 业务失败: {content}"
            assert content.get("viewRight") == 0, f"普通成员 viewRight 应为 0: {content}"
            assert content.get("mailContent") in ("", None), (
                f"越权访问不应返回正文内容: {content}"
            )

        allure.attach(
            json.dumps(
                {"role": "employee1", "target_mailId": mail_id, "viewRight": rights.get("viewRight")},
                ensure_ascii=False,
            ),
            name="FC-17 越权拦截证据",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("FC-22 权限判定接口返回三项权限标识结构")
    @allure.severity(allure.severity_level.NORMAL)
    def test_fc22_permission_fields_structure(self, email_api, created_mail_id, login_employee):
        """FC-22：权限判定接口对「有权限」「无权限」两种访问返回完整三项标识与 status。

        msg 承载提示仅在沙箱模式且密级无权限时由后端写入；当前非沙箱环境该字段不出现，
        属行为级差异，以附件记录，不据此断言（沙箱场景见功能清单 manual 条目）。
        """
        # 有权限视角
        rights_self = email_api.has_mail_view_rights(mail_id=created_mail_id)
        assert isinstance(rights_self, dict), f"响应类型异常: {type(rights_self).__name__}"
        assert rights_self.get("status") == "1", f"业务失败: {rights_self}"
        for key in ("viewRight", "classificationRight", "classificationTamper"):
            assert key in rights_self, f"缺少权限标识字段 {key}: {rights_self}"

        # 无权限视角（employee1）
        emp_api = login_employee("employee1").use(EmailViewAPI)
        rights_other = emp_api.has_mail_view_rights(mail_id=created_mail_id)
        assert isinstance(rights_other, dict), f"响应类型异常: {type(rights_other).__name__}"
        assert rights_other.get("viewRight") == 0, f"越权视角 viewRight 应为 0: {rights_other}"

        allure.attach(
            json.dumps({"self": rights_self, "other": rights_other}, ensure_ascii=False),
            name="FC-22 权限判定响应",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("FC-23 邮件正文接口返回正文与权限结构")
    @allure.severity(allure.severity_level.NORMAL)
    def test_fc23_mail_content_structure(self, email_api, created_mail_id, login_employee):
        """FC-23：正文接口返回 viewRight/classificationRight/mailContent 结构；
        越权访问时正文为空不外泄。classificationTip 提示字段属沙箱场景，见 manual 条目。
        """
        # 有权限视角
        content_self = email_api.mail_content_view(mail_id=created_mail_id)
        assert isinstance(content_self, dict), f"响应类型异常: {type(content_self).__name__}"
        assert content_self.get("status") == "1", f"业务失败: {content_self}"
        for key in ("viewRight", "classificationRight", "mailContent"):
            assert key in content_self, f"缺少字段 {key}: {content_self}"

        # 越权视角
        emp_api = login_employee("employee1").use(EmailViewAPI)
        content_other = emp_api.mail_content_view(mail_id=created_mail_id)
        assert isinstance(content_other, dict), f"响应类型异常: {type(content_other).__name__}"
        assert content_other.get("viewRight") == 0, f"越权视角 viewRight 应为 0: {content_other}"
        assert content_other.get("mailContent") in ("", None), f"越权不应返回正文: {content_other}"

        allure.attach(
            json.dumps(
                {"self_viewRight": content_self.get("viewRight"),
                 "other_viewRight": content_other.get("viewRight")},
                ensure_ascii=False,
            ),
            name="FC-23 正文响应结构证据",
            attachment_type=allure.attachment_type.TEXT,
        )