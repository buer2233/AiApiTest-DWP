// 每日全量 Pipeline（Jenkins job：api-test-daily-full）。
// 定时触发，跑全部用例，不做失败重试（retry-mode none）。
def call() {
    properties([
        // 每日凌晨触发；cron 用 H 让 Jenkins 在该小时内打散，避免集中峰值。
        pipelineTriggers([cron('H 2 * * *')])
    ])

    def common = load 'jenkins/scripts/lib/pipeline-common.groovy'
    // 全量 + 不重试，模式固定，不暴露给操作者。
    withEnv([
        'RETRY_MODE=none',
        'CASE_PATH=test_case',
        'CLEAN_ALLURE=true',
        'OPEN_REPORT=false',
        "RUN_ID=${common.resolveRunId()}",
        'CI_RUNNER_ENV=jenkins'
    ]) {
        common.runStages()
    }
}

return this
