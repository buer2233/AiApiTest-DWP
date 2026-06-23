from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_XML = PROJECT_ROOT / ".idea" / "workspace.xml"


def read_workspace_xml():
    if not WORKSPACE_XML.exists():
        pytest.skip("PyCharm workspace.xml is local IDE state and is not present.")
    return WORKSPACE_XML.read_text(encoding="utf-8")


def test_pycharm_run_configurations_do_not_use_root_test_case_directory():
    workspace = read_workspace_xml()

    assert "$PROJECT_DIR$/test_case" not in workspace
    assert "D:\\AI\\AiApiTest-DWP\\test_case" not in workspace


def test_pycharm_run_configurations_use_api_test_working_directory():
    workspace = read_workspace_xml()

    assert "$PROJECT_DIR$/api-test/test_case/test_gbif_case" in workspace
    assert "$PROJECT_DIR$/api-test/runpytest.py" in workspace
