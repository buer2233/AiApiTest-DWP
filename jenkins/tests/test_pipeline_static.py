from pathlib import Path


JENKINS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = JENKINS_ROOT.parent


def read_pipeline_files():
    return {
        "Jenkinsfile": (JENKINS_ROOT / "Jenkinsfile").read_text(encoding="utf-8"),
        "api-test-pipeline.groovy": (
            JENKINS_ROOT / "scripts" / "api-test-pipeline.groovy"
        ).read_text(encoding="utf-8"),
    }


def test_pipeline_defines_required_parameters():
    files = read_pipeline_files()
    combined = "\n".join(files.values())

    for parameter in [
        "CASE_PATH",
        "PYTEST_NODE_IDS",
        "RETRY_MODE",
        "RETRY_COUNT",
        "CLEAN_ALLURE",
        "OPEN_REPORT",
    ]:
        assert parameter in combined

    assert "test_case/test_gbif_case" in combined
    assert "none" in combined
    assert "selected" in combined
    assert "all-failed" in combined
    assert "module" in combined


def test_pipeline_declares_required_stages_and_unix_windows_branches():
    files = read_pipeline_files()
    combined = "\n".join(files.values())

    for stage_name in [
        "Checkout",
        "Prepare Python",
        "Install API Test Requirements",
        "Run API Tests",
        "Generate Allure Report",
        "Archive Runtime Artifacts",
        "Publish Allure",
    ]:
        assert f"stage('{stage_name}')" in combined or f'stage("{stage_name}")' in combined

    assert "isUnix()" in combined
    assert "sh " in combined
    assert "bat " in combined


def test_pipeline_delegates_pytest_execution_to_ci_runner():
    files = read_pipeline_files()
    combined = "\n".join(files.values())

    assert "-m tools.ci_runner" in combined
    assert "--case-path" not in combined
    assert "--node-id" not in combined
    assert "--retry-mode" not in combined
    assert "PYTEST_NODE_IDS" in combined
    assert "archiveArtifacts" in combined
    assert "allure" in combined


def test_pipeline_preserves_artifacts_when_pytest_fails():
    files = read_pipeline_files()
    combined = "\n".join(files.values())

    assert "catchError" in combined
    assert "stageResult: 'FAILURE'" in combined


def test_jenkinsfile_loads_pipeline_script_inside_node_context():
    jenkinsfile = read_pipeline_files()["Jenkinsfile"]

    assert jenkinsfile.index("node") < jenkinsfile.index("load 'jenkins/scripts/api-test-pipeline.groovy'")


def test_pipeline_can_skip_checkout_for_local_mounted_repository_jobs():
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "LOCAL_WORKSPACE_REPO" in pipeline
    assert "checkout scm" in pipeline


def test_pipeline_uses_python_virtual_environment_for_dependencies():
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "python -m venv .venv" in pipeline
    assert ".venv/bin/python" in pipeline
    assert ".venv\\\\Scripts\\\\python" in pipeline


def test_pipeline_fails_when_allure_html_report_is_not_generated():
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "allure_report_status" in pipeline
    assert "Allure HTML report was not generated" in pipeline
    assert "SystemExit(1)" in pipeline or "sys.exit" in pipeline
