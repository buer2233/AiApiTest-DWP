// 每日全量模块执行 Pipeline。
// 固定传入 RETRY_MODE=none；每个模块在 Jenkins 中配置一个独立 Job 和 CASE_PATH。

def call() {
    def sharedPipeline = load 'jenkins/scripts/api-test-pipeline.groovy'
    sharedPipeline.call([
        mode: 'none',
        includeModuleName: true,
        includeNodeIds: false,
        requireCasePath: true,
        casePathDefaultEnv: 'JENKINS_MODULE_CASE_PATH',
        emptyCasePathMessage: 'CASE_PATH is required for this Jenkins job',
        jobTriggers: [cron('0 2 * * *')]
    ])
}

return this
