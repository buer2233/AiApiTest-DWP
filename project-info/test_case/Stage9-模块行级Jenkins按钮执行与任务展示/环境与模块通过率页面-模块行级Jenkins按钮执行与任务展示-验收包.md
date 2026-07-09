# 环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示 验收包

## 1. 交付范围

- 修复后端 Daily 批量同步：`POST /api/v1/jenkins-tasks/sync` 会按 active daily `jenkins_job_binding` 传入 Jenkins job full name。
- 新增前端 DRF 单任务同步封装：`syncJenkinsTask(taskId)`。
- Jenkins 任务弹窗轮询时先调用 `POST /api/v1/jenkins-tasks/{id}/sync`，再刷新任务列表；同步后的任务通过 `taskUpdated` 通知父页面刷新模块列表。
- 补齐 Stage9 需求说明、功能测试用例、UI 映射和 RTM。

## 2. 验证证据

| 类型 | 命令 | 结果 |
| --- | --- | --- |
| 后端 RED | `cd back-end; python -m pytest tests/test_metrics_jenkins_execution_api.py::test_bulk_sync_discovers_daily_builds_with_active_daily_job_names -q` | 先失败，原因是实际调用 `discover_jenkins_builds(date=None)`，缺少 `job_full_names`。 |
| 后端 GREEN 单测 | `cd back-end; python -m pytest tests/test_metrics_jenkins_execution_api.py::test_bulk_sync_discovers_daily_builds_with_active_daily_job_names -q` | 1 passed |
| 后端 P5 Jenkins 回归 | `cd back-end; python -m pytest tests/test_metrics_jenkins_execution_api.py -q` | 32 passed，coverage 总计 60% |
| 后端 Jenkins service/命令回归 | `cd back-end; python -m pytest tests/test_metrics_jenkins_service.py tests/test_metrics_commands.py -q` | 13 passed |
| 前端 API 契约 | `cd front-end; npx vitest run tests/stage6-p5-metrics-api.test.ts --pool=threads --poolOptions.threads.singleThread=true` | 2 tests passed |
| 前端 Stage8 API 回归 | `cd front-end; npx vitest run tests/stage8-metrics-api.test.ts --pool=threads --poolOptions.threads.singleThread=true` | 3 tests passed |
| 前端目标 Playwright | `cd front-end; npx playwright test e2e/stage6-p5-jenkins-execution.spec.ts --grep "轮询运行中任务" --workers=1` | 1 passed |
| 前端 Stage8 Playwright 回归 | `cd front-end; npx playwright test e2e/stage8-module-filters-jenkins.spec.ts --grep "Jenkins 任务弹窗展示任务类型|失败重试直接触发|已有执行中任务" --workers=1` | 3 passed |
| 后端审查修复回归 | `cd back-end; python -m pytest tests/test_metrics_jenkins_execution_api.py::test_daily_discovery_wrapper_accepts_explicit_job_names tests/test_metrics_jenkins_execution_api.py::test_bulk_sync_discovers_daily_builds_with_active_daily_job_names -q` | 2 passed |
| 后端 P5 Jenkins 最终回归 | `cd back-end; python -m pytest tests/test_metrics_jenkins_execution_api.py -q` | 33 passed，coverage 总计 60% |
| 前端类型检查/构建 | `cd front-end; npm run build` | 通过；存在既有 chunk 体积和 Rollup 注释警告 |

## 3. 环境与风险

- `npm run test:unit -- tests/stage6-p5-metrics-api.test.ts` 和通过 `npm run test:e2e -- ... --workers=1` 传参时曾触发 Node OOM 或参数被 npm 吞掉；已改用 `npx vitest` / `npx playwright` 直接执行并通过。
- 真实 Jenkins job 能否触发取决于本地 `.env` 中 Jenkins 私有配置和是否已执行 `python manage.py sync_jenkins_job_bindings`。本阶段不提交真实凭据。
- 前端不直连 Jenkins；所有触发、取消、同步均经 DRF。

## 4. 独立审查与修复

| 发现 | 严重度 | 处理 |
| --- | --- | --- |
| `JenkinsTaskBulkSyncView` 传入 `job_full_names`，但后端 wrapper 不支持该参数，真实请求可能 500 | High | 已扩展 `discover_jenkins_builds(job_full_names=None, date=None)`，并新增真实 wrapper 单测。 |
| 前端 sync 失败错误会被后续 `loadTasks()` 清空 | Medium | `loadTasks` 新增 `preserveError` 选项，sync 失败时保留同步错误。 |
| 轮询整轮刷新无重入锁，慢 GET 时可能并发刷新 | Medium | 新增 `refreshing` 锁，保护 sync + loadTasks 整轮刷新。 |

## 5. 验收结论

- 三个按钮的前端落点和 DRF API 已配置到历史冻结契约。
- Jenkins job 完成后的页面刷新路径已补齐：任务弹窗轮询触发 DRF 同步，DRF 更新任务和模块数据，父页面收到任务更新后刷新模块列表。
- Daily 批量同步的 Jenkins discovery 参数缺口已修复。
