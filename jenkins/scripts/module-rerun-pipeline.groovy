// 模块重试 Pipeline。
// 固定传入 RETRY_MODE=module；按 CASE_PATH 执行当前模块全部用例。

def call() {
    def sharedPipeline = load 'jenkins/scripts/api-test-pipeline.groovy'
    sharedPipeline.call([
        mode: 'module',
        includeModuleName: true,
        includeNodeIds: false,
        throttleCategory: 'aiapitest-module-rerun'
    ])
}

return this
