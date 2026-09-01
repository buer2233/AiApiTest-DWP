"""E9+AI 框架迁移后的结构与平台执行契约测试。"""

import importlib
import json
from pathlib import Path

import pytest
import yaml


API_TEST_ROOT = Path(__file__).resolve().parents[1]


EXPECTED_API_MODULES = {
    "board": "page_api.board_api.board_api:BoardAPI",
    "doc_func": "page_api.doc_func_api.doc_func_api:DocFuncAPI",
    "ec": "page_api.ec_api.ec_api:EcAPI",
    "email_view": "page_api.email_view_api.email_view_api:EmailViewAPI",
    "formmode": "page_api.formmode_api.formmode_api:FormmodeAPI",
    "login": "page_api.login_api.login_api:LoginAPI",
    "odoc_file": "page_api.odoc_file_api.odoc_file_api:OdocFileAPI",
    "portal": "page_api.portal_api.portal_api:PortalAPI",
    "system_doc": "page_api.system_doc_api.system_doc_api:SystemDocAPI",
    "system_export": "page_api.system_export_api.system_export_api:SystemExportAPI",
    "workflow": "page_api.workflow_api.workflow_base_api:WorkflowAPI",
    "workflow_formula": "page_api.workflow_api.workflow_formula_api:WorkflowFormulaAPI",
    "workflow_import": "page_api.workflow_import_api.workflow_import_api:WorkflowImportAPI",
}


def _load_symbol(reference):
    module_name, symbol_name = reference.split(":")
    return getattr(importlib.import_module(module_name), symbol_name)


def test_all_migrated_e9_api_modules_are_importable():
    """所有已迁移接口方法模块必须能被平台进程直接导入。"""
    for module_name, reference in EXPECTED_API_MODULES.items():
        symbol = _load_symbol(reference)
        assert symbol.__name__.endswith("API"), module_name


def test_all_migrated_case_directories_are_present():
    """每个 E9 业务模块的 pytest 用例目录必须保留。"""
    expected = {
        "test_board_case",
        "test_doc_func_case",
        "test_email_case",
        "test_formmode_case",
        "test_login_case",
        "test_odoc_file_case",
        "test_system_doc_case",
        "test_workflow_case",
    }
    actual = {path.name for path in (API_TEST_ROOT / "test_case").iterdir() if path.is_dir()}
    assert expected <= actual


def test_all_migrated_case_directories_are_registered_for_platform():
    """平台模块目录必须覆盖所有迁移后的一级业务用例目录。"""
    catalog = yaml.safe_load(
        (API_TEST_ROOT / "utils" / "package_module.yaml").read_text(encoding="utf-8")
    )
    case_directories = {
        path.name
        for path in (API_TEST_ROOT / "test_case").iterdir()
        if path.is_dir() and path.name.startswith("test_") and path.name.endswith("_case")
    }
    assert case_directories <= set(catalog)


def test_ci_runner_exposes_platform_execution_contract():
    """平台必须继续通过统一 runner 支持模块、选中用例和全部失败重试。"""
    from tools.ci_runner import VALID_RETRY_MODES, build_pytest_command

    assert {"none", "module", "selected", "all-failed"} <= VALID_RETRY_MODES
    command = build_pytest_command(
        ["test_case/test_board_case"],
        API_TEST_ROOT / "runtime" / "ci-runs" / "migration" / "allure-results",
        retry_count=2,
    )
    assert "--reruns" in command
    assert "tools.pytest_case_reporter" in command
    assert any(str(item).endswith("case_results.json") for item in command)


def test_migrated_tooling_resolves_current_api_test_root():
    """迁移工具不能依赖源项目的 .workbuddy 安装位置。"""
    from skill_utils.project_root import resolve_project_root

    assert resolve_project_root() == API_TEST_ROOT


def test_login_fixture_uses_platform_base_url(monkeypatch):
    """业务登录必须使用 pytest --base-url 解析出的平台目标地址。"""
    case_conftest = importlib.import_module("test_case.conftest")
    created = {}

    class FakeLoginAPI:
        def __init__(self, base_url=None):
            created["base_url"] = base_url

        def get_rsa_info(self):
            return {}

        def check_login(self, **kwargs):
            return {"msgcode": "0", "loginstatus": "true"}

        def remind_login(self):
            return {}

        def is_weak_password(self, **kwargs):
            return {}

        def get_os_info(self):
            return {}

        @staticmethod
        def safe_login_fields(response):
            return response

    monkeypatch.setattr(case_conftest, "LoginAPI", FakeLoginAPI)
    monkeypatch.setattr(
        case_conftest,
        "APIContext",
        lambda api, caller=None: {"api": api, "caller": caller},
    )
    monkeypatch.setattr(
        case_conftest,
        "load_account",
        lambda role: {"user_name": "placeholder", "password": "placeholder"},
    )

    case_conftest.login_admin.__wrapped__("https://registered.example.invalid/e9")

    assert created["base_url"] == "https://registered.example.invalid/e9"


def test_business_cases_do_not_contain_fixed_failure_probe():
    """平台日常全量用例不得包含用于报告演示的必然失败探针。"""
    board_case = (
        API_TEST_ROOT / "test_case" / "test_board_case" / "test_board_widget_api.py"
    ).read_text(encoding="utf-8")
    assert "test_allure_failure_analysis_probe" not in board_case


def test_generated_api_index_is_not_versioned():
    """接口索引是可再生文件，不能携带源机器绝对路径进入仓库。"""
    assert not (API_TEST_ROOT / "tools" / "page_api_index.sqlite3").exists()


def test_jenkins_runner_accepts_e9_base_url_alias(tmp_path):
    """Jenkins 未提供 TARGET_BASE_URL 时可用 E9_BASE_URL 传递目标环境。"""
    from tools.ci_runner import build_run_request_from_jenkins_env

    (tmp_path / "utils").mkdir()
    (tmp_path / "utils" / "package_environment.yaml").write_text(
        "e9-test:\n  base_url: https://registered.example.invalid/api\n"
        "  url_name: E9\n  url_desc: 测试\n",
        encoding="utf-8",
    )
    request = build_run_request_from_jenkins_env(
        {
            "RETRY_MODE": "module",
            "RUN_ID": "migration-base-url",
            "E9_BASE_URL": "https://registered.example.invalid/api",
        },
        api_test_root=tmp_path,
    )
    assert request.base_url == "https://registered.example.invalid/api"


def test_load_account_maps_employee_credentials_by_role(monkeypatch):
    """员工 fixture 必须按 employee<n> 角色读取对应的 CI 凭据。"""
    common = importlib.import_module("utils.common_function")
    monkeypatch.delenv("E9_LOGINID", raising=False)
    monkeypatch.delenv("E9_USERPASSWORD", raising=False)
    monkeypatch.setenv("E9_EMPLOYEE2_LOGINID", "employee-two")
    monkeypatch.setenv("E9_EMPLOYEE2_PASSWORD", "employee-two-password")

    assert common.load_account("employee2") == {
        "user_name": "employee-two",
        "password": "employee-two-password",
    }


def test_config_accepts_target_base_url_environment_alias(monkeypatch):
    """容器侧未使用 E9_BASE_URL 时，TARGET_BASE_URL 仍可覆盖默认环境。"""
    monkeypatch.delenv("E9_BASE_URL", raising=False)
    monkeypatch.setenv("TARGET_BASE_URL", "https://registered.example.invalid/e9")
    config_module = importlib.import_module("config")

    assert config_module._load_root_base_url() == "https://registered.example.invalid/e9"


def test_load_account_rejects_partial_employee_credentials(monkeypatch):
    """员工账号只配置一半时必须明确失败，避免带着无效登录态执行。"""
    common = importlib.import_module("utils.common_function")
    monkeypatch.delenv("E9_EMPLOYEE3_LOGINID", raising=False)
    monkeypatch.setenv("E9_EMPLOYEE3_PASSWORD", "only-password")

    with pytest.raises(pytest.fail.Exception, match="E9_EMPLOYEE3_LOGINID"):
        common.load_account("employee3")


def test_load_account_reads_role_credentials_from_jenkins_secret_json(monkeypatch):
    """Jenkins Secret Text 账号 JSON 必须支持管理员和员工角色读取。"""
    common = importlib.import_module("utils.common_function")
    for key in (
        "E9_LOGINID",
        "E9_USERPASSWORD",
        "E9_EMPLOYEE1_LOGINID",
        "E9_EMPLOYEE1_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(
        "E9_ACCOUNTS_JSON",
        json.dumps(
            {
                "admin": {"user_name": "admin-json", "password": "admin-json-pass"},
                "employee1": {
                    "user_name": "employee-json",
                    "password": "employee-json-pass",
                },
            }
        ),
    )

    assert common.load_account("admin") == {
        "user_name": "admin-json",
        "password": "admin-json-pass",
    }
    assert common.load_account("employee1") == {
        "user_name": "employee-json",
        "password": "employee-json-pass",
    }
