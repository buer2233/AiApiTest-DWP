// 本地 Docker Compose Jenkins Job 修复脚本。
// 用途：让本地验收 Jenkins 直接使用挂载到容器内的仓库，避免构建前依赖 GitHub checkout。
// 运行方式：在 Jenkins Script Console 执行，或复制到 /var/jenkins_home/init.groovy.d/ 后重启 Jenkins。

import jenkins.model.Jenkins
import hudson.triggers.TimerTrigger
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty
import org.yaml.snakeyaml.Yaml

def jenkins = Jenkins.get()
def localWorkspaceMode = System.getenv('LOCAL_WORKSPACE_REPO') ?: 'false'
def mountedWorkspace = System.getenv('AIAPITEST_LOCAL_WORKSPACE') ?: '/workspace/AiApiTest-DWP'
def replaceExistingLocalJobs = System.getenv('AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS') ?: 'false'
def genericPipelineJobName = System.getenv('JENKINS_GENERIC_PIPELINE_JOB_NAME') ?: 'AiApiTest-DWP-Pipeline'
def failedRerunJobName = System.getenv('JENKINS_FAILED_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Failed-Rerun'
def moduleRerunJobName = System.getenv('JENKINS_MODULE_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Module-Rerun'
def dailyFullJobPrefix = System.getenv('JENKINS_DAILY_FULL_JOB_PREFIX') ?: 'AiApiTest-DWP-Daily-Full-Module'
def platformBootstrapJobName = System.getenv('JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME') ?: 'AiApiTest-DWP-Platform-Bootstrap'
def managedMarker = '[AiApiTest-DWP local-mounted]'
def legacyRemoteUrl = ['https://github', 'com/buer2233/AiApiTest-DWP.git'].join('.')

if (localWorkspaceMode != 'true') {
    println '[AiApiTest-DWP] LOCAL_WORKSPACE_REPO is not true; skip local mounted Job configuration.'
    return
}

if (!new File(mountedWorkspace).isDirectory()) {
    println "[AiApiTest-DWP] Mounted workspace not found: ${mountedWorkspace}; skip local mounted Job configuration."
    return
}

def shouldReplaceExistingJob = { job ->
    if (job == null) {
        return true
    }
    if (replaceExistingLocalJobs == 'true') {
        return true
    }

    def description = job.getDescription() ?: ''
    if (description.contains(managedMarker)) {
        return true
    }

    def definition = job.getDefinition()
    if (definition instanceof CpsFlowDefinition) {
        def script = definition.getScript() ?: ''
        // 兼容修复早期本地脚本：这些脚本先 git GitHub，再设置 LOCAL_WORKSPACE_REPO，正是本次卡死根因。
        return script.contains('LOCAL_WORKSPACE_REPO=true') && script.contains(legacyRemoteUrl)
    }
    return false
}

def packageModuleFile = new File(mountedWorkspace, 'api-test/utils/package_module.yaml')
def dailyModuleConfigs = []
def dailyConfigReady = false
if (!packageModuleFile.isFile()) {
    println "[AiApiTest-DWP] package_module.yaml not found: ${packageModuleFile}; preserve legacy Daily Job timer."
} else {
    try {
        def moduleDocument = new Yaml().load(packageModuleFile.getText('UTF-8'))
        if (!(moduleDocument instanceof Map) || moduleDocument.isEmpty()) {
            println '[AiApiTest-DWP] package_module.yaml has no module mapping; preserve legacy Daily Job timer.'
        } else {
            def validEntries = moduleDocument.every { packageName, metadata ->
                packageName instanceof String &&
                    packageName ==~ /[A-Za-z0-9_.-]+/ &&
                    metadata instanceof Map &&
                    ['module_name', 'module_dev', 'module_test'].every { key ->
                        metadata[key] instanceof String && metadata[key].trim()
                    }
            }
            if (!validEntries) {
                println '[AiApiTest-DWP] package_module.yaml contains incomplete module metadata; preserve legacy Daily Job timer.'
            } else {
                dailyModuleConfigs = moduleDocument.keySet().collect { packageName ->
                    // Daily Job 命名必须与后端 sync_jenkins_job_bindings 的 prefix-package 规则一致。
                    [
                        packageName: packageName,
                        casePath: "test_case/${packageName}",
                    ]
                }
                dailyConfigReady = !dailyModuleConfigs.isEmpty()
            }
        }
    } catch (Exception exc) {
        println "[AiApiTest-DWP] package_module.yaml is invalid (${exc.class.simpleName}); preserve legacy Daily Job timer."
    }
}

def jobConfigs = dailyModuleConfigs.collect { module ->
    [
        name: "${dailyFullJobPrefix}-${module.packageName}",
        description: "${managedMarker} Stage8 本地每日全量模块执行 Job（${module.packageName}）。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/daily-full-module-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true', "JENKINS_MODULE_CASE_PATH=${module.casePath}"],
        dailyCron: true,
        allowConcurrent: true,
        entrypoint: false
    ]
}

jobConfigs.addAll([
    [
        name: genericPipelineJobName,
        description: "${managedMarker} Stage10 本地通用执行 Job。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/api-test-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: true,
        entrypoint: false
    ],
    [
        name: failedRerunJobName,
        description: "${managedMarker} Stage8 本地失败用例重试 Job。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/failed-rerun-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: true,
        entrypoint: false
    ],
    [
        name: moduleRerunJobName,
        description: "${managedMarker} Stage8 本地模块重试 Job。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/module-rerun-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: true,
        entrypoint: false
    ],
    [
        // 环境 Job 与其他本地 Job 一样由 Jenkins 启动时创建/修复；顶层 Jenkinsfile 自行定义参数和禁止并发。
        name: platformBootstrapJobName,
        description: "${managedMarker} Stage13 统一平台环境启动 Job。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/Jenkinsfile.platform-bootstrap',
        envVars: ['LOCAL_WORKSPACE_REPO=true'],
        dailyCron: false,
        allowConcurrent: false,
        entrypoint: true,
        // 固定环境入口必须覆盖历史手工验收 Job，避免重启后残留临时配置。
        forceReplace: true
    ]
])

def configuredDailyJobNames = [] as LinkedHashSet
jobConfigs.each { config ->
    def job = jenkins.getItemByFullName(config.name, WorkflowJob)
    if (!(config.forceReplace || shouldReplaceExistingJob(job))) {
        println "[AiApiTest-DWP] skip existing non-local Jenkins Job: ${config.name}"
    } else {
        if (job == null) {
            job = jenkins.createProject(WorkflowJob, config.name)
        }

        def envList = config.envVars.collect { "'${it}'" }.join(', ')
        // 只在挂载目录读取 Pipeline 源码；durable-task、源码副本和证据必须使用 Jenkins 可写 workspace。
        def pipelineInvocation = """def pipelineScript
    dir('${mountedWorkspace}') {
        pipelineScript = load '${config.scriptPath}'
    }
    withEnv([${envList}]) {
        pipelineScript.call()
    }"""
def pipelineScript = """node {
    ${pipelineInvocation}
}
"""

        job.setDescription(config.description)
        job.setDefinition(new CpsFlowDefinition(pipelineScript, true))
        // 业务 Job 依靠模块锁控制互斥，环境 Job 的禁止并发由其 Jenkinsfile 在首次构建时建立并持久化。
        if (config.allowConcurrent) {
            job.removeProperty(DisableConcurrentBuildsJobProperty)
        }
        def configuredTriggers = job.getTriggers().values().findAll { !(it instanceof TimerTrigger) } as List
        if (config.dailyCron) {
            configuredTriggers.add(new TimerTrigger('0 2 * * *'))
        }
        job.setTriggers(configuredTriggers)
        job.save()
        if (config.dailyCron) {
            configuredDailyJobNames << config.name
        }
        println "[AiApiTest-DWP] Configured local mounted Jenkins Job: ${config.name}"
    }
}

// Stage8 前的共享 Daily Job 只保留历史构建，移除定时器避免与分模块 Job 重复执行。
def legacyDailyJob = jenkins.getItemByFullName(dailyFullJobPrefix, WorkflowJob)
def dailyCronMigrationReady = dailyConfigReady &&
    configuredDailyJobNames.size() == dailyModuleConfigs.size()
if (legacyDailyJob != null) {
    if (dailyCronMigrationReady) {
        def legacyTriggers = legacyDailyJob.getTriggers().values().findAll { !(it instanceof TimerTrigger) } as List
        legacyDailyJob.setTriggers(legacyTriggers)
        legacyDailyJob.save()
    } else {
        println '[AiApiTest-DWP] Preserved legacy Daily Job timer because module Daily Jobs are not fully configured.'
    }
}

jenkins.save()
