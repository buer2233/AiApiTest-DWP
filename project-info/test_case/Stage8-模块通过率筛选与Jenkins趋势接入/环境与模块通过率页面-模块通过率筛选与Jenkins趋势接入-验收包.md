# 环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-验收包

## 1. 验收结论

- 需求定级：M 档，完整 loop。
- 需求状态：已冻结，主人确认所有待选方案采用方案 A。
- 开发状态：后端、前端、Jenkins/Docker 静态兼容检查、真实 `http://127.0.0.1:5174` AI 验收已完成并通过回归。
- 验收建议：通过，等待主人终审签字。备注：本地 Jenkins API 当前缺私有认证变量，触发类接口已证明不再 404/422，但真实 Jenkins 构建返回 503/403，需在本机 `.env` 补 `JENKINS_USERNAME/JENKINS_API_TOKEN` 后验证 202 构建成功路径。

## 2. 本阶段交付范围

- `/modules` 页面删除筛选描述与通过率上限筛选，新增模块开发筛选。
- 模块名称、用例包名、模块开发、模块测试改为后端选项驱动的下拉多选，选项直接来自 `api-test/utils/package_module.yaml`，URL query 使用逗号分隔多值。
- 重置按钮放在查询按钮左侧，清空四个多选筛选并回到第一页。
- 表格列顺序调整为：日期、用例包名、模块名称、执行时间、模块开发、模块测试、总数、失败、跳过、通过率、后置能力；移动端卡片同步该统计顺序。
- 用例详情和模块行的失败重试不再二次确认，直接调用失败重试接口，成功提示固定为 `开始执行失败重试`。
- 模块重试保留二次确认，文案固定为 `模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？`。
- Jenkins 任务弹窗新增状态、日期、任务类型筛选，并区分展示任务类型和任务名。
- 后端新增筛选选项 API、多选精确筛选、Jenkins 任务 `task_type` 筛选和 `sync_jenkins_job_bindings` 管理命令。
- 本地 Jenkins 初始化脚本升级为按 `package_module.yaml` 创建每模块 Daily Job，命名与后端 binding 规则一致。

## 3. 不做事项

- 不新增重复趋势表，继续使用 P3 已建 `module_run_history` 作为趋势独立表。
- 不新增 Jenkins Job 管理页面。
- 不引入 Celery/APScheduler 等后台常驻 worker。
- 不把 Jenkins / Allure 页面 iframe 嵌入平台。
- 不在前端直连 Jenkins 或 Allure API。
- 不提交真实 Jenkins URL、账号、API Token、Cookie、生产地址或本机绝对路径。
- 方案 B 仅归档为候选，不进入前端实现范围。

## 4. 关键代码变更

| 模块 | 文件 | 摘要 |
| --- | --- | --- |
| 后端 API | `../../../back-end/config/urls.py`、`../../../back-end/metrics/views.py`、`../../../back-end/metrics/serializers.py`、`../../../back-end/metrics/module_metadata.py` | 新增 `filter-options`，从 `package_module.yaml` 提供下拉选项，支持多选精确筛选、`module_dev`、Jenkins task_type 筛选和 Swagger 注解 |
| 后端命令 | `../../../back-end/metrics/management/commands/sync_jenkins_job_bindings.py` | 读取 `.env` 中非敏感 Job 名变量，按启用环境和模块幂等 upsert Job binding |
| 后端测试 | `../../../back-end/tests/test_metrics_api.py`、`../../../back-end/tests/test_metrics_commands.py`、`../../../back-end/tests/test_metrics_jenkins_execution_api.py`、`../../../back-end/tests/test_metrics_swagger_docs.py` | 覆盖筛选、命令、Jenkins 任务筛选、权限和 Swagger 契约 |
| 前端页面 | `../../../front-end/src/views/ModulesView.vue` | 方案 A 筛选区、列顺序、URL 同步、环境切换刷新、失败重试直触发、模块重试确认 |
| 前端组件 | `../../../front-end/src/components/metrics/CaseDetailsDialog.vue`、`../../../front-end/src/components/metrics/JenkinsTasksDialog.vue`、`../../../front-end/src/components/metrics/ReadOnlyActionButtons.vue` | 用例详情提示文案、Jenkins 任务筛选、按钮宽度适配 |
| 前端 API/类型 | `../../../front-end/src/api/metrics.ts`、`../../../front-end/src/types/metrics.ts` | 新增筛选选项 API helper、筛选类型和任务类型筛选参数 |
| 前端测试 | `../../../front-end/e2e/stage8-module-filters-jenkins.spec.ts`、`../../../front-end/tests/stage8-metrics-api.test.ts` | Stage8 Playwright 和 Vitest 契约测试 |
| Jenkins/Docker | `../../../docker-compose.yml`、`../../../jenkins/scripts/configure-local-mounted-jobs.groovy`、`../../../jenkins/tests/test_pipeline_static.py`、`../../../jenkins/tests/test_docker_deployment_static.py`、`../../../jenkins/README.md` | Jenkins Job 名变量注入、每模块 Daily Job 初始化和静态回归 |

## 5. 验证证据

| 阶段 | 命令 | 证据 | 结论 |
| --- | --- | --- | --- |
| 前端 API RED | `npm run test:unit -- tests/stage8-metrics-api.test.ts` | `../../../front-end/tests/evidence/stage8-frontend-api-red-20260707.txt` | 失败符合预期，缺 `fetchModuleSnapshotFilterOptions` |
| 前端 Playwright RED | `npm run test:e2e -- e2e/stage8-module-filters-jenkins.spec.ts --project=chromium` | `../../../front-end/tests/evidence/stage8-frontend-playwright-red-20260707.txt` | 失败符合预期，旧 UI/交互不满足 Stage8 |
| 后端目标 GREEN | `python -m pytest tests/test_metrics_api.py tests/test_metrics_commands.py tests/test_metrics_jenkins_execution_api.py tests/test_metrics_swagger_docs.py` | `../../../back-end/tests/evidence/backend-stage8-phase5-target-green-20260707.txt` | 55 passed，覆盖率 72% |
| 后端全量 GREEN | `python -m pytest` | `../../../back-end/tests/evidence/backend-stage8-phase5-full-green-20260707.txt` | 140 passed，覆盖率 89% |
| Django 系统检查 | `python manage.py check` | `../../../back-end/tests/evidence/backend-stage8-phase5-manage-check-20260707.txt` | 无系统检查错误 |
| Django 迁移检查 | `python manage.py makemigrations --check --dry-run` | `../../../back-end/tests/evidence/backend-stage8-phase5-makemigrations-check-20260707.txt` | No changes detected |
| 前端 API GREEN | `npm run test:unit -- tests/stage8-metrics-api.test.ts` | `../../../front-end/tests/evidence/stage8-frontend-api-green-20260707.txt` | 3 passed |
| Stage8 目标 E2E GREEN | `npm run test:e2e -- e2e/stage8-module-filters-jenkins.spec.ts --project=chromium` | `../../../front-end/tests/evidence/stage8-frontend-playwright-green-with-screenshots-20260707.txt` | 8 passed |
| 前端 typecheck | `npm run typecheck` | `../../../front-end/tests/evidence/stage8-frontend-typecheck-green-20260707.txt` | 通过 |
| 前端全量 Vitest | `npm run test:unit` | `../../../front-end/tests/evidence/stage8-frontend-unit-full-20260707.txt` | 6 files / 12 tests passed |
| 前端全量 Playwright | `npm run test:e2e` | `../../../front-end/tests/evidence/stage8-frontend-playwright-full-green-20260707.txt` | 51 passed，1 skipped（既有 `.local` 真服务回归） |
| 前端生产构建 | `npm run build` | `../../../front-end/tests/evidence/stage8-frontend-build-green-20260707.txt` | 构建通过；存在既有 Rollup PURE 注释和 chunk size warning |
| Jenkins/Docker 静态回归 | `python -m pytest jenkins/tests/test_docker_deployment_static.py jenkins/tests/test_pipeline_static.py` | `../../../jenkins/tests/evidence/jenkins-stage8-phase7-static-20260707.txt` | 41 passed |
| AI 真实 5174 验收 | `STAGE8_REAL_ACCEPTANCE=1 STAGE8_REAL_BASE_URL=http://127.0.0.1:5174 npm run test:e2e -- e2e/stage8-real-acceptance.spec.ts --project=chromium` | `../../../front-end/tests/evidence/stage8-real-acceptance-5174-20260707.txt`、`../../../front-end/tests/evidence/screenshots/stage8-real-acceptance-modules-20260707.png` | 1 passed；filter-options 200 且来自 YAML；查询/重置、Jenkins 任务、右侧 70% 抽屉、一键失败重试和模块重试请求均已在真实页面执行 |

## 6. 截图证据

| 截图 | 路径 | 验收点 |
| --- | --- | --- |
| 模块页桌面筛选 | `../../../front-end/tests/evidence/screenshots/stage8-modules-filters-desktop-20260707.png` | 筛选区、重置按钮、列顺序、失败重试提示、模块重试确认 |
| 用例详情失败重试 | `../../../front-end/tests/evidence/screenshots/stage8-case-details-retry-20260707.png` | 选中重试和一键失败重试直接触发后提示 |
| Jenkins 任务筛选 | `../../../front-end/tests/evidence/screenshots/stage8-jenkins-tasks-filters-20260707.png` | 状态、日期、任务类型筛选和任务类型/任务名展示 |
| 模块页移动端 | `../../../front-end/tests/evidence/screenshots/stage8-modules-mobile-20260707.png` | 移动端通过率位于统计字段之后且不溢出 |
| 真实 5174 AI 验收 | `../../../front-end/tests/evidence/screenshots/stage8-real-acceptance-modules-20260707.png` | 真实服务页面完成筛选、查询/重置、Jenkins 任务、用例详情抽屉、失败重试和模块重试动作 |

## 7. 容器化兼容检查

- Stage8 未新增未登记环境变量；使用 `.env.example` 已声明的 `JENKINS_FAILED_RERUN_JOB_NAME`、`JENKINS_MODULE_RERUN_JOB_NAME`、`JENKINS_DAILY_FULL_JOB_PREFIX`。
- `docker-compose.yml` 将上述 Job 名变量传入 Jenkins 容器，保证本地 Job 初始化脚本与后端 binding 命令读取同一套配置。
- `configure-local-mounted-jobs.groovy` 使用 `AIAPITEST_LOCAL_WORKSPACE` 指定容器内挂载仓库，不写本机盘符路径；Daily 模块来源为仓库相对文件 `api-test/utils/package_module.yaml`。
- 前端只调用 DRF 相对 API；Jenkins / Allure 入口仅使用后端返回的 URL。
- `.env.example` 中 localhost / 127.0.0.1 为本地模板示例，注释已说明 Compose 内部 Jenkins API 可改为 `http://jenkins:8080`。

## 8. 独立审查

- 后端 Phase 5 独立审查：Critical 无，Important 无；Minor 已处理或记录。
- 前端 Phase 6 独立审查：发现环境切换后 URL 和列表未同步的 Important，已修复并补 Playwright 回归。
- Phase 7 容器化只读审查：发现本地 Jenkins Daily Job 与后端 binding 命名不一致的 Important，已补 RED 静态测试并修复为每模块 Daily Job；Jenkins/Docker 回归 41 passed。
- Phase 8 整体独立对抗审查：发现 3 个 Important，均已补 RED 测试并修复：
  - Jenkins 任务弹窗 `job_name` 返回真实 `job_full_name`，避免任务类型和任务名都显示为中文类型名。
  - 批量 Daily 同步捕获 Jenkins discovery / artifact 拉取异常，返回 `503 jenkins_unavailable`，不让接口变成 500。
  - `pass_rate_lte` 继续兼容旧 URL，但从 Stage8 OpenAPI 主契约移除。
- Phase 8 复审：Critical 无、Important 无、Minor 无，三项 Important 已闭环。

## 9. 残余风险与人工验收建议

- Jenkins 本地脚本已通过静态测试，但未在真实 Jenkins Script Console 中自动执行。人工联调时需在 `LOCAL_WORKSPACE_REPO=true` 的本地 Jenkins 中执行 `jenkins/scripts/configure-local-mounted-jobs.groovy`，确认生成 `JENKINS_DAILY_FULL_JOB_PREFIX-<package_name>` 每模块 Daily Job。
- 批量 Daily 同步在“新发现 build 后拉取 artifact 失败”时可能已创建 running task/run，再返回 `503 jenkins_unavailable`。这是可观测的部分同步状态；后续再次同步同一 build 会复用该 task 并继续拉取结果。
- 当前本机 Jenkins 8080 要求认证，但根 `.env` 未配置私有 `JENKINS_USERNAME/JENKINS_API_TOKEN`。真实 5174 AI 验收已验证平台按钮请求不再 404/422、动作已绑定；触发 Jenkins 构建的 202 成功路径需在补齐私有 Jenkins API 凭据后复测。
- 后续 loop 的最终审查必须运行真实地址 Playwright 验收；mock Playwright/Vitest/pytest 只能作为开发回归，不可替代主人验收前的真实端到端测试。

## 10. 主人终审签字

- 终审人：主人
- 终审日期：
- 终审结论：
- 备注：
