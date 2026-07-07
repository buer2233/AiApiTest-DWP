// 本地 Docker Compose Jenkins Job 修复脚本。
// 用途：让本地验收 Jenkins 直接使用挂载到容器内的仓库，避免构建前依赖 GitHub checkout。
// 运行方式：在 Jenkins Script Console 执行，或复制到 /var/jenkins_home/init.groovy.d/ 后重启 Jenkins。

import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob

def jenkins = Jenkins.get()
def localWorkspaceMode = System.getenv('LOCAL_WORKSPACE_REPO') ?: 'false'
def mountedWorkspace = System.getenv('AIAPITEST_LOCAL_WORKSPACE') ?: '/workspace/AiApiTest-DWP'
def replaceExistingLocalJobs = System.getenv('AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS') ?: 'false'
def failedRerunJobName = System.getenv('JENKINS_FAILED_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Failed-Rerun'
def moduleRerunJobName = System.getenv('JENKINS_MODULE_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Module-Rerun'
def dailyFullJobPrefix = System.getenv('JENKINS_DAILY_FULL_JOB_PREFIX') ?: 'AiApiTest-DWP-Daily-Full-Module'
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
if (!packageModuleFile.isFile()) {
    println "[AiApiTest-DWP] package_module.yaml not found: ${packageModuleFile}; skip daily full module Jobs."
} else {
    def packageNames = [] as LinkedHashSet
    packageModuleFile.eachLine('UTF-8') { line ->
        def matcher = line =~ /^([A-Za-z0-9_.-]+):\s*$/
        if (matcher.matches()) {
            packageNames << matcher[0][1]
        }
    }
    dailyModuleConfigs = packageNames.collect { packageName ->
        // Daily Job 命名必须与后端 sync_jenkins_job_bindings 的 prefix-package 规则一致。
        [
            packageName: packageName,
            casePath: "test_case/${packageName}",
        ]
    }
}

def jobConfigs = dailyModuleConfigs.collect { module ->
    [
        name: "${dailyFullJobPrefix}-${module.packageName}",
        description: "${managedMarker} Stage8 本地每日全量模块执行 Job（${module.packageName}）。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/daily-full-module-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true', "JENKINS_MODULE_CASE_PATH=${module.casePath}"]
    ]
}

jobConfigs.addAll([
    [
        name: failedRerunJobName,
        description: "${managedMarker} Stage8 本地失败用例重试 Job。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/failed-rerun-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true']
    ],
    [
        name: moduleRerunJobName,
        description: "${managedMarker} Stage8 本地模块重试 Job。直接使用 Docker 挂载仓库，不访问远端源码仓库。",
        scriptPath: 'jenkins/scripts/module-rerun-pipeline.groovy',
        envVars: ['LOCAL_WORKSPACE_REPO=true']
    ]
])

jobConfigs.each { config ->
    def job = jenkins.getItemByFullName(config.name, WorkflowJob)
    if (!shouldReplaceExistingJob(job)) {
        println "[AiApiTest-DWP] skip existing non-local Jenkins Job: ${config.name}"
    } else {
        if (job == null) {
            job = jenkins.createProject(WorkflowJob, config.name)
        }

        def envList = config.envVars.collect { "'${it}'" }.join(', ')
def pipelineScript = """node {
    dir('${mountedWorkspace}') {
        withEnv([${envList}]) {
            def pipelineScript = load '${config.scriptPath}'
            pipelineScript.call()
        }
    }
}
"""

        job.setDescription(config.description)
        job.setDefinition(new CpsFlowDefinition(pipelineScript, true))
        job.save()
        println "[AiApiTest-DWP] Configured local mounted Jenkins Job: ${config.name}"
    }
}

jenkins.save()
