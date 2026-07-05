"""Jenkins Pipeline 静态结构测试。

本文件不启动真实 Jenkins，而是直接读取 Jenkinsfile 和 Groovy 脚本，
验证参数、stage、跨平台分支和 ci_runner 调用契约没有被破坏。
"""

from pathlib import Path


JENKINS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = JENKINS_ROOT.parent

BUSINESS_PIPELINES = {
    "daily-full-module": {
        "jenkinsfile": "Jenkinsfile.daily-full-module",
        "script": "daily-full-module-pipeline.groovy",
        "retry_mode": "none",
        "must_have": ["CASE_PATH", "MODULE_NAME", "RETRY_COUNT", "CLEAN_ALLURE", "OPEN_REPORT"],
        "must_not_have": ["choice(\n                name: 'RETRY_MODE'", "all-failed"],
        "cron": "cron('0 2 * * *')",
        "case_path_env": "JENKINS_MODULE_CASE_PATH",
        "empty_case_path_message": "CASE_PATH is required for this Jenkins job",
    },
    "failed-rerun": {
        "jenkinsfile": "Jenkinsfile.failed-rerun",
        "script": "failed-rerun-pipeline.groovy",
        "retry_mode": "selected",
        "must_have": ["CASE_PATH", "PYTEST_NODE_IDS", "RETRY_COUNT", "CLEAN_ALLURE", "OPEN_REPORT"],
        "must_not_have": ["cron('0 2 * * *')", "all-failed"],
        "empty_node_ids_message": "PYTEST_NODE_IDS is required for failed rerun",
    },
    "module-rerun": {
        "jenkinsfile": "Jenkinsfile.module-rerun",
        "script": "module-rerun-pipeline.groovy",
        "retry_mode": "module",
        "must_have": ["CASE_PATH", "MODULE_NAME", "RETRY_COUNT", "CLEAN_ALLURE", "OPEN_REPORT"],
        "must_not_have": ["cron('0 2 * * *')", "PYTEST_NODE_IDS", "all-failed"],
    },
}


def read_required_text(path):
    """读取必须存在的文件；不存在时给出清晰的契约失败信息。"""
    assert path.exists(), f"Missing required Jenkins pipeline file: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def read_pipeline_files():
    """读取 Jenkinsfile 和可复用 Groovy Pipeline 源码。"""
    return {
        "Jenkinsfile": (JENKINS_ROOT / "Jenkinsfile").read_text(encoding="utf-8"),
        "api-test-pipeline.groovy": (
            JENKINS_ROOT / "scripts" / "api-test-pipeline.groovy"
        ).read_text(encoding="utf-8"),
    }


def read_business_pipeline_files():
    """读取三条业务 Pipeline 的 Jenkinsfile 和 Groovy 脚本。"""
    files = {}
    for name, config in BUSINESS_PIPELINES.items():
        files[f"{name}:jenkinsfile"] = read_required_text(JENKINS_ROOT / config["jenkinsfile"])
        files[f"{name}:script"] = read_required_text(
            JENKINS_ROOT / "scripts" / config["script"]
        )
    return files


def combined_business_pipeline_source():
    """合并三条业务 Pipeline 源码，便于检查共享契约。"""
    shared = read_pipeline_files()["api-test-pipeline.groovy"]
    return "\n".join([shared, *read_business_pipeline_files().values()])


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

    assert "JENKINS_DEFAULT_CASE_PATH" in combined
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


def test_pipeline_uses_sandbox_safe_environment_default_access():
    """Jenkins sandbox 不允许 env[...] 动态下标，参数默认值必须显式读取环境变量。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    parameter_block = pipeline[
        pipeline.index("def buildParameterDefinitions") : pipeline.index("// Jenkins job 参数必须")
    ]

    assert "env[" not in parameter_block
    assert "env.JENKINS_MODULE_CASE_PATH" in parameter_block
    assert "env.JENKINS_DEFAULT_CASE_PATH" in parameter_block


def test_pipeline_uses_python_virtual_environment_for_dependencies():
    """Pipeline 应使用 api-test 目录下的 Python 虚拟环境安装依赖。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "JENKINS_API_TEST_DIR" in pipeline
    assert "JENKINS_PYTHON_VENV_DIR" in pipeline
    assert "python -m venv ${pythonVenvDir}" in pipeline
    assert "python -m venv .venv" not in pipeline
    assert "/bin/python" in pipeline
    assert "\\\\Scripts\\\\python" in pipeline


def test_pipeline_fails_when_allure_html_report_is_not_generated():
    """Allure HTML 没有生成时 Pipeline 必须显式失败，不能只归档空结果。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "allure_report_status" in pipeline
    assert "Allure HTML report was not generated" in pipeline
    assert "SystemExit(1)" in pipeline or "sys.exit" in pipeline


def test_business_pipeline_files_exist_and_jenkinsfiles_load_expected_scripts():
    """三类 Jenkins 任务必须有独立 Jenkinsfile，并加载各自业务脚本。"""
    for name, config in BUSINESS_PIPELINES.items():
        jenkinsfile = read_required_text(JENKINS_ROOT / config["jenkinsfile"])
        script = read_required_text(JENKINS_ROOT / "scripts" / config["script"])

        assert "node" in jenkinsfile
        assert "checkout scm" in jenkinsfile
        assert f"load 'jenkins/scripts/{config['script']}'" in jenkinsfile
        assert ".call()" in jenkinsfile
        assert "return this" in script


def test_business_jenkinsfiles_can_skip_initial_checkout_for_local_workspace():
    """本地挂载仓库时，业务 Jenkinsfile 加载脚本前不能无条件 checkout scm。"""
    for name, config in BUSINESS_PIPELINES.items():
        jenkinsfile = read_required_text(JENKINS_ROOT / config["jenkinsfile"])

        assert "LOCAL_WORKSPACE_REPO" in jenkinsfile
        assert "checkout scm" in jenkinsfile
        assert jenkinsfile.index("LOCAL_WORKSPACE_REPO") < jenkinsfile.index("checkout scm")


def test_daily_full_module_pipeline_is_scheduled_and_fixed_to_none_mode():
    """每日全量脚本必须配置凌晨 2 点 cron，并固定使用 RETRY_MODE=none。"""
    script = read_required_text(
        JENKINS_ROOT / "scripts" / BUSINESS_PIPELINES["daily-full-module"]["script"]
    )

    assert BUSINESS_PIPELINES["daily-full-module"]["cron"] in script
    assert "RETRY_MODE=none" in script
    assert "mode: 'none'" in script
    assert "includeModuleName: true" in script
    assert "includeNodeIds: false" in script
    assert "requireCasePath: true" in script
    assert BUSINESS_PIPELINES["daily-full-module"]["case_path_env"] in script
    assert BUSINESS_PIPELINES["daily-full-module"]["empty_case_path_message"] in script
    assert "PYTEST_NODE_IDS" not in script
    shared = read_pipeline_files()["api-test-pipeline.groovy"]
    assert "casePathDefaultEnv" in shared
    assert "error(emptyCasePathMessage)" in shared
    case_path_default_block = shared[
        shared.index("def casePathDefaultEnv") : shared.index("// Jenkins job 参数必须")
    ]
    assert "casePathDefaultEnv ? ''" in case_path_default_block
    assert "JENKINS_DEFAULT_CASE_PATH" in case_path_default_block
    assert "test_case/test_gbif_case" in case_path_default_block
    for parameter in BUSINESS_PIPELINES["daily-full-module"]["must_have"]:
        assert parameter in shared
    for forbidden in BUSINESS_PIPELINES["daily-full-module"]["must_not_have"]:
        assert forbidden not in script


def test_failed_rerun_pipeline_requires_node_ids_and_uses_selected_mode():
    """失败重试脚本必须固定 selected 模式，并拒绝空 PYTEST_NODE_IDS。"""
    script = read_required_text(
        JENKINS_ROOT / "scripts" / BUSINESS_PIPELINES["failed-rerun"]["script"]
    )

    assert "RETRY_MODE=selected" in script
    assert "mode: 'selected'" in script
    assert "requireNodeIds: true" in script
    assert "includeNodeIds: true" in script
    assert "PYTEST_NODE_IDS" in script
    assert BUSINESS_PIPELINES["failed-rerun"]["empty_node_ids_message"] in script
    shared = read_pipeline_files()["api-test-pipeline.groovy"]
    for parameter in BUSINESS_PIPELINES["failed-rerun"]["must_have"]:
        assert parameter in shared
    for forbidden in BUSINESS_PIPELINES["failed-rerun"]["must_not_have"]:
        assert forbidden not in script


def test_module_rerun_pipeline_is_fixed_to_module_mode():
    """模块重试脚本必须固定 module 模式，并按 CASE_PATH 执行当前模块。"""
    script = read_required_text(
        JENKINS_ROOT / "scripts" / BUSINESS_PIPELINES["module-rerun"]["script"]
    )

    assert "RETRY_MODE=module" in script
    assert "mode: 'module'" in script
    assert "CASE_PATH" in script
    assert "includeModuleName: true" in script
    assert "includeNodeIds: false" in script
    shared = read_pipeline_files()["api-test-pipeline.groovy"]
    for parameter in BUSINESS_PIPELINES["module-rerun"]["must_have"]:
        assert parameter in shared
    for forbidden in BUSINESS_PIPELINES["module-rerun"]["must_not_have"]:
        assert forbidden not in script


def test_business_pipelines_delegate_execution_to_shared_ci_runner_contract():
    """业务脚本只能固定业务模式，不得复制 pytest 或 runner 参数拼接逻辑。"""
    combined = combined_business_pipeline_source()

    assert combined.count("-m tools.ci_runner --from-jenkins-env") >= 1
    assert "jenkins/scripts/api-test-pipeline.groovy" in combined
    for forbidden in [
        "-m pytest",
        "--case-path",
        "--node-id",
        "--retry-mode",
        "--retry-count",
    ]:
        assert forbidden not in combined


def test_business_pipelines_reuse_cross_platform_artifact_and_allure_contract():
    """三条业务脚本必须复用 Windows/Linux、归档和 Allure 共享链路。"""
    combined = combined_business_pipeline_source()

    for required in [
        "isUnix()",
        "sh ",
        "bat ",
        "LOCAL_WORKSPACE_REPO",
        "JENKINS_API_TEST_DIR",
        "JENKINS_PYTHON_VENV_DIR",
        "archiveArtifacts",
        "allure",
        "Allure HTML report was not generated",
        "error(emptyNodeIdsMessage)",
    ]:
        assert required in combined
