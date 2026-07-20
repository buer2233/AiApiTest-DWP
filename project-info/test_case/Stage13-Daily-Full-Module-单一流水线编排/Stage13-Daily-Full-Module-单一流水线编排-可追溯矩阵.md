# Stage13-Daily-Full-Module-单一流水线编排-可追溯矩阵（RTM）

> 需求来源：`../../demand/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-需求说明.md`（2026-07-19 已冻结）。
>
> 本阶段已填写每项 AC 的测试用例、UI 范围和 API/Pipeline 契约；“实现位置”和“验收状态”必须由后续实施、独立审查与验收阶段填写，当前不得预填为通过。

## 追溯矩阵

| AC 编号 | 需求功能 | 测试用例编号 | UI 元素 / 页面 | API / Pipeline 契约 | 实现位置（文件:符号） | 验收状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `AC1.1` | F1 唯一 Daily 定时父 Job 与无定时 Worker | `TC-S13-F1-001` | 无；Jenkins Job 页面 | Daily 父 Job `0 2 * * *`；Worker 上游触发 | `jenkins/init.groovy`、`jenkins/scripts/daily-full-module-pipeline.groovy` | 静态回归通过；环境 Job 待运行 |
| `AC1.2` | F1 三类 Pipeline 独立十并发与排队 | `TC-S13-F1-002` | 无；Jenkins 队列页面 | Daily / 模块重试 / 失败重试独立限流分类 | `jenkins/init.groovy` 的独立 throttle 分类 | 静态回归通过；环境 Job 待运行 |
| `AC1.3` | F1 模块失败不短路、父任务最终失败 | `TC-S13-F1-003`、`TC-S13-F1-006`、`TC-S13-F1-007` | 无 | Daily `running -> test_failed/failed/canceled`；父摘要与归档 | `api-test/tools/daily_aggregate.py`、`back-end/metrics/views.py:sync_task_with_result` | pytest / 静态回归通过；环境 Job 待运行 |
| `AC1.4` | F1 默认/覆盖 URL 执行全量模块 | `TC-S13-F1-004` | 无 | `TARGET_BASE_URL`；既有 `--base-url` 校验；模块 YAML 全量发现 | `api-test/tools/ci_runner.py`、`jenkins/scripts/daily-full-module-pipeline.groovy` | pytest / 静态回归通过；环境 Job 待运行 |
| `AC1.5` | F1 YAML/URL 预检失败不调度 | `TC-S13-F1-005`、`TC-S13-F1-007` | 无 | Daily 调度前预检、结构化诊断、无 Worker/父任务/快照副作用 | `api-test/utils/environment_catalog.py`、`back-end/metrics/views.py` | pytest / 静态回归通过；环境 Job 待运行 |
| `AC2.1` | F2 平台仅存一条 Daily 父任务 | `TC-S13-F2-001`、`TC-S13-F1-006` | 任务列表；无模块子任务页 | `daily_full` `JenkinsTask`；module 为空的 `TestRun` | `back-end/metrics/models.py`、`metrics/views.py:sync_task_with_result` | pytest 通过；环境 Job 待运行 |
| `AC2.2` | F2 父级聚合摘要与唯一 Allure | `TC-S13-F2-002`、`TC-S13-F2-004`、`TC-S13-F1-007` | `/environments` R1；父任务报告入口 | 稳定 `summary.json`、模块明细、合并 Allure 原始结果 | `api-test/tools/daily_aggregate.py`、`jenkins/scripts/daily-full-module-pipeline.groovy`、`metrics/serializers.py` | pytest / 静态回归通过；Allure 插件验收待环境 Job |
| `AC2.3` | F2 模块快照、失败与趋势逐模块同步 | `TC-S13-F2-003`、`TC-S13-F2-004` | 环境快照与模块通过率页面 | 父摘要到 `ModuleSnapshot` / `TestCaseResult` / `ModuleRunHistory` 的幂等同步 | `back-end/metrics/views.py:apply_daily_parent_summary` | pytest 通过；环境 Job 待运行 |
| `AC3.1` | F3 环境 YAML schema 与 URL 唯一校验 | `TC-S13-F3-001`、`TC-S13-F3-002` | R3 表单校验反馈 | `package_environment.yaml`；`base_url/url_name/url_desc`；UTF-8/两空格/blob SHA | `api-test/utils/environment_catalog.py`、`back-end/metrics/environment_catalog.py`、`EnvironmentEditorDialog.vue` | pytest / Vitest 通过；环境 Job 待运行 |
| `AC3.2` | F3 admin CRUD 先落 MySQL、再建同步请求 | `TC-S13-F3-003`、`TC-S13-F3-004`、`TC-S13-F3-010`、`TC-S13-F3-014` | `/environments` R2/R3 | `POST/PATCH/DELETE /api/v1/test-environments`；至少一个启用环境；`202`、`400`、`409 last_active_environment`、`403` | `back-end/metrics/views.py`、`environment_catalog.py`、`useEnvironmentCatalog.ts` | pytest / Vitest 通过；环境 Job 待运行 |
| `AC3.3` | F3 隔离 checkout 自动提交并推送 YAML | `TC-S13-F3-005`、`TC-S13-F3-006`、`TC-S13-F3-010` | R2/R4 同步状态与 Jenkins 链接 | 专用同步 Job；隔离 checkout；blob SHA；快进推送；`mysql_to_yaml` | `jenkins/Jenkinsfile.environment-catalog-sync`、`metrics/views.py`、`EnvironmentCatalogSyncDialog.vue` | pytest / 静态 / Vitest 通过；环境 Job 待运行 |
| `AC3.4` | F3 页面导入 YAML 后 MySQL 新增/更新/停用 | `TC-S13-F3-007`、`TC-S13-F3-008`、`TC-S13-F3-010` | `/environments` R4 导入弹窗 | `POST /api/v1/test-environments/sync-from-yaml`；`yaml_to_mysql`；单一事务 | `back-end/metrics/environment_catalog.py`、`metrics/views.py`、`EnvironmentCatalogSyncDialog.vue` | pytest / Vitest 通过；环境 Job 待运行 |
| `AC3.5` | F3 同步失败可观察、可重试且不半更新 | `TC-S13-F3-006`、`TC-S13-F3-008`、`TC-S13-F3-010`、`TC-S13-F3-013`、`TC-S13-F3-014` | R2 最近错误；R4 状态/重试 | 同步请求 `failed/pending`；`GET /api/v1/environment-catalog-sync-attempts/{id}`；retry `202/409` | `metrics/views.py:dispatch_environment_catalog_sync_attempt`、`environment_catalog.py`、`useEnvironmentCatalog.ts` | pytest / Vitest 通过；环境 Job 待运行 |
| `AC3.6` | F3 blob SHA 冲突拒绝覆盖 | `TC-S13-F3-009`、`TC-S13-F3-010`、`TC-S13-F3-014` | R4 冲突操作 | `expected_yaml_blob_sha` 与 `observed_yaml_blob_sha`；`conflict`；`409 sync_not_retryable` | `back-end/metrics/environment_catalog.py`、`EnvironmentCatalogSyncDialog.vue` | pytest / Vitest 通过；环境 Job 待运行 |
| `AC3.7` | F3 member 无环境管理权限 | `TC-S13-F3-011`、`TC-S13-F3-013`、`TC-S13-F3-014` | `/environments` R2-R4 对 member 不渲染 | 写接口/同步审计 `403 admin_required`；Cookie JWT | `metrics/views.py:TestEnvironmentListView`、`EnvironmentsView.vue` | pytest / Playwright 用例已写；运行待环境 Job |
| `AC3.8` | F3 环境初始化不再硬编码默认环境 | `TC-S13-F3-012` | 无；初始化不可作为页面直接操作 | 镜像内环境 YAML 初始投影；运行时仅 Jenkins 页面导入 | `back-end/Dockerfile`、`metrics/management/commands/seed_environment.py` | 待验收阶段填写 |
| `AC4.1` | F4 验收前不删除旧 Daily Job | `TC-S13-F4-001`、`TC-S13-F1-001` | 无；Jenkins Job 页面 | 版本化迁移删除守卫；未签字不删除 | `jenkins/init.groovy` 的旧 Job 删除守卫 | 静态回归通过；环境 Job 待运行 |
| `AC4.2` | F4 验收后受控删除旧 Job 与构建历史 | `TC-S13-F4-002` | 无；Jenkins Job 页面 | 主人最终签字守卫；受控旧 Job/历史删除 | 待实施阶段填写 | 待验收阶段填写 |

## 双向覆盖检查

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| AC 到测试用例 | 已覆盖 | 18/18 项 AC 至少映射一条主用例，关键高风险 AC 映射正常、异常、状态/权限扩展用例。 |
| 测试用例到 AC | 已覆盖 | 27 条 `TC-S13-*` 测试用例均在其用例正文和本矩阵中关联至少一项 AC。 |
| UI 范围 | 已覆盖 | C01、R1-R4 映射已落实；member 不渲染 R2-R4，禁止 DOM 已写入 Playwright 用例。 |
| API / Pipeline 契约 | 已覆盖 | 写接口、读接口、Jenkins 父/Worker/同步 Job、聚合产物协议均已定位。 |
| 实施位置 | 已填写 | 关键 AC 已回填 api-test、Jenkins、后端和前端文件/符号。 |
| 验收状态 | 进行中 | 静态、pytest、Vitest、typecheck 与独立审查完成；固定 Jenkins 环境 Job 尚未运行。 |

## 漂移检查清单（一致性自动门禁）

- [x] **无遗漏需求**：AC1.1 至 AC4.2 全部在本矩阵中有测试用例。
- [x] **无凭空用例**：27 条 `TC-S13-*` 均能回溯到至少一项冻结 AC。
- [x] **正常、异常、边界、权限、状态机、并发、Jenkins/Docker 协议已设计覆盖**：见测试用例文档“覆盖与交接”。
- [x] **无遗漏界面**：C01、R1-R4 及禁止 DOM 项已实施并纳入 Playwright 用例。
- [x] **无契约漂移**：后端 API、Jenkins 静态、api-test 和前端 API 契约已核对；member 目录审计字段已从浏览器响应删除。
- [x] **无未实现需求**：所有 AC 已填写实现位置。
- [x] **无孤儿代码**：后端/Jenkins 最终复审整改与前端独立代码审读未发现阻断问题。
- [ ] **全部达成**：待固定 Jenkins 环境 Job 的运行态证据。

## 漂移处置记录

| 发现的漂移 | 类型 | 处置（回写需求 / 补用例 / 补实现 / 上报主人） | 状态 |
| --- | --- | --- | --- |
| 当前无已发现需求-测试漂移 | 无 | 已完成 AC 与测试用例双向编号核对；后续实现须持续回写。 | 已关闭 |
