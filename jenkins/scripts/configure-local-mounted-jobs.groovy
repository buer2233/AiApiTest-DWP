// 本地 Compose Jenkins Job 修复脚本。所有受管 Job 可重复创建/修复，绝不删除历史 Job 或构建。

import hudson.plugins.git.BranchSpec
import hudson.plugins.git.GitSCM
import hudson.plugins.git.UserRemoteConfig
import hudson.triggers.TimerTrigger
import hudson.plugins.throttleconcurrents.ThrottleJobProperty
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty


def jenkins = Jenkins.get()
def localWorkspaceMode = System.getenv('LOCAL_WORKSPACE_REPO') ?: 'false'
def mountedWorkspace = System.getenv('AIAPITEST_LOCAL_WORKSPACE') ?: '/workspace/AiApiTest-DWP'
def replaceExistingLocalJobs = System.getenv('AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS') ?: 'false'
def genericPipelineJobName = System.getenv('JENKINS_GENERIC_PIPELINE_JOB_NAME') ?: 'AiApiTest-DWP-Pipeline'
def failedRerunJobName = System.getenv('JENKINS_FAILED_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Failed-Rerun'
def moduleRerunJobName = System.getenv('JENKINS_MODULE_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Module-Rerun'
def dailyFullJobPrefix = System.getenv('JENKINS_DAILY_FULL_JOB_PREFIX') ?: 'AiApiTest-DWP-Daily-Full-Module'
def dailyFullParentJobName = System.getenv('JENKINS_DAILY_FULL_JOB_NAME') ?: dailyFullJobPrefix
def dailyFullWorkerJobName = System.getenv('JENKINS_DAILY_FULL_WORKER_JOB_NAME') ?: "${dailyFullParentJobName}-Worker"
def environmentCatalogSyncJobName = System.getenv('JENKINS_ENVIRONMENT_CATALOG_SYNC_JOB_NAME') ?: 'AiApiTest-DWP-Environment-Catalog-Sync'
def platformBootstrapJobName = System.getenv('JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME') ?: 'AiApiTest-DWP-Platform-Bootstrap'
def catalogScmUrl = System.getenv('JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL') ?: ''
def catalogScmBranch = System.getenv('JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH') ?: 'main'
def catalogScmCredentialsId = System.getenv('JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID') ?: ''
def legacyDailyRemovalApproved = System.getenv('JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED') ?: 'false'
def dailyWorkerThrottleCategory = 'aiapitest-daily-worker'
def moduleRerunThrottleCategory = 'aiapitest-module-rerun'
def failedRerunThrottleCategory = 'aiapitest-failed-rerun'
def managedMarker = '[AiApiTest-DWP local-mounted]'

if (localWorkspaceMode != 'true') {
    println '[AiApiTest-DWP] LOCAL_WORKSPACE_REPO is not true; skip local mounted Job configuration.'
    return
}

if (!new File(mountedWorkspace).isDirectory()) {
    println "[AiApiTest-DWP] Mounted workspace not found: ${mountedWorkspace}; skip local mounted Job configuration."
    return
}

def shouldReplaceExistingJob = { job ->
    if (job == null || replaceExistingLocalJobs == 'true') {
        return true
    }
    return (job.getDescription() ?: '').contains(managedMarker)
}

def throttleDescriptor = jenkins.getDescriptorByType(ThrottleJobProperty.DescriptorImpl)
def managedThrottleCategories = [
    new ThrottleJobProperty.ThrottleCategory(dailyWorkerThrottleCategory, 10, 10, []),
    new ThrottleJobProperty.ThrottleCategory(moduleRerunThrottleCategory, 10, 10, []),
    new ThrottleJobProperty.ThrottleCategory(failedRerunThrottleCategory, 10, 10, [])
]
def managedThrottleCategoryNames = managedThrottleCategories.collect { category -> category.categoryName } as Set
def preservedThrottleCategories = throttleDescriptor.getCategories().findAll { category ->
    !managedThrottleCategoryNames.contains(category.categoryName)
}
throttleDescriptor.setCategories(preservedThrottleCategories + managedThrottleCategories)
throttleDescriptor.save()

def localDefinition = { config ->
    def envList = config.envVars.collect { "'${it}'" }.join(', ')
    def invocation = """def pipelineScript
    dir('${mountedWorkspace}') {
        pipelineScript = load '${config.scriptPath}'
    }
    withEnv([${envList}]) {
        pipelineScript.call()
    }"""
    return new CpsFlowDefinition("""node {
    ${invocation}
}
""", true)
}

def catalogSyncDefinition = {
    if (!catalogScmUrl) {
        return new CpsFlowDefinition(
            "error('JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL is required for the isolated catalog sync Job.')",
            true
        )
    }
    def remoteConfig = new UserRemoteConfig(catalogScmUrl, null, null, catalogScmCredentialsId)
    def scm = new GitSCM(
        [remoteConfig],
        [new BranchSpec("*/${catalogScmBranch}")],
        false,
        [],
        null,
        null,
        []
    )
    return new CpsScmFlowDefinition(scm, 'jenkins/Jenkinsfile.environment-catalog-sync')
}

def jobConfigs = [
    [
        name: dailyFullParentJobName,
        description: "${managedMarker} Stage13 唯一 Daily 父 Job。负责全量模块编排、父级聚合与唯一 Allure。",
        scriptPath: 'jenkins/Jenkinsfile.daily-full-module',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: true,
        allowConcurrent: true,
        forceReplace: true,
        throttleCategory: null
    ],
    [
        name: dailyFullWorkerJobName,
        description: "${managedMarker} Stage13 Daily Worker。仅由唯一 Daily 父 Job 触发，无定时器。",
        scriptPath: 'jenkins/Jenkinsfile.daily-full-module-worker',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: true,
        forceReplace: true,
        throttleCategory: dailyWorkerThrottleCategory
    ],
    [
        name: genericPipelineJobName,
        description: "${managedMarker} 本地通用执行 Job。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/api-test-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: true,
        throttleCategory: null
    ],
    [
        name: failedRerunJobName,
        description: "${managedMarker} 失败用例重试 Job。",
        scriptPath: 'jenkins/scripts/failed-rerun-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: true,
        throttleCategory: failedRerunThrottleCategory
    ],
    [
        name: moduleRerunJobName,
        description: "${managedMarker} 模块重试 Job。",
        scriptPath: 'jenkins/scripts/module-rerun-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: true,
        throttleCategory: moduleRerunThrottleCategory
    ],
    [
        name: environmentCatalogSyncJobName,
        description: '[AiApiTest-DWP SCM] Stage13 环境目录同步 Job。仅使用隔离、干净的 SCM checkout。',
        dailyCron: false,
        allowConcurrent: false,
        forceReplace: true,
        throttleCategory: null,
        definitionFactory: catalogSyncDefinition
    ],
    [
        name: platformBootstrapJobName,
        description: "${managedMarker} Stage13 统一平台环境启动 Job。",
        scriptPath: 'jenkins/Jenkinsfile.platform-bootstrap',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: false,
        entrypoint: true,
        forceReplace: true,
        throttleCategory: null
    ]
]

jobConfigs.each { config ->
    def job = jenkins.getItemByFullName(config.name, WorkflowJob)
    if (!(config.forceReplace || shouldReplaceExistingJob(job))) {
        println "[AiApiTest-DWP] skip existing non-local Jenkins Job: ${config.name}"
        return
    }
    if (job == null) {
        job = jenkins.createProject(WorkflowJob, config.name)
    }

    job.setDescription(config.description)
    job.setDefinition(config.definitionFactory ? config.definitionFactory() : localDefinition(config))
    job.removeProperty(DisableConcurrentBuildsJobProperty)
    job.removeProperty(ThrottleJobProperty)
    if (config.throttleCategory) {
        job.addProperty(new ThrottleJobProperty(0, 0, [config.throttleCategory], true, 'category', false))
    } else if (!config.allowConcurrent) {
        job.addProperty(new DisableConcurrentBuildsJobProperty())
    }
    def configuredTriggers = job.getTriggers().values().findAll { !(it instanceof TimerTrigger) } as List
    if (config.dailyCron) {
        configuredTriggers.add(new TimerTrigger('0 2 * * *'))
    }
    job.setTriggers(configuredTriggers)
    job.save()
    println "[AiApiTest-DWP] Configured Jenkins Job: ${config.name}"
}

// Stage13 升级后旧分模块 Daily Job 仅保留配置和历史构建，移除 TimerTrigger 避免与唯一父 Job 重复调度。
def legacyDailyJobs = jenkins.getAllItems(WorkflowJob).findAll { legacyDailyJob ->
    legacyDailyJob.fullName.startsWith("${dailyFullJobPrefix}-") &&
        legacyDailyJob.fullName != dailyFullWorkerJobName
}
legacyDailyJobs.each { legacyDailyJob ->
    def legacyTriggers = legacyDailyJob.getTriggers().values().findAll { !(it instanceof TimerTrigger) } as List
    legacyDailyJob.setTriggers(legacyTriggers)
    legacyDailyJob.save()
    println "[AiApiTest-DWP] Removed legacy Daily timer while preserving Job and build history: ${legacyDailyJob.fullName}"
}

if (legacyDailyRemovalApproved == 'true') {
    println '[AiApiTest-DWP] Legacy Daily removal approval is recorded, but this Stage13 task never removes Jobs or build history.'
} else {
    println '[AiApiTest-DWP] Preserving legacy per-module Daily Jobs and their build history until final acceptance.'
}

jenkins.save()
