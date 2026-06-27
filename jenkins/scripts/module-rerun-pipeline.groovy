// 模块重试 Pipeline（Jenkins job：api-test-module-rerun）。按模块路径重跑。
def call() {
    properties([
        parameters([
            string(
                name: 'CASE_PATH',
                defaultValue: 'test_case/test_gbif_case',
                description: '要重跑的模块路径（相对 api-test）'
            ),
            string(
                name: 'RETRY_COUNT',
                defaultValue: '0',
                description: 'pytest-rerunfailures 重试次数'
            )
        ])
    ])

    def common = load 'jenkins/scripts/lib/pipeline-common.groovy'
    // 模式固定为 module；CASE_PATH 由操作者通过参数指定。
    withEnv([
        'RETRY_MODE=module',
        "CASE_PATH=${params.CASE_PATH}",
        "RETRY_COUNT=${params.RETRY_COUNT}",
        'CLEAN_ALLURE=true',
        'OPEN_REPORT=false',
        "RUN_ID=${common.resolveRunId()}",
        'CI_RUNNER_ENV=jenkins'
    ]) {
        common.runStages()
    }
}

return this
