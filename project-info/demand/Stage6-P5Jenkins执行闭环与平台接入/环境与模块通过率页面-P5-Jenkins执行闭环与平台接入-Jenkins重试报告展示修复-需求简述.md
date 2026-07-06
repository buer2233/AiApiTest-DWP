# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins重试报告展示修复-需求简述

## 0. 定级与裁剪

- 定级：S 档。
- 原因：本次只核查并补强既有失败重试、模块重试 Jenkins Job 的 Allure 报告展示链路和本地挂载 Job 配置，不新增数据表、不新增页面、不变更 DRF API。
- 裁剪：不新增 UI 原型；沿用 P5 已冻结 Jenkins 执行闭环需求。保留架构影响、API 契约、容器化兼容检查、TDD、真实 Jenkins 回归和提交验收。

## 1. 背景

每日全量 Job 已完成本地报告保留和 Jenkins Allure 插件展示验证。主人要求继续检查失败重试 Job 与模块重试 Job，确认测试结束后同样能在 Jenkins Job 页面通过 Allure 插件查看对应报告。

## 2. 范围

- 检查 `jenkins/scripts/failed-rerun-pipeline.groovy`。
- 检查 `jenkins/scripts/module-rerun-pipeline.groovy`。
- 确认两条业务 Pipeline 均复用 `jenkins/scripts/api-test-pipeline.groovy` 的 runtime 归档、30 天保留和 `Publish Allure` 阶段。
- 修复本地挂载 Job 在多个 Job 同时运行时被 Jenkins 分配到 `@2` 空目录的问题。

## 3. 不做事项

- 不调整 api-test 执行协议。
- 不改变测试用例选择规则。
- 不修改平台 DRF / Vue 接口。
- 不提交本地 `.env`、Jenkins home、`api-test/runtime` 或 Allure 运行产物。

## 4. 验收口径

- 失败重试 Job 执行完成后，`summary.json` 中 `allure_report_status=generated`。
- 模块重试 Job 执行完成后，`summary.json` 中 `allure_report_status=generated`。
- 两个 Job 的 Jenkins build archive 中均存在 `allure-report.zip` 和 `allure-summary.json`。
- 控制台日志中 `Publish Allure` 阶段使用 `Allure Commandline`。
- 本地挂载 Job 不再进入 `/workspace/AiApiTest-DWP@2`。

## 5. 架构影响与兼容检查

- DRF：无影响。
- Vue：无影响。
- Jenkins：修复本地 Job 配置脚本，业务 Pipeline 继续复用共享脚本。
- api-test：无协议变更。
- Docker：不新增镜像参数；沿用当前工具链镜像和挂载路径。
- 数据模型：无影响。
- 权限：无影响。
- 报告协议：保持 `runtime/ci-runs/<run_id>`、Allure 插件发布和 artifact 兜底归档不变。

## 6. API 契约

本次不涉及 DRF API 契约变更。
