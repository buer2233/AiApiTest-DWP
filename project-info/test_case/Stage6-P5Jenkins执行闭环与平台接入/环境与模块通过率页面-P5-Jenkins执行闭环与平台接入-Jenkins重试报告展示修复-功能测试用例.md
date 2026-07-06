# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins重试报告展示修复-功能测试用例

## TC-RERUN-001 失败重试复用共享 Allure 发布链路

- 优先级：P0
- 前置条件：Jenkins 工具链镜像已安装 Allure 插件并注册 `Allure Commandline`。
- 步骤：
  1. 检查 `failed-rerun-pipeline.groovy`。
  2. 触发 `AiApiTest-DWP-Failed-Rerun`，传入失败用例 node id。
  3. 查看控制台和归档产物。
- 期望：
  - 业务脚本加载 `api-test-pipeline.groovy`。
  - `Publish Allure` 阶段使用 `Allure Commandline`。
  - `summary.json` 的 `allure_report_status` 为 `generated`。
  - Jenkins build archive 存在 `allure-report.zip` 和 `allure-summary.json`。

## TC-RERUN-002 模块重试复用共享 Allure 发布链路

- 优先级：P0
- 前置条件：Jenkins 工具链镜像已安装 Allure 插件并注册 `Allure Commandline`。
- 步骤：
  1. 检查 `module-rerun-pipeline.groovy`。
  2. 触发 `AiApiTest-DWP-Module-Rerun`，传入模块 `CASE_PATH`。
  3. 查看控制台和归档产物。
- 期望：
  - 业务脚本加载 `api-test-pipeline.groovy`。
  - `Publish Allure` 阶段使用 `Allure Commandline`。
  - `summary.json` 的 `allure_report_status` 为 `generated`。
  - Jenkins build archive 存在 `allure-report.zip` 和 `allure-summary.json`。

## TC-RERUN-003 本地挂载 Job 不进入 @2 空目录

- 优先级：P0
- 前置条件：失败重试和模块重试 Job 均使用本地挂载仓库。
- 步骤：
  1. 同时触发失败重试与模块重试。
  2. 检查两个 Job 的控制台日志。
- 期望：
  - 两个 Job 均在 `/workspace/AiApiTest-DWP` 执行。
  - 控制台日志不出现 `/workspace/AiApiTest-DWP@2`。
  - 两个 Job 均成功进入 `Publish Allure` 阶段。
