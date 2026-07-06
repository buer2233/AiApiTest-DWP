# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins每日全量卡死修复-需求简述

## 0. 需求分级与流程裁剪

- **定级结论**：S 档。
- **定级理由**：本次只修复既有 Jenkins 每日全量模块执行 Job 在 `Run API Tests` 阶段卡死的问题，不新增数据表、不新增页面、不变更 DRF API、不改变 api-test 执行协议和 Allure 产物目录结构。
- **裁剪说明**：不新增 UI 原型；沿用 P5 已冻结页面、接口和报告入口设计。保留需求澄清冻结、架构影响评估、API 契约冻结、容器化兼容检查、TDD、回归证据和独立审查。

## 1. 背景

主人在 Jenkins 页面发现 `AiApiTest-DWP-Daily-Full-Module` 的第 3 次构建卡在 `Run API Tests` 阶段。容器内构建日志显示 `tools.ci_runner --from-jenkins-env` 执行后启动了 Allure Web server，并停在 `Press <Ctrl+C> to exit`。该行为会让 Jenkins 非交互构建长期不结束。

## 2. 目标

- Jenkins 每日全量模块 Job 即使手工构建时误勾选 `OPEN_REPORT`，也不能在 CI 内执行 `allure open`。
- `api-test/tools/ci_runner.py` 在 Jenkins 环境变量模式下必须防御性忽略 `OPEN_REPORT=true`，避免其他 Jenkins Job 复现同类卡死。
- Jenkins `Run API Tests` 阶段必须有超时保护，避免 pytest、Allure 或外部依赖异常挂起时长期占用执行器。
- `api-test/tools/ci_runner.py` 必须在 pytest 或 Allure HTML 生成超时时写入可诊断的 `summary.json` 和 `console.log`。
- 本地命令行模式的 `--open-report` 能力保留，不影响开发者手工查看 Allure 报告。
- Jenkins 仍生成并归档 `runtime/ci-runs/<run_id>/` 下的 `summary.json`、`console.log`、`allure-results` 和 `allure-report`。

## 3. 范围

- 修改 `jenkins/scripts/api-test-pipeline.groovy` 的 `OPEN_REPORT` 注入策略。
- 修改 `api-test/tools/ci_runner.py` 的 Jenkins 环境解析逻辑。
- 为 Jenkins `Run API Tests`、pytest 子进程和 Allure HTML 生成增加固定超时防线。
- 补充 Jenkins 静态测试和 api-test 单元测试。
- 留存 Jenkins 控制台根因证据、RED/GREEN 和回归证据。

## 4. 不做事项

- 不修改 Jenkins 凭据、Job 私有配置或 `.env`。
- 不修改 DRF API、Vue 页面、Jenkins Job 名称、报告 URL 同步协议。
- 不移除 `OPEN_REPORT` 参数展示，避免破坏既有 Jenkins 参数表和文档截图；但 CI 执行时强制不打开浏览器服务。

## 5. 需求澄清冻结

- [已澄清] 卡死对象为 `AiApiTest-DWP-Daily-Full-Module` 第 3 次构建，卡点为 `Run API Tests`。
- [已澄清] 本次优先解决 Jenkins 脚本卡死，不扩展为报告服务改造。
- [已澄清] `OPEN_REPORT` 在 CI 中没有实际价值，Jenkins 只需要归档和发布报告入口。
- [待澄清] 无。

## 6. 验收口径

- RED 测试能证明修复前 Jenkins 会把 `OPEN_REPORT=${params.OPEN_REPORT}` 注入 CI，`ci_runner` 会把 Jenkins `OPEN_REPORT=true` 解析为打开报告。
- GREEN 测试证明 Jenkins Pipeline 强制 `OPEN_REPORT=false`，`ci_runner` Jenkins env 忽略 `OPEN_REPORT=true`。
- GREEN 测试证明 `Run API Tests` 有 60 分钟 Jenkins stage 超时，pytest 子进程有 45 分钟超时，Allure HTML 生成有 10 分钟超时，并为 summary、failed node ids 和 console 诊断留出落盘缓冲。
- 手工或自动验证 `Run API Tests` 不再停留在 `allure open` 常驻服务。
- 回归测试通过，且不提交 `.env`、真实凭据、Jenkins 运行产物或本机绝对路径。

## 7. 架构影响评估

- **Jenkins**：影响 `api-test-pipeline.groovy` 的环境变量注入和 `Run API Tests` 超时保护，属于执行安全修复。
- **api-test**：影响 Jenkins env 模式的 `RunRequest.open_report` 解析，并补充 pytest/Allure 子进程超时诊断；CLI `--open-report` 模式不变。
- **DRF / Vue**：无影响。
- **Jenkins 执行链路**：不改变 Job 参数、run_id、summary、Allure 产物路径和归档结构。
- **报告协议**：不变，仍通过 Jenkins artifact 或 Allure 插件入口查看报告。
- **权限 / 数据模型 / Docker**：无新增表、无权限变更、无镜像结构变更。

## 8. API 契约冻结

本次不涉及 DRF API 契约变更。既有 P5 Jenkins 任务 API、模块快照 API 和报告字段保持不变。

## 9. 容器化兼容检查

- 不新增本机绝对路径。
- 不新增宿主机固定端口。
- 不读取或提交真实 `.env`、token、Cookie 或 Jenkins API Token。
- 修复后 Jenkins 容器内只生成静态 Allure HTML 并归档，不启动面向容器本地的常驻 Allure Web server。
- 超时值使用代码内固定默认值，不新增 `.env.example` 变量，不引入额外部署配置。
