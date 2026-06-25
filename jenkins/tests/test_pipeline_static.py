"""Jenkins Pipeline 静态结构测试。

本文件不启动真实 Jenkins，而是直接读取 Jenkinsfile 和 Groovy 脚本，
验证参数、stage、跨平台分支和 ci_runner 调用契约没有被破坏。
"""

from pathlib import Path


JENKINS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = JENKINS_ROOT.parent


def read_pipeline_files():
    """读取 Jenkinsfile 和可复用 Groovy Pipeline 源码。"""
    return {
        "Jenkinsfile": (JENKINS_ROOT / "Jenkinsfile").read_text(encoding="utf-8"),
        "api-test-pipeline.groovy": (
            JENKINS_ROOT / "scripts" / "api-test-pipeline.groovy"
        ).read_text(encoding="utf-8"),
    }


def test_pipeline_defines_required_parameters():
    """Pipeline 必须暴露前端、后端和 api-test 共同约定的构建参数。"""
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
    """Pipeline 必须包含核心 stage，并同时保留 Linux sh 与 Windows bat 分支。"""
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
    """Jenkins 只负责编排，pytest 执行和重试规则必须委托给 ci_runner。"""
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
    """pytest 用例失败时 Run API Tests 不应把 Jenkins stage 标记为失败。"""
    files = read_pipeline_files()
    combined = "\n".join(files.values())

    run_stage_start = combined.index("stage('Run API Tests')")
    generate_stage_start = combined.index("stage('Generate Allure Report')")
    run_stage = combined[run_stage_start:generate_stage_start]

    assert "catchError" not in run_stage
    assert "stageResult: 'FAILURE'" not in run_stage
    assert "-m tools.ci_runner --from-jenkins-env" in run_stage


def test_jenkinsfile_loads_pipeline_script_inside_node_context():
    """Jenkinsfile 必须在 node workspace 上下文中 load Groovy 脚本。"""
    jenkinsfile = read_pipeline_files()["Jenkinsfile"]

    assert jenkinsfile.index("node") < jenkinsfile.index("load 'jenkins/scripts/api-test-pipeline.groovy'")


def test_pipeline_can_skip_checkout_for_local_mounted_repository_jobs():
    """本地挂载仓库的 Jenkins 容器应支持跳过 scm checkout。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "LOCAL_WORKSPACE_REPO" in pipeline
    assert "checkout scm" in pipeline


def test_pipeline_uses_python_virtual_environment_for_dependencies():
    """Pipeline 应使用 api-test 目录下的 Python 虚拟环境安装依赖。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "python -m venv .venv" in pipeline
    assert ".venv/bin/python" in pipeline
    assert ".venv\\\\Scripts\\\\python" in pipeline


def test_pipeline_fails_when_allure_html_report_is_not_generated():
    """Allure HTML 没有生成时 Pipeline 必须显式失败，不能只归档空结果。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "allure_report_status" in pipeline
    assert "Allure HTML report was not generated" in pipeline
    assert "SystemExit(1)" in pipeline or "sys.exit" in pipeline
