"""Jenkins Pipeline 静态结构测试。

本文件不启动真实 Jenkins，而是直接读取 Jenkinsfile 和 Groovy 脚本，
验证参数、stage、跨平台分支和 ci_runner 调用契约没有被破坏。
"""

from pathlib import Path


JENKINS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = JENKINS_ROOT.parent

BUSINESS_PIPELINES = {
    "daily-full-module-worker": {
        "jenkinsfile": "Jenkinsfile.daily-full-module-worker",
        "script": "daily-full-module-worker-pipeline.groovy",
        "retry_mode": "none",
        "must_have": ["CASE_PATH", "MODULE_NAME", "TARGET_BASE_URL", "RETRY_COUNT", "CLEAN_ALLURE", "OPEN_REPORT"],
        "must_not_have": ["choice(\n                name: 'RETRY_MODE'", "all-failed"],
        "empty_case_path_message": "CASE_PATH is required for Daily Worker",
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
    """合并四类业务 Pipeline 源码，便于检查共享契约。"""
    shared = read_pipeline_files()["api-test-pipeline.groovy"]
    return "\n".join(
        [
            read_pipeline_files()["Jenkinsfile"],
            shared,
            *read_business_pipeline_files().values(),
        ]
    )


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

    assert "JENKINS_DEFAULT_CASE_PATH" not in combined
    assert "def casePathDefault = config.get('casePathDefault', 'test_case/test_gbif_case')" in combined
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
        "Run API Tests",
        "Archive Runtime Artifacts",
        "Publish Allure",
    ]:
        assert f"stage('{stage_name}')" in combined or f'stage("{stage_name}")' in combined

    assert "stage('Prepare Python')" not in combined
    assert "stage('Install API Test Requirements')" not in combined
    assert "stage('Generate Allure Report')" not in combined

    assert "isUnix()" in combined
    assert "sh " in combined
    assert "bat " in combined


def test_pipeline_delegates_pytest_execution_to_ci_runner():
    """Jenkins 只负责编排，pytest 执行和重试规则必须委托给 ci_runner。"""
    files = read_pipeline_files()
    combined = "\n".join(files.values())

    assert "python3 jenkins/scripts/api_runner_cli.py execute" in combined
    assert "python jenkins\\scripts\\api_runner_cli.py execute" in combined
    assert "-m tools.ci_runner" not in combined
    assert "--case-path" not in combined
    assert "--node-id" not in combined
    assert "--retry-mode" not in combined
    assert "PYTEST_NODE_IDS" in combined
    assert "archiveArtifacts" in combined
    assert "allure" in combined


def test_pipeline_binds_e9_accounts_secret_for_api_runner():
    """业务 Pipeline 必须从 Jenkins Secret Text 凭据向隔离 runner 注入账号 JSON。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "JENKINS_API_TEST_E9_CREDENTIALS_ID" in pipeline
    assert "withCredentials" in pipeline
    assert "credentialsId: e9CredentialsId" in pipeline
    assert "variable: 'E9_ACCOUNTS_JSON'" in pipeline


def test_pipeline_preserves_artifacts_when_pytest_fails():
    """pytest 用例失败时 Run API Tests 不应把 Jenkins stage 标记为失败。"""
    files = read_pipeline_files()
    combined = "\n".join(files.values())

    run_stage_start = combined.index("stage('Run API Tests')")
    archive_stage_start = combined.index("stage('Archive Runtime Artifacts')")
    run_stage = combined[run_stage_start:archive_stage_start]

    assert "catchError" not in run_stage
    assert "stageResult: 'FAILURE'" not in run_stage
    assert "api_runner_cli.py execute" in run_stage


def test_jenkinsfile_loads_pipeline_script_inside_node_context():
    """Jenkinsfile 必须在 node workspace 上下文中 load Groovy 脚本。"""
    jenkinsfile = read_pipeline_files()["Jenkinsfile"]

    assert jenkinsfile.index("node") < jenkinsfile.index("load 'jenkins/scripts/api-test-pipeline.groovy'")


def test_jenkinsfile_uses_the_fixed_local_workspace_contract():
    """通用 Jenkinsfile 固定从 Compose 挂载仓库加载，不保留 checkout 模式开关。"""
    jenkinsfile = read_pipeline_files()["Jenkinsfile"]

    assert "Using fixed local mounted repository" in jenkinsfile
    assert "LOCAL_WORKSPACE_REPO" not in jenkinsfile
    assert "checkout scm" not in jenkinsfile


def test_pipeline_checkout_stage_is_fixed_to_local_mounted_repository():
    """业务 Pipeline 的 Checkout stage 只声明固定挂载仓库，不访问 SCM。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "Using fixed local mounted repository" in pipeline
    assert "LOCAL_WORKSPACE_REPO" not in pipeline
    assert "checkout scm" not in pipeline


def test_pipeline_uses_sandbox_safe_environment_default_access():
    """参数默认值使用代码常量，不进行 sandbox 动态环境访问。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    parameter_block = pipeline[
        pipeline.index("def buildParameterDefinitions") : pipeline.index("// Jenkins job 参数必须")
    ]

    assert "env[" not in parameter_block
    assert "env.JENKINS_MODULE_CASE_PATH" not in parameter_block
    assert "env.JENKINS_DEFAULT_CASE_PATH" not in parameter_block
    assert "test_case/test_gbif_case" in parameter_block


def test_pipeline_uses_only_shared_api_runner_cli_without_controller_dependencies():
    """业务 Pipeline 只能委托共享 runner CLI，不得在 controller 准备业务 Python。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "python3 jenkins/scripts/api_runner_cli.py execute" in pipeline
    assert "python jenkins\\scripts\\api_runner_cli.py execute" in pipeline
    for forbidden in [
        "JENKINS_PYTHON_VENV_DIR",
        "AIAPITEST_PREINSTALLED_REQUIREMENTS",
        "python -m venv",
        "pip install",
        "install_missing_requirements",
        "-m tools.ci_runner",
    ]:
        assert forbidden not in pipeline


def test_pipeline_fails_when_allure_html_report_is_not_generated():
    """Allure HTML 状态必须由 runner helper 的完整 summary 校验决定。"""
    helper = read_required_text(JENKINS_ROOT / "scripts" / "api_runner_lifecycle.py")

    assert "allure_report_status" in helper
    assert "generated" in helper
    assert "summary.json" in helper


def test_pipeline_archives_runtime_even_when_allure_validation_fails():
    """runner 失败时仍必须在 finally 中归档 runtime 与生命周期证据。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]
    run_stage_start = pipeline.index("stage('Run API Tests')")
    archive_stage_start = pipeline.index("stage('Archive Runtime Artifacts')")
    publish_stage_start = pipeline.index("stage('Publish Allure')")
    guarded_block = pipeline[run_stage_start:]

    assert run_stage_start < archive_stage_start < publish_stage_start
    assert "def primaryFailure = null" in pipeline
    assert "finally" in guarded_block
    assert "archiveArtifacts" in guarded_block
    assert "runner-lifecycle" in guarded_block
    assert "throw primaryFailure" in guarded_block


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
    archive_stage_start = pipeline.index("stage('Archive Runtime Artifacts')")
    run_stage = pipeline[run_stage_start:archive_stage_start]

    assert "timeout(" in run_stage
    assert "time: 60" in run_stage
    assert "unit: 'MINUTES'" in run_stage
    assert run_stage.index("timeout(") < run_stage.index("api_runner_cli.py execute")


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
        assert "Using fixed local mounted repository" in jenkinsfile
        assert "checkout scm" not in jenkinsfile
        assert f"load 'jenkins/scripts/{config['script']}'" in jenkinsfile
        assert ".call()" in jenkinsfile
        assert "return this" in script


def test_business_jenkinsfiles_have_no_retired_workspace_mode_switch():
    """业务 Jenkinsfile 固定使用挂载仓库，不再接受 workspace 模式覆盖。"""
    for name, config in BUSINESS_PIPELINES.items():
        jenkinsfile = read_required_text(JENKINS_ROOT / config["jenkinsfile"])

        assert "LOCAL_WORKSPACE_REPO" not in jenkinsfile
        assert "checkout scm" not in jenkinsfile
        assert "Using fixed local mounted repository" in jenkinsfile


def test_local_mounted_job_config_script_uses_workspace_without_git_checkout():
    """本地 Compose Jenkins Job 应直接使用挂载仓库，不得先访问 GitHub checkout。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "/workspace/AiApiTest-DWP" in script
    assert "AIAPITEST_LOCAL_WORKSPACE" not in script
    assert "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS" not in script
    assert "shouldReplaceExistingJob" not in script
    assert "managedMarker" in script
    assert "AiApiTest-DWP-Daily-Full-Module" in script
    assert "AiApiTest-DWP-Failed-Rerun" in script
    assert "AiApiTest-DWP-Module-Rerun" in script
    assert "dailyFullParentJobName" in script
    assert "dailyFullWorkerJobName" in script
    assert "environmentCatalogSyncJobName" in script
    assert "CpsFlowDefinition" in script
    assert "dir('${mountedWorkspace}')" in script
    assert "ws('${mountedWorkspace}')" not in script
    assert "def invocation = \"\"\"dir('${mountedWorkspace}')" in script
    assert "pipelineScript = load '${config.scriptPath}'" in script
    assert "pipelineScript.call()" in script
    assert "git branch:" not in script
    assert "github.com" not in script


def test_local_mounted_job_config_creates_one_daily_parent_and_one_worker():
    """Stage13 只创建一个定时 Daily 父 Job 和一个无定时 Worker。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "def dailyFullParentJobName = 'AiApiTest-DWP-Daily-Full-Module'" in script
    assert "def dailyFullWorkerJobName = 'AiApiTest-DWP-Daily-Full-Module-Worker'" in script
    assert "JENKINS_DAILY_FULL_JOB_NAME" not in script
    assert "JENKINS_DAILY_FULL_WORKER_JOB_NAME" not in script
    assert "name: dailyFullParentJobName" in script
    assert "name: dailyFullWorkerJobName" in script
    assert "dailyCron: true" in script
    assert "dailyCron: false" in script
    assert "dailyModuleConfigs" not in script
    assert "test_case/test_gbif_case_module2" not in script


def test_local_mounted_job_config_sets_daily_parent_cron_without_legacy_deletion():
    """仅 Daily 父 Job 定时；旧 Job 只移除重复定时器，不允许删除。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "TimerTrigger" in script
    assert "0 2 * * *" in script
    assert "setTriggers" in script
    assert "instanceof TimerTrigger" in script
    assert "removeTrigger" not in script
    assert "preserving Job and build history" in script
    assert "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED" not in script
    assert "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES" not in script
    assert "legacyDailyJob.delete()" not in script


def test_local_mounted_job_config_does_not_reparse_module_yaml_or_deletion_allowlist():
    """模块发现移交 Task 1；init 不解析模块 YAML 或已退役删除白名单。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "package_module.yaml" not in script
    assert "org.yaml.snakeyaml.Yaml" not in script
    assert "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED" not in script
    assert "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES" not in script
    assert "legacyDailyDeletionAllowlist" not in script


def test_local_mounted_job_config_auto_creates_platform_bootstrap_from_jenkinsfile():
    """环境 Job 与既有本地 Job 一样由 Jenkins init 幂等创建，不依赖手工配置。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "def platformBootstrapJobName = 'AiApiTest-DWP-Platform-Bootstrap'" in script
    assert "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME" not in script
    assert "name: platformBootstrapJobName" in script
    assert "scriptPath: 'jenkins/Jenkinsfile.platform-bootstrap'" in script
    assert "entrypoint: true" in script
    assert "dailyCron: false" in script
    assert "load '${config.scriptPath}'" in script


def test_local_init_idempotently_repairs_all_declared_managed_jobs():
    """所有受管 Job 都按固定配置幂等修复，不保留可配置替换开关。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "forceReplace: true" in script
    assert "job.setDefinition" in script
    assert "shouldReplaceExistingJob" not in script
    assert "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS" not in script


def test_local_init_configures_category_throttles_and_global_sync_serialization():
    """三类业务 Job 使用独立分类限流，目录同步 Job 使用全局串行属性。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "allowConcurrent: false" in script
    assert "ThrottleJobProperty" in script
    assert "ThrottleCategory(dailyWorkerThrottleCategory, 10, 10, [])" in script
    assert "ThrottleCategory(moduleRerunThrottleCategory, 10, 10, [])" in script
    assert "ThrottleCategory(failedRerunThrottleCategory, 10, 10, [])" in script
    assert "if (config.throttleCategory)" in script
    assert "new DisableConcurrentBuildsJobProperty()" in script


def test_local_mounted_job_loads_from_mount_but_calls_pipeline_in_writable_workspace():
    """挂载仓库只读时，durable-task 和运行证据必须回到 Jenkins 自己的 workspace。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")
    bootstrap = read_required_text(JENKINS_ROOT / "Jenkinsfile.platform-bootstrap")

    assert "def pipelineScript" in script
    assert "pipelineScript = load '${config.scriptPath}'" in script
    assert script.index("pipelineScript = load '${config.scriptPath}'") < script.index(
        "pipelineScript.call()"
    )
    assert "dir('${mountedWorkspace}') {\n        withEnv" not in script
    assert "def call()" in bootstrap
    assert bootstrap.index("def call()") < bootstrap.index("node {")


def test_jenkins_readme_states_daily_cron_is_effective_after_initialization():
    """初始化脚本已直接配置 cron，文档不得继续要求首次手工 Build 才生效。"""
    readme = read_required_text(JENKINS_ROOT / "README.md")

    assert "初始化完成后即生效" in readme
    assert "首次创建 Job 后建议先手工 Build 一次" not in readme
    assert "先手工 Build 一次，确认参数和 `0 2 * * *` 定时触发生效" not in readme


def test_business_local_jobs_allow_concurrent_builds():
    """业务本地 Pipeline Job 必须移除禁止并发属性；环境 Job 例外由 Jenkinsfile 管理。"""
    script = read_required_text(JENKINS_ROOT / "scripts" / "configure-local-mounted-jobs.groovy")

    assert "def genericPipelineJobName = 'AiApiTest-DWP-Pipeline'" in script
    assert "JENKINS_GENERIC_PIPELINE_JOB_NAME" not in script
    assert "DisableConcurrentBuildsJobProperty" in script
    assert "removeProperty" in script


def test_pipeline_has_no_executor_scoped_virtualenv_after_runner_migration():
    """并发隔离由唯一 runner 容器承担，controller 不再创建 executor venv。"""
    pipeline = read_pipeline_files()["api-test-pipeline.groovy"]

    assert "env.EXECUTOR_NUMBER" not in pipeline
    assert "executor-${executorNumber}" not in pipeline
    assert "JENKINS_PYTHON_VENV_DIR" not in pipeline


def test_jenkins_readme_describes_image_runner_instead_of_legacy_venv():
    """Jenkins 文档必须与 api-runner 迁移后的实际执行和产物语义一致。"""
    readme = read_required_text(JENKINS_ROOT / "README.md")

    for forbidden in [
        "Prepare Python",
        "Install API Test Requirements",
        "Generate Allure Report",
        "executor venv",
        "JENKINS_PYTHON_VENV_DIR",
        "AIAPITEST_PREINSTALLED_REQUIREMENTS",
        "install_missing_requirements",
    ]:
        assert forbidden not in readme
    for required in [
        "aiapitest-api-runner:local",
        "api_runner_cli.py execute",
        "镜像内源码",
        "runner-lifecycle",
        "导出失败",
    ]:
        assert required in readme


def test_daily_full_module_parent_and_worker_keep_their_separate_contracts():
    """父任务只调度聚合，Worker 才固定执行单模块 none 模式。"""
    parent = read_required_text(JENKINS_ROOT / "scripts" / "daily-full-module-pipeline.groovy")
    worker = read_required_text(
        JENKINS_ROOT / "scripts" / BUSINESS_PIPELINES["daily-full-module-worker"]["script"]
    )

    assert "cron('0 2 * * *')" in parent
    assert "parallel workerBranches" in parent
    assert "daily_full_module_cli.py" in parent
    assert "mode: 'none'" in worker
    assert "includeModuleName: true" in worker
    assert "includeNodeIds: false" in worker
    assert "includeTargetBaseUrl: true" in worker
    assert "requireCasePath: true" in worker
    assert BUSINESS_PIPELINES["daily-full-module-worker"]["empty_case_path_message"] in worker
    assert "PYTEST_NODE_IDS" not in worker
    assert "cron('0 2 * * *')" not in worker
    shared = read_pipeline_files()["api-test-pipeline.groovy"]
    assert "error(emptyCasePathMessage)" in shared
    case_path_default_block = shared[
        shared.index("def casePathDefault") : shared.index("// Jenkins job 参数必须")
    ]
    assert "config.get('casePathDefault', 'test_case/test_gbif_case')" in case_path_default_block
    assert "JENKINS_DEFAULT_CASE_PATH" not in case_path_default_block
    assert "test_case/test_gbif_case" in case_path_default_block
    for parameter in BUSINESS_PIPELINES["daily-full-module-worker"]["must_have"]:
        assert parameter in shared
    for forbidden in BUSINESS_PIPELINES["daily-full-module-worker"]["must_not_have"]:
        assert forbidden not in worker


def test_daily_parent_registers_its_timer_only_for_the_configured_parent_job_name():
    """保留旧 Job 手工构建时，加载共享脚本也不能重新注册 Daily 定时器。"""
    parent = read_required_text(JENKINS_ROOT / "scripts" / "daily-full-module-pipeline.groovy")

    assert "def configuredDailyParentJobName = 'AiApiTest-DWP-Daily-Full-Module'" in parent
    assert "JENKINS_DAILY_FULL_JOB_NAME" not in parent
    assert "if (env.JOB_NAME == configuredDailyParentJobName)" in parent
    assert "pipelineTriggers([cron('0 2 * * *')])" in parent


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

    assert combined.count("api_runner_cli.py execute") == 2
    assert "jenkins/scripts/api-test-pipeline.groovy" in combined
    for forbidden in [
        "-m pytest",
        "-m tools.ci_runner",
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
        "Using fixed local mounted repository",
        "api_runner_cli.py execute",
        "runner-lifecycle",
        "archiveArtifacts",
        "stage('Publish Allure')",
        "allure([",
        "primaryFailure",
        "error(emptyNodeIdsMessage)",
    ]:
        assert required in combined


def test_all_four_business_pipelines_forbid_controller_installs_and_workspace_mounts():
    """四类 Job 合并源码不得保留旧依赖安装、controller pytest 或 runner bind mount。"""
    combined = combined_business_pipeline_source()

    for forbidden in [
        "python -m venv",
        "pip install",
        "install_missing_requirements",
        "JENKINS_PYTHON_VENV_DIR",
        "-m tools.ci_runner",
        "--volume",
        "--mount",
        "docker.sock",
    ]:
        assert forbidden not in combined


def test_runner_helper_reuses_task3_api_runner_fingerprint_contract():
    """Task 4 只能选择 Task 3 api-runner 域，禁止复制 hash 或 ignore 算法。"""
    helper = read_required_text(JENKINS_ROOT / "scripts" / "api_runner_lifecycle.py")

    assert "default_domain_specs" in helper
    assert "compute_domain_hashes" in helper
    assert "DependencyDomainSpec" in helper
    assert "name == \"api-runner\"" in helper or "name == 'api-runner'" in helper
    assert "def _iter_files" not in helper
    assert "IGNORED_PARTS" not in helper
    assert "IGNORED_NAMES" not in helper


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
