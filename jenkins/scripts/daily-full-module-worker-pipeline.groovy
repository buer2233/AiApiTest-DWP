// Daily Worker 只执行父任务分派的一个模块；YAML 发现、预检和聚合由父任务委托 Task 1 工具。

def call() {
    def sharedPipeline = load 'jenkins/scripts/api-test-pipeline.groovy'
    sharedPipeline.call([
        mode: 'none',
        includeModuleName: true,
        includeNodeIds: false,
        includeTargetBaseUrl: true,
        requireCasePath: true,
        emptyCasePathMessage: 'CASE_PATH is required for Daily Worker',
        throttleCategory: 'aiapitest-daily-worker'
    ])
}

return this
