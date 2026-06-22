import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_TEST_ROOT = Path(__file__).resolve().parents[1]


def load_module_from_api_test(module_name):
    module_path = API_TEST_ROOT / f"{module_name}.py"
    assert module_path.is_file(), f"{module_path} should exist after api-test migration"
    sys.path.insert(0, str(API_TEST_ROOT))
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(API_TEST_ROOT))


def test_framework_files_are_moved_under_api_test():
    expected_items = [
        "report",
        "test_case",
        "test_data",
        "utils",
        "config.py",
        "conftest.py",
        "pytest.ini",
        "requirements.txt",
        "runpytest.py",
    ]

    for item in expected_items:
        assert (API_TEST_ROOT / item).exists(), f"api-test/{item} should exist"
        assert not (PROJECT_ROOT / item).exists(), f"root {item} should be moved into api-test"


def test_config_paths_are_api_test_relative():
    config = load_module_from_api_test("config")

    assert Path(config.base_dir) == API_TEST_ROOT
    assert Path(config.test_case_dir) == API_TEST_ROOT / "test_case"
    assert Path(config.test_data_dir) == API_TEST_ROOT / "test_data"
    assert Path(config.report_dir) == API_TEST_ROOT / "report"
    assert Path(config.allure_results_dir) == API_TEST_ROOT / "report" / "allure-results"
    assert Path(config.allure_report_dir) == API_TEST_ROOT / "report" / "allure-report"
    assert Path(config.runtime_dir) == API_TEST_ROOT / "runtime"
    assert Path(config.logs_dir) == API_TEST_ROOT / "logs"


def test_build_pytest_command_uses_api_test_allure_results_by_default():
    runpytest = load_module_from_api_test("runpytest")

    command = runpytest.build_pytest_command(
        case_path="test_case/test_gbif_case",
        marker="smoke",
        clean=True,
    )

    assert command[:4] == ["python", "-m", "pytest", "test_case/test_gbif_case"]
    assert f"--alluredir={API_TEST_ROOT / 'report' / 'allure-results'}" in command
    assert ["-m", "smoke"] == command[5:7]
    assert "--clean-alluredir" in command


def test_build_allure_generate_command_uses_api_test_report_dirs():
    runpytest = load_module_from_api_test("runpytest")
    report_dir = API_TEST_ROOT / "report" / "allure-report" / "fixed"

    command = runpytest.build_allure_generate_command(report_dir=report_dir)

    assert command == [
        "allure",
        "generate",
        str(API_TEST_ROOT / "report" / "allure-results"),
        "-o",
        str(report_dir),
    ]


def test_ensure_runtime_dirs_creates_api_test_directories():
    runpytest = load_module_from_api_test("runpytest")

    runpytest.ensure_runtime_dirs()

    expected_dirs = [
        API_TEST_ROOT / "report",
        API_TEST_ROOT / "runtime",
        API_TEST_ROOT / "logs",
        API_TEST_ROOT / "report" / "allure-results",
        API_TEST_ROOT / "report" / "allure-report",
    ]
    for directory in expected_dirs:
        assert directory.is_dir(), f"{directory} should be created under api-test"
