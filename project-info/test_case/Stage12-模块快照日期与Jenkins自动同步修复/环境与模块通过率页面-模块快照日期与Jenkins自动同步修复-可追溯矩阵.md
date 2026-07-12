# 环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-可追溯矩阵（RTM）

> 需求来源：`../../demand/Stage12-模块快照日期与Jenkins自动同步修复/环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-需求说明.md`。
>
> 当前已进入回归与真实验收阶段。本矩阵区分“自动测试通过”“真实验证通过”和“真实验证待观察”；自动化通过不能替代尚未发生的真实 02:00 触发或双 worker 进程并发。

## 1. 追溯矩阵

| AC 编号 | 需求功能 | 测试用例编号 | UI / API / 命令 | 实现位置（文件:符号） | 验证证据 | 验收状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `AC-S12-1.1` | F1 queueId 精确恢复并同次同步 | `TC-S12-F1-001/009/010` | 单任务 sync；既有任务弹窗 | `back-end/metrics/jenkins_service.py:_recover_build_from_expired_queue,fetch_jenkins_task_result`；`back-end/metrics/views.py:sync_task_with_result,JenkinsTaskSyncView` | 后端 209 passed；真实接口验收证据中 task 58 sync=200；验收包 §3.4 数据复核 | 通过（自动+真实） |
| `AC-S12-1.2` | F1 RUN_ID 精确恢复 | `TC-S12-F1-002` | 单任务 sync；无新增 UI | `back-end/metrics/jenkins_service.py:_build_parameter,_recover_build_from_expired_queue` | `./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-后端pytest覆盖率证据.txt` | 通过（自动） |
| `AC-S12-1.3` | F1 并发 build 精确隔离 | `TC-S12-F1-003/007` | 单任务 sync 409；批量 sync 200；无新增 UI | `back-end/metrics/jenkins_service.py:JenkinsBuildMatchError,_recover_build_from_expired_queue`；`back-end/metrics/views.py:record_jenkins_build_match_error,JenkinsTaskSyncView,JenkinsTaskBulkSyncView` | 定向测试覆盖 queueId/RUN_ID 双分支、单任务 409、状态/锁保持及批量不误报 503 | 通过（自动） |
| `AC-S12-1.4` | F1 queue 404 暂无 build 时保持 queued | `TC-S12-F1-004/008` | 单任务 sync；任务弹窗保持 queued | `back-end/metrics/jenkins_service.py:fetch_jenkins_task_result`；`back-end/metrics/views.py:sync_task_with_result` | 后端 pytest 证据；`test_fetch_task_result_keeps_queue_pending_when_expired_queue_has_no_matching_build` | 通过（自动） |
| `AC-S12-1.5` | F1 Jenkins 真不可用返回 503 | `TC-S12-F1-005/009` | 单任务 sync 503 `jenkins_unavailable` | `back-end/metrics/jenkins_service.py:_request,fetch_jenkins_task_result`；`back-end/metrics/views.py:JenkinsTaskSyncView` | 后端 209 passed 与 API 错误分类回归 | 通过（自动） |
| `AC-S12-1.6` | F1 新任务前刷新旧锁并恢复真实 build | `TC-S12-F1-006` | 既有模块重试触发接口 | `back-end/metrics/views.py:refresh_module_execution_state,create_queued_jenkins_task,sync_task_with_result` | 组件测试及 task 57/58 真实恢复、锁释放已验证；“恢复后紧接新触发”组合场景未单独执行 | 部分通过（组合场景待观察） |
| `AC-S12-2.1` | F2 延迟同步使用 Jenkins 实际完成日 | `TC-S12-F2-001/009` | 模块日期、趋势 API | `back-end/metrics/jenkins_service.py:_build_times`；`back-end/metrics/views.py:apply_module_summary,ModuleSnapshotTrendView` | 后端 209 passed；桌面/移动截图均显示 2026/7/12；验收包 §3.4 | 通过（自动+真实） |
| `AC-S12-2.2` | F2 跨表完成时间一致 | `TC-S12-F2-002/007/008/010` | 模块日期/执行时间、趋势 | `back-end/metrics/views.py:sync_task_with_result,apply_module_summary` | 后端 pytest；真实 task 57/58、模块 1/2、趋势历史数据复核；Playwright 1 passed | 通过（自动+真实） |
| `AC-S12-2.3` | F2 失败重试不改模块时间 | `TC-S12-F2-003` | 既有模块表格和趋势 | `back-end/metrics/views.py:apply_failed_rerun_summary` | 后端 pytest `test_sync_failed_retry_test_failed_updates_cases_without_touching_module_execution_time` | 通过（自动） |
| `AC-S12-2.4` | F2 非法时间兜底与脱敏警告 | `TC-S12-F2-004/005/006` | 无新增 UI | `back-end/metrics/jenkins_service.py:_build_times`；`back-end/metrics/views.py:sync_task_with_result` | 后端 pytest覆盖非法 duration 与同步时刻 fallback | 通过（自动） |
| `AC-S12-3.1` | F3 worker 自动同步模块重试 | `TC-S12-F3-001/002/003/010/014` | `sync_jenkins_results --once/--watch`；既有模块页 | `back-end/metrics/jenkins_sync.py:run_jenkins_sync_cycle`；`back-end/metrics/management/commands/sync_jenkins_results.py:Command` | 命令/worker pytest通过；worker 真实运行证据记录稳定轮询与故障恢复；Playwright 可见结果通过 | 部分通过（真实新 build 自动处理待观察） |
| `AC-S12-3.2` | F3 自动发现分模块 Daily build | `TC-S12-F3-004` | worker Daily discovery | `back-end/metrics/jenkins_sync.py:run_jenkins_sync_cycle`；`back-end/metrics/views.py:create_or_get_daily_task_from_discovery` | worker pytest覆盖发现与同步；真实 Job/cron 已就绪 | 部分通过（下一次 02:00 待观察） |
| `AC-S12-3.3` | F3 重复发现幂等 | `TC-S12-F1-010/F2-010/F3-005/F3-013` | worker 与内部同步服务 | `back-end/metrics/jenkins_sync.py:run_jenkins_sync_cycle`；`back-end/metrics/views.py:create_or_get_daily_task_from_discovery,sync_task_with_result` | 后端 pytest覆盖重复两轮、终态 skip 和唯一键复用 | 通过（自动） |
| `AC-S12-3.4` | F3 单 Job 失败隔离并可恢复 | `TC-S12-F3-006/008/009/011/012` | worker；批量 sync | `back-end/metrics/jenkins_sync.py:run_jenkins_sync_cycle`；`back-end/metrics/views.py:JenkinsTaskBulkSyncView` | 后端 pytest；worker 日志 5 轮 `failed=2` 后恢复为 0；错误日志仅含 binding id/错误类型 | 通过（自动+真实 watch） |
| `AC-S12-3.5` | F3 双 worker 并发一致 | `TC-S12-F3-007` | worker 与数据库唯一约束 | `back-end/metrics/views.py:create_or_get_daily_task_from_discovery` | `test_daily_discovery_reuses_task_created_by_another_worker_after_unique_conflict` 通过 | 部分通过（真实双进程未执行） |
| `AC-S12-4.1` | F4 active 模块 Job 与 binding 同名 | `TC-S12-F4-001/002/007/008` | Compose init；binding 命名契约 | `docker-compose.yml`；`jenkins/scripts/configure-local-mounted-jobs.groovy` | Jenkins 静态 54 passed；`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Jenkins真实初始化证据.txt` | 通过（自动+真实） |
| `AC-S12-4.2` | F4 新 Job 自带单个 02:00 TimerTrigger | `TC-S12-F4-003` | Jenkins init | `jenkins/scripts/configure-local-mounted-jobs.groovy` 的 `TimerTrigger`/`setTriggers` | 静态证据；真实两个分模块 Job 均 `timer_count=1/specs=0 2 * * *` | 通过（自动+真实配置） |
| `AC-S12-4.3` | F4 遗留共享 Job 保留并移除定时器 | `TC-S12-F4-004` | Jenkins init | `jenkins/scripts/configure-local-mounted-jobs.groovy` 的 `legacyDailyJob.setTriggers` | 静态证据；真实遗留 Job 仍存在且 `timer_count=0` | 通过（自动+真实配置） |
| `AC-S12-4.4` | F4 重复初始化幂等 | `TC-S12-F4-005/006/008` | Jenkins 重启/init | `jenkins/scripts/configure-local-mounted-jobs.groovy`；`docker-compose.yml` | 静态 54 passed；真实证据 `Jenkins final idempotency restart: PASS` | 通过（自动+真实） |
| `AC-S12-5.1` | F5 趋势以请求当天结束并包含真实历史 | `TC-S12-F5-001/005/008` | 7/30 天趋势、模块日期 | `back-end/metrics/views.py:select_daily_trend_rows,ModuleSnapshotTrendView` | 后端 pytest；Playwright 1 passed；趋势真实含 7/11 daily_full、7/12 module_rerun | 通过（自动+真实） |
| `AC-S12-5.2` | F5 无执行日不补造记录 | `TC-S12-F5-002` | 7/30 天趋势 | `back-end/metrics/views.py:ModuleSnapshotTrendView` | 后端趋势空窗口/真实历史过滤测试通过 | 通过（自动） |
| `AC-S12-5.3` | F5 真实 build 20/21 补同步 | `TC-S12-F5-003/006/007` | 受控 Django shell | `./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-历史补同步脚本.py`；正式同步服务 | `./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-历史补同步证据.txt`；真实趋势复核 | 通过（自动+真实） |
| `AC-S12-5.4` | F5 task 57/58 与 build 28/29 补同步 | `TC-S12-F5-004/007/008` | 单任务 sync、模块页、任务弹窗 | `back-end/metrics/views.py:sync_task_with_result,release_task_lock,JenkinsTaskSyncView` | task 58 sync=200；task57/58 均 test_failed、build=28/29、锁 released；Playwright 1 passed | 通过（自动+真实） |

## 2. 测试层级统计

| 验证层级 | 涉及 AC 数 | 说明 |
| --- | ---: | --- |
| `BE-PY` | 18 | API、同步服务、时间语义、状态机、唯一约束、趋势和受控补同步服务 |
| `WK-CMD` | 5 | F3 的 once/watch、参数、故障隔离、停止语义和并发 |
| `JD-STATIC` | 5 | F3 依赖边界，以及 F4 Compose/Groovy/Job 配置与幂等 |
| `REAL` | 10 | queue/build 恢复、实际时延、真实 Job 配置和 20/21/28/29 补同步 |
| `FE-PW` | 6 | 既有模块日期、执行时间、趋势、任务终态的前端可见结果 |

> 同一 AC 可由多个层级共同覆盖，统计不可相加为 23。

## 3. 当前验收状态统计

| 状态 | AC 数 | AC |
| --- | ---: | --- |
| 通过（自动或自动+真实） | 19 | `1.1`~`1.5`、`2.1`~`2.4`、`3.3`、`3.4`、`4.1`~`4.4`、`5.1`~`5.4` |
| 部分通过 / 待观察 | 4 | `1.6`、`3.1`、`3.2`、`3.5` |

> `3.2` 必须等待下一次真实 02:00 分模块 Daily 触发；`3.5` 必须等待真实双进程并发。现有静态、pytest 或空闲 watch 运行不能替代这两项真实观察。

## 4. 漂移检查清单（一致性自动门禁）

- [x] **无遗漏需求**：冻结需求 §4 的 23 个 AC 均至少映射一条测试用例。
- [x] **无凭空用例**：50 条测试用例均至少映射一个冻结 AC；补充异常/边界场景仍挂靠对应功能 AC。
- [x] **无遗漏界面**：涉及可见结果的 AC 已映射既有模块表格、趋势或任务弹窗；F4 等纯基础设施项明确为“无产品 UI”。
- [x] **无契约漂移**：仅使用冻结需求 §7 的 API/管理命令语义；历史补同步明确不新增长期 API。
- [x] **无未实现需求**：23 个 AC 均已有明确实现位置；4 个 AC 的缺口属于验证深度，不是缺少实现文件。
- [x] **无孤儿代码**：首轮独立 review subagent 已完成审查，发现项均已映射到实现、测试或文档修复。
- [ ] **全部达成**：当前 19 条通过、4 条部分通过；真实 02:00、新 build 自动处理与双进程等观察项仍保留。

## 5. 漂移处置记录

| 发现的漂移 | 类型 | 处置 | 状态 |
| --- | --- | --- | --- |
| 当前未发现冻结 AC、API/命令契约与测试设计之间的语义漂移。 | 测试设计 | 后续实现不得改变 queue 404、时间来源、失败重试、趋势窗口或历史补同步语义；如实现受阻须回到需求 §0 熔断。 | 已记录 |
| 真实双 worker 并发尚未执行。 | 真实验证缺口 | 保留 `AC-S12-3.5` 为部分通过；不得用模拟唯一键冲突冒充真实双进程证据。 | 待观察 |
| 新分模块 Daily Job 尚未经历下一次真实 02:00 调度。 | 时间窗口缺口 | 保留 `AC-S12-3.2` 为部分通过；真实触发后补充 build、worker discovery 和落库证据。 | 待观察 |
| worker watch 已连续运行，但当前没有新 active 任务/build 可供自动处理。 | 真实验证深度 | `AC-S12-3.1` 仅确认进程多轮稳定与自动测试，通过新 build 场景后再升级为完全通过。 | 待观察 |
