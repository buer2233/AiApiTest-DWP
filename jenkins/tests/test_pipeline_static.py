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


def test_jenkinsfile_can_skip_checkout_for_local_workspace():
    """通用 Jenkinsfile 在本地挂载仓库模式下也不能无条件 checkout scm。"""
    jenkinsfile = read_pipeline_files()["Jenkinsfile"]

    assert "LOCAL_WORKSPACE_REPO" in jenkinsfile
    assert "checkout scm" in jenkinsfile
    assert jenkinsfile.index("LOCAL_WORKSPACE_REPO") < jenkinsfile.index("checkout scm")


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


def test_pipeline_installs_only_missing_api_test_requirements():
    """Pipeline 应通过脚本只安装缺失依赖，避免每次全量 pip install。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    install_stage_start = pipeline.index("stage('Install API Test Requirements')")
    run_stage_start = pipeline.index("stage('Run API Tests')")
    install_stage = pipeline[install_stage_start:run_stage_start]

    unix_install_command = (
        "cd ${apiTestDir} && python -m venv ${pythonVenvDir} && "
        "${unixPython} -m tools.install_missing_requirements requirements.txt"
    )
    windows_install_command = (
        "cd ${apiTestDir} && python -m venv ${pythonVenvDir} && "
        "${windowsPython} -m tools.install_missing_requirements requirements.txt"
    )

    assert unix_install_command in install_stage
    assert windows_install_command in install_stage
    assert install_stage.count("-m tools.install_missing_requirements requirements.txt") == 2
    assert "-m pip install" not in install_stage
    assert "pip install -r" not in install_stage


def test_pipeline_fails_when_allure_html_report_is_not_generated():
    """Allure HTML 没有生成时 Pipeline 必须显式失败，不能只归档空结果。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "allure_report_status" in pipeline
    assert "Allure HTML report was not generated" in pipeline
    assert "SystemExit(1)" in pipeline or "sys.exit" in pipeline


def test_pipeline_archives_runtime_even_when_allure_validation_fails():
    """Allure 校验失败时也要归档 runtime，后端才能读取 summary 诊断。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    run_stage_start = pipeline.index("stage('Run API Tests')")
    generate_stage_start = pipeline.index("stage('Generate Allure Report')")
    archive_stage_start = pipeline.index("stage('Archive Runtime Artifacts')")
    publish_stage_start = pipeline.index("stage('Publish Allure')")
    try_start = pipeline.rindex("try {", 0, run_stage_start)
    guarded_block = pipeline[try_start:publish_stage_start]

    assert run_stage_start < generate_stage_start < archive_stage_start < publish_stage_start
    assert "try {" in guarded_block
    assert "} finally {" in guarded_block
    assert guarded_block.index("} finally {") < guarded_block.index("stage('Archive Runtime Artifacts')")
    assert "archiveArtifacts" in guarded_block


def test_pipeline_accepts_platform_run_id_for_artifact_lookup():
    """平台触发 Jenkins 时必须能指定 RUN_ID，后端才能按同一目录同步 artifact。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "name: 'RUN_ID'" in pipeline
    assert "params.RUN_ID" in pipeline
    assert "env.BUILD_TAG" in pipeline
    assert "RUN_ID=${runId}" in pipeline


def test_pipeline_forces_open_report_off_in_ci_environment():
    """Jenkins 非交互环境不能把 OPEN_REPORT=true 传给 ci_runner，避免 allure open 常驻卡死。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    env_start = pipeline.index("withEnv([")
    env_end = pipeline.index("]) {", env_start)
    env_block = pipeline[env_start:env_end]

    assert '"OPEN_REPORT=false"' in env_block
    assert '"OPEN_REPORT=${params.OPEN_REPORT}"' not in env_block


def test_pipeline_keeps_local_runtime_reports_for_30_days():
    """Jenkins 和 api-test 本地 runtime 报告默认保留 30 天。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    env_start = pipeline.index("withEnv([")
    env_end = pipeline.index("]) {", env_start)
    env_block = pipeline[env_start:env_end]

    assert "buildDiscarder(logRotator(" in pipeline
    assert "def ciRunRetentionDays = env.CI_RUN_RETENTION_DAYS ?: '30'" in pipeline
    assert "daysToKeepStr: ciRunRetentionDays" in pipeline
    assert "artifactDaysToKeepStr: ciRunRetentionDays" in pipeline
    assert '"CI_RUN_RETENTION_DAYS=${ciRunRetentionDays}"' in env_block


def test_run_api_tests_stage_has_timeout_guard():
    """Run API Tests 必须有 Jenkins 级超时，避免 pytest 或 Allure 子进程无限挂起。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    run_stage_start = pipeline.index("stage('Run API Tests')")
    generate_stage_start = pipeline.index("stage('Generate Allure Report')")
    run_stage = pipeline[run_stage_start:generate_stage_start]

    assert "timeout(" in run_stage
    assert "time: 60" in run_stage
    assert "unit: 'MINUTES'" in run_stage
    assert run_stage.index("timeout(") < run_stage.index("-m tools.ci_runner --from-jenkins-env")


def test_run_api_tests_stage_timeout_leaves_ci_runner_diagnostic_buffer():
    """Jenkins 外层超时必须大于 ci_runner 内部 pytest 与 Allure 超时总和。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    ci_runner = (REPO_ROOT / "api-test" / "tools" / "ci_runner.py").read_text(encoding="utf-8")

    assert "time: 60" in pipeline
    assert "DEFAULT_PYTEST_TIMEOUT_SECONDS = 45 * 60" in ci_runner
    assert "DEFAULT_ALLURE_TIMEOUT_SECONDS = 10 * 60" in ci_runner


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


def test_local_mounted_job_config_script_uses_workspace_without_git_checkout():
    """本地 Compose Jenkins Job 应直接使用挂载仓库，不得先访问 GitHub checkout。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "/workspace/AiApiTest-DWP" in script
    assert "AIAPITEST_LOCAL_WORKSPACE" in script
    assert "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS" in script
    assert "?: 'false'" in script
    assert "shouldReplaceExistingJob" in script
    assert "managedMarker" in script
    assert "skip existing non-local Jenkins Job" in script
    assert "LOCAL_WORKSPACE_REPO=true" in script
    assert "AiApiTest-DWP-Daily-Full-Module" in script
    assert "AiApiTest-DWP-Failed-Rerun" in script
    assert "AiApiTest-DWP-Module-Rerun" in script
    assert "test_case/test_gbif_case_module2" in script
    assert "CpsFlowDefinition" in script
    assert "dir('${mountedWorkspace}')" in script
    assert "ws('${mountedWorkspace}')" not in script
    assert script.index("dir('${mountedWorkspace}')") < script.index("load '${config.scriptPath}'")
    assert "git branch:" not in script
    assert "github.com" not in script


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
        "stage('Publish Allure')",
        "allure([",
        "Allure HTML report was not generated",
        "error(emptyNodeIdsMessage)",
    ]:
        assert required in combined


def test_failed_and_module_rerun_pipelines_reuse_shared_allure_publish_contract():
    """失败重试和模块重试必须逐条复用共享 Allure 插件发布链路。"""
    shared = read_pipeline_files()["api-test-pipeline.groovy"]

    for name in ["failed-rerun", "module-rerun"]:
        script = read_required_text(JENKINS_ROOT / "scripts" / BUSINESS_PIPELINES[name]["script"])

        assert "load 'jenkins/scripts/api-test-pipeline.groovy'" in script
        assert "sharedPipeline.call([" in script
        assert f"mode: '{BUSINESS_PIPELINES[name]['retry_mode']}'" in script

    for required in [
        "stage('Archive Runtime Artifacts')",
        "archiveArtifacts",
        "stage('Publish Allure')",
        "allure([",
        "commandline: 'Allure Commandline'",
        "resultPolicy: 'LEAVE_AS_IS'",
        "CI_RUN_RETENTION_DAYS",
        "buildDiscarder(logRotator(",
    ]:
        assert required in shared


def test_allure_commandline_toolchain_name_matches_publish_stage():
    """工具链镜像注册的 Allure 工具名必须和 Pipeline 发布阶段一致。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    dockerfile = read_required_text(REPO_ROOT / "docker" / "jenkins" / "Dockerfile")
    init_script = read_required_text(
        JENKINS_ROOT / "scripts" / "configure-allure-commandline.groovy"
    )

    assert "jenkins-plugin-cli --plugins allure-jenkins-plugin" in dockerfile
    assert "COPY jenkins/scripts/configure-allure-commandline.groovy" in dockerfile
    assert 'ENV ALLURE_COMMANDLINE_HOME="/opt/allure-${ALLURE_COMMANDLINE_VERSION}"' in dockerfile
    assert "def toolName = 'Allure Commandline'" in init_script
    assert "ALLURE_COMMANDLINE_HOME" in init_script
    assert "commandline: 'Allure Commandline'" in pipeline


def test_publish_allure_stage_falls_back_when_plugin_is_misconfigured():
    """Allure 插件存在但工具未配置时，不能让已生成的报告构建失败。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    publish_start = pipeline.index("stage('Publish Allure')")
    publish_stage = pipeline[publish_start:]

    assert "catch (Throwable ignored)" in publish_stage
    assert "Allure Jenkins plugin publish failed" in publish_stage


def test_publish_allure_stage_does_not_mark_test_failures_as_jenkins_unstable():
    """pytest 失败是业务测试结果，不应由 Allure 插件改写 Jenkins 构建状态。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    publish_start = pipeline.index("stage('Publish Allure')")
    publish_stage = pipeline[publish_start:]

    assert "commandline: 'Allure Commandline'" in publish_stage
    assert "resultPolicy: 'LEAVE_AS_IS'" in publish_stage
