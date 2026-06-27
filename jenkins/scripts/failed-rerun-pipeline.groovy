// 失败重试 Pipeline（Jenkins job：api-test-failed-rerun）。
// selected：按指定 pytest node id 重试；all-failed：重试上次全部失败用例。
def call() {
    properties([
        parameters([
            choice(
                name: 'RETRY_MODE',
                choices: ['selected', 'all-failed'].join('\n'),
                description: '失败重试模式：selected 按 node id；all-failed 重试上次全部失败'
            ),
            text(
                name: 'PYTEST_NODE_IDS',
                defaultValue: '',
                description: 'selected 模式下的 pytest node ids（换行或逗号分隔）'
            ),
            string(
                name: 'CASE_PATH',
                defaultValue: 'test_case',
                description: 'all-failed 模式下回退使用的用例路径'
            ),
            string(
                name: 'RETRY_COUNT',
                defaultValue: '0',
                description: 'pytest-rerunfailures 重试次数'
            )
        ])
    ])

    def common = load 'jenkins/scripts/lib/pipeline-common.groovy'
    // RETRY_MODE 由操作者在 selected / all-failed 间选择，node id 经 PYTEST_NODE_IDS 传入。
    withEnv([
        "RETRY_MODE=${params.RETRY_MODE}",
        "PYTEST_NODE_IDS=${params.PYTEST_NODE_IDS ?: ''}",
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
