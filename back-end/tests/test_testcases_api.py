import pytest
from django.test import override_settings

from apps.testcases.models import TestCaseItem
from apps.testcases.services.scanner import sync_pytest_cases


@pytest.mark.django_db
def test_admin_can_sync_pytest_cases(auth_client, admin_user):
    client = auth_client(admin_user)

    response = client.post("/api/v1/test-cases/sync")

    assert response.status_code == 200
    assert response.data["data"]["total"] >= 1
    assert TestCaseItem.objects.filter(node_id__contains="::test_").exists()


@pytest.mark.django_db
def test_member_cannot_sync_pytest_cases(auth_client, member_user):
    client = auth_client(member_user)

    response = client.post("/api/v1/test-cases/sync")

    assert response.status_code == 403


@pytest.mark.django_db
def test_sync_is_idempotent_by_node_id(auth_client, admin_user):
    client = auth_client(admin_user)

    first = client.post("/api/v1/test-cases/sync")
    initial_count = TestCaseItem.objects.count()
    second = client.post("/api/v1/test-cases/sync")

    assert first.status_code == 200
    assert second.status_code == 200
    assert TestCaseItem.objects.count() == initial_count
    assert second.data["data"]["updated"] >= 1


@pytest.mark.django_db
def test_authenticated_user_can_list_search_and_filter_test_cases(auth_client, member_user):
    TestCaseItem.objects.create(
        node_id="test_case/test_demo/test_demo_api.py::TestDemo::test_login",
        package_name="test_demo",
        module_name="Demo 模块",
        file_path="api-test/test_case/test_demo/test_demo_api.py",
        class_name="TestDemo",
        function_name="test_login",
        title="登录接口",
        description="验证登录接口",
    )
    TestCaseItem.objects.create(
        node_id="test_case/test_other/test_other_api.py::test_other",
        package_name="test_other",
        module_name="Other 模块",
        file_path="api-test/test_case/test_other/test_other_api.py",
        function_name="test_other",
        title="其他接口",
    )
    client = auth_client(member_user)

    response = client.get("/api/v1/test-cases", {"keyword": "登录", "package_name": "test_demo"})

    assert response.status_code == 200
    assert response.data["meta"]["total"] == 1
    assert response.data["data"][0]["function_name"] == "test_login"


@pytest.mark.django_db
def test_test_case_list_returns_empty_state_shape(auth_client, member_user):
    client = auth_client(member_user)

    response = client.get("/api/v1/test-cases", {"keyword": "not-match"})

    assert response.status_code == 200
    assert response.data["data"] == []
    assert response.data["meta"]["total"] == 0


@pytest.mark.django_db
def test_test_case_list_rejects_invalid_sync_status(auth_client, member_user):
    client = auth_client(member_user)

    response = client.get("/api/v1/test-cases", {"sync_status": "bad"})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_sync_source_missing_returns_contract_error(auth_client, admin_user, tmp_path, settings):
    missing_dir = tmp_path / "missing-test-case-dir"
    settings.TEST_CASE_SOURCE_DIR = missing_dir
    client = auth_client(admin_user)

    response = client.post("/api/v1/test-cases/sync")

    assert response.status_code == 500
    assert response.data["error"]["code"] == "sync_source_missing"


@pytest.mark.django_db
def test_scanner_uses_allure_title_without_docstring(tmp_path, settings):
    source_dir = tmp_path / "api-test" / "test_case"
    module_dir = source_dir / "test_demo"
    module_dir.mkdir(parents=True)
    test_file = module_dir / "test_demo_api.py"
    test_file.write_text(
        "import allure\n\n"
        "@allure.title('Allure 标题')\n"
        "def test_title_only():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    settings.TEST_CASE_SOURCE_DIR = source_dir
    settings.REPO_ROOT = tmp_path

    sync_pytest_cases()

    item = TestCaseItem.objects.get(function_name="test_title_only")
    assert item.title == "Allure 标题"


@pytest.mark.django_db
def test_scanner_uses_allure_story_without_docstring(tmp_path, settings):
    source_dir = tmp_path / "api-test" / "test_case"
    module_dir = source_dir / "test_demo"
    module_dir.mkdir(parents=True)
    test_file = module_dir / "test_demo_story_api.py"
    test_file.write_text(
        "import allure\n\n"
        "@allure.story('Allure Story')\n"
        "def test_story_only():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    settings.TEST_CASE_SOURCE_DIR = source_dir
    settings.REPO_ROOT = tmp_path

    sync_pytest_cases()

    item = TestCaseItem.objects.get(function_name="test_story_only")
    assert item.title == "Allure Story"
