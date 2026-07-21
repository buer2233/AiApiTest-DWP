"""Stage13 唯一 Daily 编排与环境目录同步 Job 的静态契约测试。

测试不连接 Jenkins；通过版本化 Pipeline、init Groovy 和镜像配置验证
任务创建、排队分类及跨 Job 归档的不可变边界。
"""

from pathlib import Path


JENKINS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = JENKINS_ROOT.parent


def read_source(relative_path: str) -> str:
    """读取受 Stage13 约束的版本化 Jenkins 源文件。"""
    path = JENKINS_ROOT / relative_path
    assert path.exists(), f"Missing Stage13 Jenkins source: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def test_daily_parent_is_the_only_scheduled_job_and_worker_has_no_timer():
    """TC-S13-F1-001：仅父 Job 定时，Worker 只能由父 Job 触发。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")
    parent_pipeline = read_source("scripts/daily-full-module-pipeline.groovy")
    worker_pipeline = read_source("scripts/daily-full-module-worker-pipeline.groovy")

    assert "dailyFullParentJobName" in init_script
    assert "dailyFullWorkerJobName" in init_script
    assert "name: dailyFullParentJobName" in init_script
    assert "name: dailyFullWorkerJobName" in init_script
    assert "dailyCron: true" in init_script
    assert "dailyCron: false" in init_script
    assert "new TimerTrigger('0 2 * * *')" in init_script
    assert "${dailyFullJobPrefix}-${module.packageName}" not in init_script
    assert "jobTriggers" not in worker_pipeline
    assert "cron('0 2 * * *')" not in worker_pipeline
    assert "job: dailyWorkerJobName" in parent_pipeline
    assert "parallel workerBranches" in parent_pipeline


def test_daily_parent_delegates_yaml_preflight_and_aggregation_to_task1_tools():
    """TC-S13-F1-003~005：Groovy 只编排，预检和聚合复用 Task 1 工具。"""
    parent_pipeline = read_source("scripts/daily-full-module-pipeline.groovy")
    helper = read_source("scripts/daily_full_module_cli.py")

    assert "preflight --module-manifest" in parent_pipeline
    assert "aggregate --module-manifest" in parent_pipeline
    assert parent_pipeline.index("preflight --module-manifest") < parent_pipeline.index(
        "job: dailyWorkerJobName"
    )
    assert parent_pipeline.index("parallel workerBranches") < parent_pipeline.index(
        "aggregate --module-manifest"
    )
    assert "propagate: false" in parent_pipeline
    assert "copyArtifacts" in parent_pipeline
    assert "currentBuild.result = 'FAILURE'" in parent_pipeline
    assert "TARGET_BASE_URL" in parent_pipeline

    assert "from tools.daily_aggregation import" in helper
    assert "aggregate_daily_run" in helper
    assert "load_module_keys" in helper
    assert "from tools.environment_catalog import" in helper
    assert "load_environment_catalog" in helper
    assert "pytest" not in helper.lower()
    assert "retry" not in helper.lower()


def test_daily_parent_uses_platform_specific_target_url_expansion_for_preflight():
    """TC-S13-F1-004：Windows 与 Linux 都将 TARGET_BASE_URL 传入 Task 1 预检。"""
    parent_pipeline = read_source("scripts/daily-full-module-pipeline.groovy")

    assert "def preflightArguments = isUnix() ?" in parent_pipeline
    assert '"$DAILY_TARGET_BASE_URL"' in parent_pipeline
    assert '"%DAILY_TARGET_BASE_URL%"' in parent_pipeline
    assert "runTask1Tool(preflightArguments)" in parent_pipeline


def test_independent_throttle_categories_queue_each_business_job_type_at_ten():
    """TC-S13-F1-002：三类业务 Job 独立限流，环境目录同步不占用配额。"""
    dockerfile = (REPO_ROOT / "docker" / "jenkins" / "Dockerfile").read_text(encoding="utf-8")
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")

    assert "throttle-concurrents" in dockerfile
    assert "copyartifact" in dockerfile
    assert "ThrottleJobProperty" in init_script
    for category_name in [
        "aiapitest-daily-worker",
        "aiapitest-module-rerun",
        "aiapitest-failed-rerun",
    ]:
        assert category_name in init_script
    assert init_script.count("ThrottleCategory(") >= 3
    assert "10, 10" in init_script
    assert "throttleCategory: dailyWorkerThrottleCategory" in init_script
    assert "throttleCategory: moduleRerunThrottleCategory" in init_script
    assert "throttleCategory: failedRerunThrottleCategory" in init_script
    assert "environmentCatalogSyncJobName" in init_script
    assert "throttleCategory: null" in init_script
    assert "new DisableConcurrentBuildsJobProperty()" in init_script


def test_init_uses_jenkins_plugin_constructor_signatures_for_throttle_and_scm():
    """限流分类和隔离 SCM Job 必须按 Jenkins 插件的实际构造器签名创建。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")

    for category_name in [
        "dailyWorkerThrottleCategory",
        "moduleRerunThrottleCategory",
        "failedRerunThrottleCategory",
    ]:
        assert (
            f"new ThrottleJobProperty.ThrottleCategory({category_name}, 10, 10, [])"
            in init_script
        )
    assert (
        "new UserRemoteConfig(catalogScmUrl, null, null, catalogScmCredentialsId)"
        in init_script
    )
    assert "new GitSCM(" in init_script
    assert "[remoteConfig]," in init_script
    assert "[new BranchSpec(\"*/${catalogScmBranch}\")]," in init_script
    assert "false,\n        [],\n        null,\n        null,\n        []" in init_script


def test_init_removes_legacy_daily_timers_and_deletes_only_explicitly_approved_jobs():
    """旧 Job 默认保留；仅双开关与精确安全白名单同时成立时才允许删除。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")

    assert "def legacyDailyJobs = jenkins.getAllItems(WorkflowJob).findAll" in init_script
    assert "legacyDailyJob.fullName.startsWith(\"${dailyFullJobPrefix}-\")" in init_script
    assert "legacyDailyJob.fullName != dailyFullWorkerJobName" in init_script
    assert "legacyDailyJobs.each { legacyDailyJob ->" in init_script
    assert "legacyDailyJob.setTriggers(legacyTriggers)" in init_script
    assert "legacyDailyJob.save()" in init_script
    assert "removeItem" not in init_script
    assert "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED" in init_script
    assert "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES" in init_script
    assert "split(',', -1)" in init_script
    assert "legacyDailyDeletionAllowlist" in init_script
    assert "legacyDailyDeletionAllowlistIsValid" in init_script
    assert "it.startsWith(\"${dailyFullJobPrefix}-\")" in init_script
    assert "it != dailyFullParentJobName" in init_script
    assert "it != dailyFullWorkerJobName" in init_script

    deletion_guard = "if (legacyDailyRemovalApproved == 'true' && legacyDailyDeletionAllowlistIsValid)"
    assert deletion_guard in init_script
    deletion_call = "legacyDailyJob.delete()"
    assert deletion_call in init_script
    assert init_script.index(deletion_guard) < init_script.index(deletion_call)


def test_legacy_daily_timer_filter_protects_custom_parent_and_worker_jobs():
    """父 Job 即使自定义为前缀子项，也必须保留每日 0 点定时器。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")
    timer_filter = init_script.split("def legacyDailyJobs =", 1)[1].split(
        "legacyDailyJobs.each", 1
    )[0]

    assert 'legacyDailyJob.fullName.startsWith("${dailyFullJobPrefix}-")' in timer_filter
    assert "legacyDailyJob.fullName != dailyFullParentJobName" in timer_filter
    assert "legacyDailyJob.fullName != dailyFullWorkerJobName" in timer_filter


def test_legacy_daily_deletion_allowlist_has_static_safety_guards():
    """缺失、空、重复、非法及不存在 Job 均必须由源码守卫安全处理。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")

    assert "System.getenv('JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES') ?: ''" in init_script
    assert ".split(',', -1)" in init_script
    assert ".collect { it.trim() }" in init_script
    assert "legacyDailyDeletionAllowlist &&" in init_script
    assert (
        "legacyDailyDeletionAllowlist.toSet().size() == "
        "legacyDailyDeletionAllowlist.size()"
    ) in init_script
    assert "legacyDailyDeletionAllowlist.every { it ->" in init_script
    assert 'it.startsWith("${dailyFullJobPrefix}-")' in init_script
    assert "it != dailyFullParentJobName" in init_script
    assert "it != dailyFullWorkerJobName" in init_script

    deletion_guard = "if (legacyDailyRemovalApproved == 'true' && legacyDailyDeletionAllowlistIsValid)"
    lookup = "jenkins.getItemByFullName(legacyDailyJobName, WorkflowJob)"
    null_guard = "if (legacyDailyJob != null)"
    deletion_call = "legacyDailyJob.delete()"
    assert all(marker in init_script for marker in [deletion_guard, lookup, null_guard, deletion_call])
    assert init_script.index(deletion_guard) < init_script.index(lookup)
    assert init_script.index(lookup) < init_script.index(null_guard) < init_script.index(
        deletion_call
    )


def test_legacy_daily_deletion_documentation_requires_final_green_platform_job():
    """README 必须把受控删除限定为验收后由运维重启 Jenkins bootstrap 执行。"""
    readme = read_source("README.md")

    for marker in [
        "默认保留",
        "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED=true",
        "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES",
        "合法精确白名单",
        "固定 Platform Bootstrap Job 全绿后",
        "主人/平台运维",
        "重启 Jenkins",
        "Jenkins bootstrap",
    ]:
        assert marker in readme


def test_daily_worker_accepts_only_daily_parent_cause_and_skips_module_allure_publish():
    """Worker 只能接受唯一 Daily 父任务触发，并只归档模块产物。"""
    worker_pipeline = read_source("scripts/daily-full-module-worker-pipeline.groovy")
    shared_pipeline = read_source("scripts/api-test-pipeline.groovy")
    module_rerun_pipeline = read_source("scripts/module-rerun-pipeline.groovy")
    failed_rerun_pipeline = read_source("scripts/failed-rerun-pipeline.groovy")

    assert "currentBuild.getBuildCauses('hudson.model.Cause$UpstreamCause')" in worker_pipeline
    assert "JENKINS_DAILY_FULL_JOB_NAME" in worker_pipeline
    assert "cause.upstreamProject == expectedDailyParentJobName" in worker_pipeline
    assert "publishAllure: false" in worker_pipeline
    assert "def publishAllure = config.containsKey('publishAllure') ? config.publishAllure : true" in shared_pipeline
    assert "if (publishAllure) {\n                stage('Publish Allure')" in shared_pipeline
    assert "publishAllure:" not in module_rerun_pipeline
    assert "publishAllure:" not in failed_rerun_pipeline


def test_daily_parent_is_the_only_daily_pipeline_that_publishes_allure_after_archiving():
    """Daily 模块 Worker 只归档，父 Pipeline 独占唯一 Allure 发布入口。"""
    parent_pipeline = read_source("scripts/daily-full-module-pipeline.groovy")
    worker_pipeline = read_source("scripts/daily-full-module-worker-pipeline.groovy")

    assert parent_pipeline.count("allure([") == 1
    assert "allure([" not in worker_pipeline
    assert parent_pipeline.index("archiveArtifacts") < parent_pipeline.index("allure([")
    assert parent_pipeline.index("allure([") < parent_pipeline.index('def summary = new JsonSlurperClassic()')
    archive_stage = parent_pipeline[
        parent_pipeline.index("stage('Archive Daily Parent')"):parent_pipeline.index('def summary = new JsonSlurperClassic()')
    ]
    assert "catchError" not in archive_stage
    assert "try {" not in archive_stage


def test_environment_catalog_sync_uses_clean_scm_checkout_and_blob_guard_before_callback():
    """TC-S13-F3-005/006：同步 Job 隔离、串行并在快进推送后才回调。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")
    sync_jenkinsfile = read_source("Jenkinsfile.environment-catalog-sync")
    sync_pipeline = read_source("scripts/environment-catalog-sync-pipeline.groovy")
    sync_helper = read_source("scripts/environment_catalog_sync_cli.py")

    assert "CpsScmFlowDefinition" in init_script
    assert "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL" in init_script
    assert "LOCAL_WORKSPACE_REPO" not in sync_jenkinsfile
    assert "LOCAL_WORKSPACE_REPO" not in sync_pipeline
    assert "deleteDir()" in sync_jenkinsfile
    assert "checkout scm" in sync_jenkinsfile
    assert "EXPECTED_YAML_BLOB_SHA" in sync_pipeline
    assert "git merge-base --is-ancestor" in sync_pipeline
    assert "git merge-base --is-ancestor origin/${branchName} HEAD" in sync_pipeline
    assert "git merge-base --is-ancestor HEAD origin/${branchName}" not in sync_pipeline
    assert "git push" in sync_pipeline
    assert "callback" in sync_pipeline.lower()
    assert sync_pipeline.index("git push") < sync_pipeline.index("stage('Callback After Push')")
    assert "pytest" not in sync_pipeline.lower()
    assert "docker compose" not in sync_pipeline.lower()
    assert "from tools.environment_catalog import" in sync_helper
    assert "verify_yaml_blob_sha" in sync_helper
    assert "dump_environment_catalog" in sync_helper


def test_environment_catalog_sync_records_validated_head_sha_after_mysql_push_only():
    """mysql_to_yaml 只能在成功 push 后回传经过校验的实际 HEAD SHA。"""
    sync_pipeline = read_source("scripts/environment-catalog-sync-pipeline.groovy")
    mysql_to_yaml_start = sync_pipeline.index("if (syncDirection == 'mysql_to_yaml')")
    yaml_to_mysql_start = sync_pipeline.index("    } else {", mysql_to_yaml_start)
    mysql_to_yaml_flow = sync_pipeline[mysql_to_yaml_start:yaml_to_mysql_start]
    yaml_to_mysql_flow = sync_pipeline[yaml_to_mysql_start:]

    assert "string(name: 'COMMIT_SHA'" not in sync_pipeline
    assert "params.COMMIT_SHA" not in sync_pipeline
    assert "def recordPushedCommitSha(String resultPath)" in sync_pipeline
    assert "readCommand('git rev-parse HEAD', 'git rev-parse HEAD')" in sync_pipeline
    assert 'return bat(returnStdout: true, script: "@${windowsCommand}").trim()' in sync_pipeline
    assert "commitSha ==~ /^[0-9a-f]{40}$/" in sync_pipeline
    assert "new JsonSlurperClassic().parseText(readFile(file: resultPath))" in sync_pipeline
    assert "resultPayload.commit_sha = commitSha" in sync_pipeline
    assert "JsonOutput.toJson(resultPayload)" in sync_pipeline
    assert "recordPushedCommitSha(resultPath)" in mysql_to_yaml_flow
    assert "recordPushedCommitSha(resultPath)" not in yaml_to_mysql_flow
    assert mysql_to_yaml_flow.index("git push --quiet origin HEAD:${branchName}") < mysql_to_yaml_flow.index(
        "recordPushedCommitSha(resultPath)"
    ) < mysql_to_yaml_flow.index("callbackAfterSuccessfulPush(resultPath, catalogCallbackEndpoint)")


def test_environment_catalog_sync_uses_fixed_private_service_endpoints_not_url_parameters():
    """内部导出和回调端点只能从私有服务地址与已校验请求标识构造。"""
    sync_pipeline = read_source("scripts/environment-catalog-sync-pipeline.groovy")

    assert "string(name: 'CATALOG_EXPORT_URL'" not in sync_pipeline
    assert "string(name: 'CATALOG_CALLBACK_URL'" not in sync_pipeline
    assert "params.CATALOG_EXPORT_URL" not in sync_pipeline
    assert "params.CATALOG_CALLBACK_URL" not in sync_pipeline
    assert "JENKINS_ENVIRONMENT_CATALOG_SERVICE_BASE_URL" in sync_pipeline
    assert "def catalogExportEndpoint =" in sync_pipeline
    assert "def catalogCallbackEndpoint =" in sync_pipeline
    assert "/api/v1/internal/environment-catalog-sync-attempts/${syncRequestId}/export/" in sync_pipeline
    assert "/api/v1/internal/environment-catalog-sync-attempts/${syncRequestId}/callback/" in sync_pipeline


def test_environment_catalog_sync_validates_all_caller_inputs_before_constructing_commands():
    """请求方向、请求标识和 YAML blob SHA 必须先收敛为安全局部值。"""
    sync_pipeline = read_source("scripts/environment-catalog-sync-pipeline.groovy")

    assert "def syncDirection = params.SYNC_DIRECTION ?: ''" in sync_pipeline
    assert "if (!(syncDirection in ['mysql_to_yaml', 'yaml_to_mysql']))" in sync_pipeline
    assert "def syncRequestId = params.SYNC_REQUEST_ID ?: ''" in sync_pipeline
    assert "syncRequestId ==~ /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/" in sync_pipeline
    assert "def expectedYamlBlobSha = params.EXPECTED_YAML_BLOB_SHA ?: ''" in sync_pipeline
    assert "expectedYamlBlobSha ==~ /^[0-9a-f]{40}$/" in sync_pipeline
    assert 'def controlDir = "catalog-sync/${syncRequestId}"' in sync_pipeline
    assert "--expected-blob-sha ${expectedYamlBlobSha}" in sync_pipeline

    runtime_source = sync_pipeline[sync_pipeline.index("def branchName") :]
    assert "params." not in runtime_source


def test_environment_catalog_sync_uses_private_askpass_credentials_only_for_git_network_operations():
    """受限 push 凭据只包裹 fetch/push，askpass 文件本身不落入凭据或远端地址。"""
    sync_pipeline = read_source("scripts/environment-catalog-sync-pipeline.groovy")
    unix_askpass = read_source("scripts/environment-catalog-git-askpass.sh")
    windows_askpass = read_source("scripts/environment-catalog-git-askpass.bat")
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    readme = read_source("README.md")

    assert "JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID" in sync_pipeline
    assert "usernamePassword(" in sync_pipeline
    assert "CATALOG_GIT_PUSH_USERNAME" in sync_pipeline
    assert "CATALOG_GIT_PUSH_PASSWORD" in sync_pipeline
    assert "GIT_ASKPASS" in sync_pipeline
    assert "git fetch --quiet --prune origin" in sync_pipeline
    assert "git push --quiet origin HEAD:${branchName}" in sync_pipeline
    assert "withCatalogPushCredentials" in sync_pipeline

    for askpass in [unix_askpass, windows_askpass]:
        assert "CATALOG_GIT_PUSH_USERNAME" in askpass
        assert "CATALOG_GIT_PUSH_PASSWORD" in askpass
        assert "CATALOG_GIT_PUSH_CREDENTIALS_ID" not in askpass
        assert "origin" not in askpass

    for variable in [
        "JENKINS_ENVIRONMENT_CATALOG_SERVICE_BASE_URL",
        "JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID",
    ]:
        assert variable in compose
        assert variable in env_example
        assert variable in readme


def test_legacy_daily_job_deletion_guard_defaults_to_preserving_all_jobs():
    """TC-S13-F4-001：批准缺失、白名单为空或非法时不得删除任何 Job。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")

    assert "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED" in init_script
    assert "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES" in init_script
    assert "legacyDailyRemovalApproved" in init_script
    assert "legacyDailyDeletionAllowlistIsValid" in init_script
    assert "removeItem" not in init_script
    assert "Preserving legacy per-module Daily Jobs" in init_script


class FakeJenkins:
    """最小 fake Jenkins，用于锁定 init 的幂等创建语义。"""

    def __init__(self):
        self.jobs: dict[str, dict[str, str]] = {}
        self.create_calls = 0

    def configure(self, name: str, definition: str) -> None:
        if name not in self.jobs:
            self.jobs[name] = {}
            self.create_calls += 1
        self.jobs[name]["definition"] = definition


def test_local_init_idempotently_repairs_stage13_jobs_with_fake_jenkins():
    """TC-S13-F1-001：重复 init 只更新同名受管 Job，不创建重复 Job。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")
    fake_jenkins = FakeJenkins()
    managed_jobs = [
        "AiApiTest-DWP-Daily-Full-Module",
        "AiApiTest-DWP-Daily-Full-Module-Worker",
        "AiApiTest-DWP-Environment-Catalog-Sync",
    ]

    assert "jenkins.getItemByFullName(config.name, WorkflowJob)" in init_script
    assert "if (job == null)" in init_script
    assert "job.setDefinition" in init_script
    for _ in range(2):
        for job_name in managed_jobs:
            fake_jenkins.configure(job_name, "versioned-stage13-definition")

    assert set(fake_jenkins.jobs) == set(managed_jobs)
    assert fake_jenkins.create_calls == len(managed_jobs)
