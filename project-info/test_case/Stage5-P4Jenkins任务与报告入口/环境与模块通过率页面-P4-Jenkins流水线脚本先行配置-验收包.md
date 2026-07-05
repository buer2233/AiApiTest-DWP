# 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 验收包

## 1. 需求概览

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 |
| 需求分级 | M |
| 关联模块 | `jenkins` / `api-test` / `docker`；`back-end`、`front-end` 本阶段不开发执行对接 |
| 需求冻结日期 | 2026-07-05 |
| 本包生成日期 | 2026-07-05 |
| 需求说明 | `project-info/demand/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-需求说明.md` |
| 功能测试用例 | `project-info/test_case/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-功能测试用例.md` |
| Jenkins Job 交互说明 | `project-info/UI/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-JenkinsJob参数交互说明.md` |
| RTM | `project-info/test_case/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-可追溯矩阵.md` |

## 2. 逐条验收结论（对照需求 §12 验收口径）

| AC 编号 | 验收点 | 自测结论 | 证据 | 备注 |
| --- | --- | --- | --- | --- |
| `AC-JENKINS-1.1` | 每个模块每日全量 Job 支持凌晨 2 点自动执行 | ✅Jenkins 实例配置通过 | `AiApiTest-DWP-Daily-Full-Module` config：1 个 `TimerTrigger`，`<spec>0 2 * * *</spec>`；`JENKINS_MODULE_CASE_PATH=test_case/test_gbif_case_module2` | 已清理重复 JobProperty；真实自然触发需等到下一个 02:00 |
| `AC-JENKINS-1.2` | 每日全量手工触发后产物完整 | ✅Jenkins 构建通过 | `AiApiTest-DWP-Daily-Full-Module #2`：`SUCCESS`，duration `44065ms`，归档 `summary.json`、`failed_nodeids.json`、`allure-report/index.html` | summary 中测试状态为 `failed`，原因是示例模块含故意失败用例；Jenkins 任务和报告生成链路通过 |
| `AC-JENKINS-1.3` | 每日全量归档 runtime 并可查看 Allure | ✅Jenkins 构建通过 | `AiApiTest-DWP-Daily-Full-Module #2` 日志：`allure_report_status=generated`、`Archiving artifacts`、`Finished: SUCCESS` | 当前 Jenkins 未安装 Allure 插件，已按设计降级为 runtime artifact 中的 HTML 报告 |
| `AC-JENKINS-1.4` | 每日全量后续同步会更新日期和执行时间 | ✅文档通过 | 需求 §5/§8、`jenkins/README.md`、RTM | 下一阶段平台同步时验证入库 |
| `AC-JENKINS-2.1` | 失败重试只执行传入 node id | ✅Jenkins 构建通过 | `AiApiTest-DWP-Failed-Rerun #2`：`SUCCESS`；参数 `PYTEST_NODE_IDS=test_case/test_gbif_case_module2/test_gbif_api_module2.py::TestGbifModule2API::test_species_search_by_keyword`；summary `status=passed` | 固定 `RETRY_MODE=selected`，不使用 `all-failed` |
| `AC-JENKINS-2.2` | 失败重试未传 node id 明确失败 | ✅自动化契约通过 | `jenkins/scripts/api-test-pipeline.groovy` 中 `error(emptyNodeIdsMessage)`；`python -m pytest jenkins/tests/test_pipeline_static.py -q`：`16 passed` | 本轮 Jenkins 实例验证了有 node id 的成功路径；空参数失败由静态契约覆盖 |
| `AC-JENKINS-2.3` | 失败重试产物完整 | ✅Jenkins 构建通过 | `AiApiTest-DWP-Failed-Rerun #2` 日志：`allure_report_status=generated`、`Archiving artifacts`、`Finished: SUCCESS` | 与每日全量复用同一归档契约 |
| `AC-JENKINS-2.4` | 失败重试后续同步不更新日期和执行时间 | ✅文档通过 | 需求 §5/§8、`jenkins/README.md`、RTM | 下一阶段平台同步时验证入库 |
| `AC-JENKINS-3.1` | 模块重试执行当前模块全部用例 | ✅Jenkins 构建通过 | `AiApiTest-DWP-Module-Rerun #2`：`SUCCESS`，duration `47238ms`；summary 记录故意失败用例 `test_deliberate_assertion_failure` | 固定 `RETRY_MODE=module`，执行当前模块全部用例 |
| `AC-JENKINS-3.2` | 模块重试产物完整 | ✅Jenkins 构建通过 | `AiApiTest-DWP-Module-Rerun #2` 日志：`allure_report_status=generated`、`Archiving artifacts`、`Finished: SUCCESS` | 与每日全量复用同一归档契约 |
| `AC-JENKINS-3.3` | 模块重试后续同步会更新日期和执行时间 | ✅文档通过 | 需求 §5/§8、`jenkins/README.md`、RTM | 下一阶段平台同步时验证入库 |

## 3. 测试证据

### RED 证据

- 命令：`python -m pytest jenkins/tests/test_pipeline_static.py -q`
- 结果：`6 failed, 8 passed`
- 失败原因：新增契约测试找不到 `jenkins/Jenkinsfile.daily-full-module`、`jenkins/Jenkinsfile.failed-rerun`、`jenkins/Jenkinsfile.module-rerun` 及三条业务 Groovy 脚本，符合 TDD RED 预期。

### GREEN / 回归证据

| 命令 | 结果 | 说明 |
| --- | --- | --- |
| `python -m pytest jenkins/tests/test_pipeline_static.py -q` | `16 passed in 0.13s` | Jenkins Pipeline 静态契约测试，新增 sandbox 安全访问回归 |
| `python -m pytest jenkins/tests -q` | `24 passed in 0.17s` | Jenkins 目录静态回归 |
| `python -m pytest api-test/tests/test_ci_runner.py -q` | `13 passed in 0.20s` | `ci_runner` 执行器契约回归 |

### Jenkins 实例验收证据

| Jenkins Job | 构建号 | Jenkins 结果 | 检出提交 | 关键产物 / 日志 | 业务 summary |
| --- | --- | --- | --- | --- | --- |
| `AiApiTest-DWP-Daily-Full-Module` | `#2` | `SUCCESS` | `d9162ff05957d1cf9bb2c18458f7a8204a4ffaa3` | `allure_report_status=generated`、`Archiving artifacts`、`Finished: SUCCESS`、`allure-report/index.html` 已归档 | `status=failed`，故意失败用例进入 `failed_nodeids` |
| `AiApiTest-DWP-Failed-Rerun` | `#2` | `SUCCESS` | `d9162ff05957d1cf9bb2c18458f7a8204a4ffaa3` | `allure_report_status=generated`、`Archiving artifacts`、`Finished: SUCCESS`、`summary.json` 已归档 | `status=passed`，只执行传入 node id |
| `AiApiTest-DWP-Module-Rerun` | `#2` | `SUCCESS` | `d9162ff05957d1cf9bb2c18458f7a8204a4ffaa3` | `allure_report_status=generated`、`Archiving artifacts`、`Finished: SUCCESS`、`allure-report/index.html` 已归档 | `status=failed`，故意失败用例进入 `failed_nodeids` |

补充修复证据：

- `AiApiTest-DWP-Daily-Full-Module #1` 初次真实构建失败，根因是 Jenkins sandbox 拒绝 `api-test-pipeline.groovy` 中动态下标访问环境变量。
- 已按 TDD 增加静态回归测试 `test_pipeline_uses_sandbox_safe_environment_default_access`，修复为显式读取 `env.JENKINS_MODULE_CASE_PATH` / `env.JENKINS_DEFAULT_CASE_PATH`。
- 修复提交：`d9162ff fix: 兼容 Jenkins sandbox 环境变量默认值`，已推送到 `origin/main_dev_001`。
- #2 三条 Job 日志均无 `Skipped parameter`，参数过滤问题已消除。
- 清理后 Jenkins Job 配置：Daily 仅 1 组参数属性和 1 个 `0 2 * * *` TimerTrigger；Failed-Rerun / Module-Rerun 各 1 组参数属性且无 cron。

### 覆盖率说明

本阶段不修改 DRF 后端或 Vue 前端，不适用后端 pytest-django 覆盖率与前端 Playwright 截图门禁。Jenkins 交付以静态契约测试、`api-test` runner 单测和主人 Jenkins 实例人工验收为证据。

## 4. 一致性报告（RTM 摘要）

- RTM 漂移检查清单结论：自动化、文档和本机 Jenkins 实例构建证据无漂移；后续平台同步项留到下一阶段验证。
- 可追溯矩阵：`环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-可追溯矩阵.md`

## 5. 实现摘要

- **Jenkins**：
  - 新增 `jenkins/Jenkinsfile.daily-full-module`
  - 新增 `jenkins/Jenkinsfile.failed-rerun`
  - 新增 `jenkins/Jenkinsfile.module-rerun`
  - 新增 `jenkins/scripts/daily-full-module-pipeline.groovy`
  - 新增 `jenkins/scripts/failed-rerun-pipeline.groovy`
  - 新增 `jenkins/scripts/module-rerun-pipeline.groovy`
  - 扩展 `jenkins/scripts/api-test-pipeline.groovy`，支持固定业务模式、可选 `MODULE_NAME`、可选 `PYTEST_NODE_IDS`、失败重试空 node id 校验、Job cron 触发配置。
- **测试**：
  - 扩展 `jenkins/tests/test_pipeline_static.py`，覆盖三条业务脚本、固定模式、cron、失败重试 node id 校验、共享执行器、跨平台、归档和 Allure 契约。
- **文档**：
  - 更新 `jenkins/README.md`，补充三类 Jenkins Job 创建方式、参数、触发方式、日期/执行时间语义和人工验收步骤。
- **前后端**：
  - 本阶段未修改 `back-end/` 和 `front-end/`，执行对接留到下一阶段。

## 6. 独立对抗审查

| 审查项 | 结论 | 证据 |
| --- | --- | --- |
| Jenkins 脚本独立审查 | 发现 2 个 P1 阻塞、1 个 P2 测试过拟合、1 个 P3 文档状态问题；均已处理或降为人工验收待执行 | P1-1：每日全量 `CASE_PATH` 改为 per-job `JENKINS_MODULE_CASE_PATH` 默认并缺失失败；P1-2：三个业务 Jenkinsfile 支持 `LOCAL_WORKSPACE_REPO=true` 时跳过初始 checkout；P2：补充静态测试覆盖；P3：验收包已生成并回填证据 |

## 7. 待主人确认项（熔断遗留）

| 编号 | 事项 | agent 的处理 | 需主人确认 |
| --- | --- | --- | --- |
| UAT-1 | Jenkins 实例上创建三类 Job 并执行真实构建 | 已创建三类 Job，并完成 #2 真实构建验收 | 已完成 |
| UAT-2 | 每日全量真实 `0 2 * * *` 定时触发 | Jenkins config 已确认 `TimerTrigger` 为 `0 2 * * *`，并已手工触发 Daily #2 验证执行链路 | 自然定时触发需等待下一个 02:00 产生记录 |

## 8. 已知限制 / 后续项

- 本阶段不做 DRF 触发 Jenkins、Jenkins 任务记录表、执行锁、取消任务接口或结果同步接口。
- 本阶段不做 Vue Jenkins 任务弹窗、失败重试按钮启用、模块重试按钮启用或报告入口展示。
- Jenkins/Allure 外链不叠加平台 Cookie 验证；只有平台 DRF API 需要 Cookie 验证。
- `.env.example` 和 Docker 文档未改动，因为本阶段未新增环境变量、端口、挂载路径或工具链要求。

---

## 验收结论（主人签字）

- [x] 全部 AC 达成（平台同步项按本阶段裁剪留到下一阶段入库验证）
- [x] 自动化测试证据充分可信
- [x] RTM 无自动化/文档漂移
- [x] 待确认项已逐条裁决

**验收人（主人）**：`主人`　**日期**：`2026-07-05`　**结论**：`通过`
