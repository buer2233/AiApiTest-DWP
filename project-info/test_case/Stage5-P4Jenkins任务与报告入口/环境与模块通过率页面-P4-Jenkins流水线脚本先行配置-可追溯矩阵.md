# 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 可追溯矩阵（RTM）

> 本矩阵以冻结需求 §12 的 `AC-JENKINS-*` 为主线，追溯到功能测试用例、Jenkins Job 参数界面、脚本契约、实现位置和验收状态。

## 追溯矩阵

| AC 编号 | 需求功能 | 测试用例编号 | UI 元素 / 页面 | API / 脚本契约 | 实现位置（文件:符号） | 验收状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `AC-JENKINS-1.1` | F2 每日全量凌晨 2 点自动执行 | `TC-JENKINS-F-001` | Jenkins 每日全量 Job 配置页 | `Jenkinsfile.daily-full-module` + `cron('0 2 * * *')` + `JENKINS_MODULE_CASE_PATH` | `jenkins/scripts/daily-full-module-pipeline.groovy:call`、`jenkins/scripts/api-test-pipeline.groovy:buildParameterDefinitions`、`jenkins/Jenkinsfile.daily-full-module` | Jenkins config 已验收：Daily Job 存在 1 个 `0 2 * * *` TimerTrigger |
| `AC-JENKINS-1.2` | F2 每日全量手工触发后产物完整 | `TC-JENKINS-F-002`、`TC-JENKINS-E-001`、`TC-JENKINS-E-002` | Jenkins Build with Parameters / build artifact | `RETRY_MODE=none` + `CASE_PATH` + `tools.ci_runner --from-jenkins-env` | `jenkins/scripts/daily-full-module-pipeline.groovy:call`、`jenkins/scripts/api-test-pipeline.groovy:call` | Jenkins #2 通过，runtime / Allure HTML 已归档 |
| `AC-JENKINS-1.3` | F2 每日全量归档 runtime 并可查看 Allure | `TC-JENKINS-F-003`、`TC-JENKINS-ERR-002` | Jenkins artifact / Allure report | `archiveArtifacts("${runDir}/**")` + `allure(results: ...)` | `jenkins/scripts/api-test-pipeline.groovy:call` | Jenkins #2 通过，`allure_report_status=generated` |
| `AC-JENKINS-1.4` | F2 后续同步会更新日期和执行时间 | `TC-JENKINS-ST-001` | Jenkins Job 说明 / README | 执行类型 `daily_full` / `RETRY_MODE=none`，本阶段无 DRF API | `jenkins/README.md`、需求 §5/§8 | 文档通过；后续接入阶段验证 |
| `AC-JENKINS-2.1` | F6 失败重试只执行传入 node id | `TC-JENKINS-F-004`、`TC-JENKINS-F-005`、`TC-JENKINS-E-002` | Jenkins 失败重试 Job 参数页 | `RETRY_MODE=selected` + `PYTEST_NODE_IDS` | `jenkins/scripts/failed-rerun-pipeline.groovy:call`、`jenkins/scripts/api-test-pipeline.groovy:call` | Jenkins #2 通过，summary `status=passed` |
| `AC-JENKINS-2.2` | F6 未传 node id 明确失败 | `TC-JENKINS-ERR-001` | Jenkins 失败重试 Job 参数页 / console log | `PYTEST_NODE_IDS` 参数校验 | `jenkins/scripts/failed-rerun-pipeline.groovy:call`、`jenkins/scripts/api-test-pipeline.groovy:call` | 自动化契约通过，空参数错误路径由静态测试覆盖 |
| `AC-JENKINS-2.3` | F6 失败重试产物完整 | `TC-JENKINS-F-006`、`TC-JENKINS-E-001`、`TC-JENKINS-ERR-002` | Jenkins artifact / Allure report | 共享归档与 Allure 发布契约 | `jenkins/scripts/api-test-pipeline.groovy:call` | Jenkins #2 通过，runtime / Allure HTML 已归档 |
| `AC-JENKINS-2.4` | F6 后续同步不更新日期和执行时间 | `TC-JENKINS-ST-002` | Jenkins Job 说明 / README | 执行类型 `failed_rerun` / `RETRY_MODE=selected`，本阶段无 DRF API | `jenkins/README.md`、需求 §5/§8 | 文档通过；后续接入阶段验证 |
| `AC-JENKINS-3.1` | F7 模块重试执行当前模块全部用例 | `TC-JENKINS-F-007`、`TC-JENKINS-E-002` | Jenkins 模块重试 Job 参数页 | `RETRY_MODE=module` + `CASE_PATH` | `jenkins/scripts/module-rerun-pipeline.groovy:call`、`jenkins/scripts/api-test-pipeline.groovy:call` | Jenkins #2 通过，summary 捕获模块内故意失败用例 |
| `AC-JENKINS-3.2` | F7 模块重试产物完整 | `TC-JENKINS-F-008`、`TC-JENKINS-E-001`、`TC-JENKINS-ERR-002` | Jenkins artifact / Allure report | 共享归档与 Allure 发布契约 | `jenkins/scripts/api-test-pipeline.groovy:call` | Jenkins #2 通过，runtime / Allure HTML 已归档 |
| `AC-JENKINS-3.3` | F7 后续同步会更新日期和执行时间 | `TC-JENKINS-ST-003` | Jenkins Job 说明 / README | 执行类型 `module_rerun` / `RETRY_MODE=module`，本阶段无 DRF API | `jenkins/README.md`、需求 §5/§8 | 文档通过；后续接入阶段验证 |

## 漂移检查清单（一致性自动门禁）

- [x] **无遗漏需求**：每个需求 AC 都至少有一条测试用例覆盖。
- [x] **无凭空用例**：每条测试用例都能追溯到某个 AC 或全部 AC 的安全前置。
- [x] **无遗漏界面**：本阶段无 Vue 页面；涉及页面的 AC 均映射到 Jenkins Job 参数页、构建详情、artifact 或 Allure 报告。
- [x] **无契约漂移**：本阶段 API 契约裁剪为 Jenkins 脚本契约；三条脚本参数、执行模式和归档契约已在需求 §7 冻结。
- [x] **无未实现需求**：每个 AC 均已回填 Jenkins 脚本、共享脚本或文档实现位置。
- [x] **无孤儿代码**：新增业务脚本、Jenkinsfile、测试和 README 均可追溯到 `AC-JENKINS-*`。
- [x] **全部达成**：自动化门禁通过；本机 Jenkins 实例三条 Job #2 均为 `SUCCESS`；平台同步项留到下一阶段验证。

## 漂移处置记录

| 发现的漂移 | 类型 | 处置（回写需求 / 补用例 / 补实现 / 上报主人） | 状态 |
| --- | --- | --- | --- |
| Daily #1 Jenkins sandbox 拒绝动态环境变量下标访问 | Jenkins 实例验收发现 | 补静态回归测试并修复为显式 `env.JENKINS_MODULE_CASE_PATH` / `env.JENKINS_DEFAULT_CASE_PATH` 访问，提交 `d9162ff`，三条 Job #2 重跑通过 | 已关闭 |
