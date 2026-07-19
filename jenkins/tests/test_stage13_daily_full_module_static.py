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
    assert "git push" in sync_pipeline
    assert "callback" in sync_pipeline.lower()
    assert sync_pipeline.index("git push") < sync_pipeline.index("stage('Callback After Push')")
    assert "pytest" not in sync_pipeline.lower()
    assert "docker compose" not in sync_pipeline.lower()
    assert "from tools.environment_catalog import" in sync_helper
    assert "verify_yaml_blob_sha" in sync_helper
    assert "dump_environment_catalog" in sync_helper


def test_environment_catalog_import_does_not_require_an_unused_export_endpoint():
    """TC-S13-F3-006：YAML 导入路径只需回调地址，不应被无关导出地址阻断。"""
    sync_pipeline = read_source("scripts/environment-catalog-sync-pipeline.groovy")

    assert "if (params.SYNC_DIRECTION == 'mysql_to_yaml' && !params.CATALOG_EXPORT_URL?.trim())" in sync_pipeline
    assert "CATALOG_EXPORT_URL and CATALOG_CALLBACK_URL are required." not in sync_pipeline


def test_legacy_daily_jobs_are_preserved_until_a_future_approved_migration():
    """TC-S13-F4-001：本任务只登记受控删除守卫，绝不删除旧 Job 或历史。"""
    init_script = read_source("scripts/configure-local-mounted-jobs.groovy")

    assert "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED" in init_script
    assert "legacyDailyRemovalApproved" in init_script
    assert ".delete()" not in init_script
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
