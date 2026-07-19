// 失败重试 Pipeline。
// 固定传入 RETRY_MODE=selected；勾选失败用例和一键失败重试都使用 PYTEST_NODE_IDS。

def call() {
    def sharedPipeline = load 'jenkins/scripts/api-test-pipeline.groovy'
    sharedPipeline.call([
        mode: 'selected',
        includeNodeIds: true,
        requireNodeIds: true,
        emptyNodeIdsMessage: 'PYTEST_NODE_IDS is required for failed rerun',
        throttleCategory: 'aiapitest-failed-rerun'
    ])
}

return this
