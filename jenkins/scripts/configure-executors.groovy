// 配置 Jenkins controller 并发容量，并确保平台 Pipeline Job 允许并发构建。
// 该脚本由 Docker Compose 挂载到 init.groovy.d，每次 Jenkins 启动时幂等执行。

import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty

def jenkins = Jenkins.get()
def rawExecutorCount = System.getenv('JENKINS_EXECUTORS') ?: '40'
def executorCount

try {
    executorCount = Integer.parseInt(rawExecutorCount)
} catch (NumberFormatException ignored) {
    throw new IllegalArgumentException("JENKINS_EXECUTORS must be an integer: ${rawExecutorCount}")
}

if (executorCount < 1 || executorCount > 100) {
    throw new IllegalArgumentException("JENKINS_EXECUTORS must be between 1 and 100: ${executorCount}")
}

def genericPipelineJobName = System.getenv('JENKINS_GENERIC_PIPELINE_JOB_NAME') ?: 'AiApiTest-DWP-Pipeline'
def failedRerunJobName = System.getenv('JENKINS_FAILED_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Failed-Rerun'
def moduleRerunJobName = System.getenv('JENKINS_MODULE_RERUN_JOB_NAME') ?: 'AiApiTest-DWP-Module-Rerun'
def dailyFullJobPrefix = System.getenv('JENKINS_DAILY_FULL_JOB_PREFIX') ?: 'AiApiTest-DWP-Daily-Full-Module'
def exactJobNames = [genericPipelineJobName, failedRerunJobName, moduleRerunJobName] as Set

jenkins.setNumExecutors(executorCount)
jenkins.getAllItems(WorkflowJob).findAll { job ->
    exactJobNames.contains(job.fullName) || job.fullName == dailyFullJobPrefix || job.fullName.startsWith("${dailyFullJobPrefix}-")
}.each { job ->
    job.removeProperty(DisableConcurrentBuildsJobProperty)
    job.save()
    println "[AiApiTest-DWP] Concurrent builds enabled for ${job.fullName}."
}

jenkins.save()
println "[AiApiTest-DWP] Jenkins controller executors configured: ${executorCount}."
