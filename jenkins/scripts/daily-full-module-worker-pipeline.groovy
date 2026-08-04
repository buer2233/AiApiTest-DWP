// Daily Worker 只执行父任务分派的一个模块；YAML 发现、预检和聚合由父任务委托 Task 1 工具。

def requireDailyParentUpstreamCause() {
    def expectedDailyParentJobName = 'AiApiTest-DWP-Daily-Full-Module'
    def upstreamCauses = currentBuild.getBuildCauses('hudson.model.Cause$UpstreamCause')
    def isExpectedParent = upstreamCauses.any { cause ->
        cause.upstreamProject == expectedDailyParentJobName
    }
    if (!isExpectedParent) {
        error("Daily Worker must be triggered by ${expectedDailyParentJobName}.")
    }
}

def call() {
    // 仅信任 Jenkins 构建原因，不能信任手工/API 调用可伪造的参数。
    requireDailyParentUpstreamCause()
    def sharedPipeline = load 'jenkins/scripts/api-test-pipeline.groovy'
    sharedPipeline.call([
        mode: 'none',
        includeModuleName: true,
        includeNodeIds: false,
        includeTargetBaseUrl: true,
        requireCasePath: true,
        emptyCasePathMessage: 'CASE_PATH is required for Daily Worker',
        throttleCategory: 'aiapitest-daily-worker',
        publishAllure: false
    ])
}

return this
