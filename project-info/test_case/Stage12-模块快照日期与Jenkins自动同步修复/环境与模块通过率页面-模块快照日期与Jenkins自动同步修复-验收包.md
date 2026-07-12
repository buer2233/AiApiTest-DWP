# 环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-验收包

> 本包已回填自动化与真实环境证据。结论严格区分“自动测试通过”“真实验证通过”和“真实验证待观察”；尚未发生的真实双进程并发、下一次 02:00 调度和新 build 自动处理不得写成已通过。

## 1. 需求概览

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-模块快照日期与Jenkins自动同步修复 |
| 需求分级 | M，不裁剪完整 loop |
| 关联模块 | `back-end` / `jenkins` / `docker` / `front-end`（既有字段刷新验收） |
| 需求冻结日期 | 2026-07-12 |
| 本包生成 / 证据回填日期 | 2026-07-12 |
| 当前结论 | 19 个 AC 通过，4 个 AC 部分通过；尚不能签署“全部 AC 达成” |
| 冻结需求 | `../../demand/Stage12-模块快照日期与Jenkins自动同步修复/环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-需求说明.md` |
| 功能测试用例 | `./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-功能测试用例.md` |
| 可追溯矩阵 | `./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-可追溯矩阵.md` |

## 2. 逐条验收结论

| AC 编号 | 验收点 | 对应用例 | 当前结论 | 证据位置 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `AC-S12-1.1` | queueId 精确恢复并同次读取 artifact、返回 200 | `TC-S12-F1-001/009/010` | 通过（自动+真实） | 后端 209 passed；真实接口验收证据；§3.4 | task 58 sync 返回 200，最终 test_failed |
| `AC-S12-1.2` | queueId 不可用时按 RUN_ID 精确恢复 | `TC-S12-F1-002` | 通过（自动） | `./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-后端pytest覆盖率证据.txt` | 精确 run_key 分支已测 |
| `AC-S12-1.3` | 并发 build 不错配，歧义时不猜测 | `TC-S12-F1-003/007` | 通过（自动） | Jenkins service/API 定向回归；RTM 实现位置 | queueId/RUN_ID 双分支、单任务 409、状态/锁保持和批量隔离均有直接负向用例 |
| `AC-S12-1.4` | queue 404 暂无 build 时保持 queued/200 | `TC-S12-F1-004/008` | 通过（自动） | 后端 pytest 证据 | pending 与超时规则均有回归 |
| `AC-S12-1.5` | Jenkins 真不可达/认证失败才返回 503 | `TC-S12-F1-005/009` | 通过（自动） | 后端 pytest 证据 | queue 404 与服务不可用已分流 |
| `AC-S12-1.6` | 新任务前先恢复旧锁任务真实 build | `TC-S12-F1-006` | 部分通过 | 后端组件测试；§3.4 task 57/58 与锁数据 | 恢复与锁释放已验证；恢复后紧接新触发的组合场景待观察 |
| `AC-S12-2.1` | 延迟同步仍按 Jenkins 实际完成日落库 | `TC-S12-F2-001/009` | 通过（自动+真实） | 后端 pytest；桌面/移动截图；§3.4 | 模块 1/2 均显示 2026/7/12 |
| `AC-S12-2.2` | 快照/历史/任务/TestRun 完成时间一致 | `TC-S12-F2-002/007/008/010` | 通过（自动+真实） | 后端 pytest；Playwright 1 passed；§3.4 | 页面执行时长取 summary，不取 Jenkins 总时长 |
| `AC-S12-2.3` | 失败重试不改模块日期和执行时间 | `TC-S12-F2-003` | 通过（自动） | 后端 pytest 证据 | 真实失败重试专项未重复执行 |
| `AC-S12-2.4` | 时间字段非法时安全兜底并告警 | `TC-S12-F2-004/005/006` | 通过（自动） | 后端 pytest 证据 | duration=0、负数、非法和溢出均覆盖 |
| `AC-S12-3.1` | worker 自动同步模块重试并刷新可见数据 | `TC-S12-F3-001/002/003/010/014` | 部分通过 | 后端 pytest；worker 真实运行证据；Playwright 证据 | watch 已多轮稳定运行，但未在本轮观察到新 build 被自动处理 |
| `AC-S12-3.2` | worker 发现每模块 Daily build | `TC-S12-F3-004` | 部分通过 | 后端 pytest；Jenkins 真实初始化证据 | Job 与 cron 已就绪；下一次真实 02:00 触发待观察 |
| `AC-S12-3.3` | 重复发现同 build 不重复写业务数据 | `TC-S12-F1-010/F2-010/F3-005/F3-013` | 通过（自动） | 后端 pytest 证据 | 两轮发现、终态 skip、唯一冲突复用均通过 |
| `AC-S12-3.4` | 单 Job 失败隔离，恢复后可补同步 | `TC-S12-F3-006/008/009/011/012` | 通过（自动+真实 watch） | 后端 pytest；worker stdout/stderr 日志 | 5 轮 failed=2 后恢复为 failed=0，错误输出已脱敏 |
| `AC-S12-3.5` | 双 worker 并发最终一致 | `TC-S12-F3-007` | 部分通过 | 后端并发冲突 pytest | 真实双进程未执行，不得标完全通过 |
| `AC-S12-4.1` | active 模块均有与 binding 同名 Daily Job | `TC-S12-F4-001/002/007/008` | 通过（自动+真实） | Jenkins 54 passed；Jenkins 真实初始化证据 | 两个分模块 Job 均存在 |
| `AC-S12-4.2` | 新 Job 创建即有单个 02:00 TimerTrigger | `TC-S12-F4-003` | 通过（自动+真实配置） | Jenkins 静态/真实初始化证据 | 两个 Job 均 timer_count=1、spec=0 2 * * * |
| `AC-S12-4.3` | 遗留共享 Job 保留历史、移除 TimerTrigger | `TC-S12-F4-004` | 通过（自动+真实配置） | Jenkins 静态/真实初始化证据 | 遗留 Job 仍存在且 timer_count=0 |
| `AC-S12-4.4` | 多次 init 不重复 Job/属性/触发器 | `TC-S12-F4-005/006/008` | 通过（自动+真实） | Jenkins 54 passed；真实初始化证据 | 最终幂等重启 PASS |
| `AC-S12-5.1` | 7/30 天窗口以请求当天结束并含真实历史 | `TC-S12-F5-001/005/008` | 通过（自动+真实） | 后端 pytest；Playwright 1 passed；桌面截图；§3.4 | 真实含 7/11 daily_full、7/12 module_rerun |
| `AC-S12-5.2` | 无真实执行日不生成 0 或复制记录 | `TC-S12-F5-002` | 通过（自动） | 后端趋势 pytest | Playwright 未单独构造空洞日期 |
| `AC-S12-5.3` | 真实 build 20/21 生成 daily_full 历史 | `TC-S12-F5-003/006/007` | 通过（自动+真实） | 历史补同步脚本/证据；§3.4 | artifact 模块归属先校验后同步 |
| `AC-S12-5.4` | task 57/58 对应 build 28/29 终结并释放锁 | `TC-S12-F5-004/007/008` | 通过（自动+真实） | API 访问日志；Playwright；§3.4 | 两任务均 test_failed，锁均 released |

## 3. 测试证据索引

### 3.1 后端 pytest / pytest-django

- 完整证据：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-后端pytest覆盖率证据.txt`。
- 结果：`209 passed`，总覆盖率 `91%`。
- Stage12 核心模块覆盖率：`metrics/jenkins_service.py 91%`、`metrics/jenkins_sync.py 93%`、`sync_jenkins_results.py 96%`。
- HTML 覆盖率：`../../../back-end/tests/evidence/htmlcov/index.html`。
- 覆盖内容：queueId/RUN_ID 恢复、queue pending、真实时间与 fallback、任务/锁状态、Daily discovery、重复幂等、唯一键冲突复用、单任务/单 Job 故障隔离、趋势当天窗口、权限与错误契约。
- 证据强度限制：真实双进程并发未执行；`AC-S12-3.5` 不能仅凭模拟 `IntegrityError` 标完全通过。

### 3.2 Jenkins / Docker 静态测试

- 静态证据：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Jenkins静态测试证据.txt`，结果 `54 passed in 1.88s`。
- 真实初始化证据：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Jenkins真实初始化证据.txt`。
- Compose 挂载：`docker-compose.yml` 将 `configure-local-mounted-jobs.groovy` 只读挂载到 `init.groovy.d`。
- 真实 Job：两个分模块 Daily Job 均存在，均只有一个 `0 2 * * *` TimerTrigger；遗留共享 Job 保留且 timer_count=0。
- 幂等：真实重启证据为 `Jenkins final idempotency restart: PASS`。
- 证据强度限制：Job 配置已通过，但下一次真实 02:00 调度尚未发生，`AC-S12-3.2` 保持部分通过。

### 3.3 worker 管理命令

- 自动测试：后端 209 passed 包含 `--once`、`--watch`、非法 interval 回退、interval 非 watch、SIGTERM/KeyboardInterrupt 停止和结构化计数。
- 真实运行证据：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-worker真实运行证据.txt`，记录成功轮询与 Jenkins 重启期间的故障隔离。
- 故障恢复：日志包含 5 轮 `failed=2`，Jenkins 恢复后继续输出 `failed=0`，证明 watch 未因单 Job 失败退出。
- 当前限制：运行窗口内没有新 active task 或新 Daily build，不能据此声称已真实验证“新 build 自动落库”和同步时延；运行日志属于本机验收产物，不作为业务代码提交。

### 3.4 真实补同步与数据对比

- 执行脚本：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-历史补同步脚本.py`；脚本先校验 module2 node id 前缀，再复用 `fetch_jenkins_task_result` 和 `sync_task_with_result`，未使用裸 SQL。
- build 20/21 证据：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-历史补同步证据.txt`；分别生成 task 59/60，状态均为 test_failed，完成时间来自 Jenkins。
- task 58 API：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-真实接口验收证据.json` 记录 `POST /api/v1/jenkins-tasks/58/sync` 返回 200。
- 只读数据库复核：task 57/58 分别绑定 build 28/29，均为 test_failed；两个执行锁均为 released，release_reason 为 `task test_failed`。
- 模块快照：module1 `completed_at=2026-07-12T07:08:42.402000+00:00`、duration 7.25；module2 `completed_at=2026-07-12T07:08:12.048000+00:00`、duration 7.41。
- module2 历史：7/11 存在 daily_full；7/12 同时存在 daily_full 与 module_rerun，趋势按既有优选规则展示 module_rerun。
- 幂等：自动测试已通过；真实脚本包含终态 `SKIP` 防重逻辑，但本轮未单独归档第二次执行输出。
- 所有记录均未写入真实 token、Cookie、Authorization 或含敏感查询参数的 URL。

### 3.5 Playwright / 真实接口

- 用例：`../../../front-end/e2e/stage12-snapshot-date-jenkins-sync-real-acceptance.spec.ts`。
- 运行证据：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Playwright运行证据.txt`，Chromium `1 passed (12.8s)`。
- 桌面截图：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Playwright验收-桌面.png`，30 天趋势已延伸至 7/12。
- 移动截图：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-Playwright验收-移动端.png`，模块 1/2 均显示 2026/7/12 与真实执行时长，无横向溢出。
- 真实断言：模块列表 200、30 天趋势 200；趋势包含 7/11 daily_full 与 7/12 module_rerun；任务弹窗中 task 57 为测试失败。
- task 58 的 200/test_failed 由后端访问日志和数据库复核补充验证。
- 前端单测：`8 files / 19 tests passed`，包含 Stage12 Playwright 入口不得写死本机端口的静态回归。
- 前端构建：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-前端构建证据.txt`，`vue-tsc --noEmit && vite build` 成功；仅保留既有 Rollup PURE 与 chunk size warning。

### 3.6 独立对抗审查

- 独立 review subagent：首轮已执行，结论为 0 个 Critical、6 个 Important、3 个 Minor。
- Critical/Important 发现及修复闭环：全部完成；新增覆盖旧锁恢复顺序、Jenkins 不可用保锁、超时 queue_pending、畸形 JSON/严格 build number、worker 配置/SIGTERM、YAML cron 切换门禁和歧义 build 错误契约。
- 修复后复核：主线程完成定向、全量和真实环境集成验证；独立复审代理因当前会话未提供仓库读取工具，未将其输出冒充复审结论。

## 4. 一致性报告（RTM 摘要）

- 需求 AC 总数：23。
- 已映射 AC：23。
- 测试用例总数：50。
- 当前测试设计漂移：未发现。
- 实现位置完整性：23/23 已补全。
- 实际验收状态：19 条通过，4 条部分通过。
- 部分通过：`AC-S12-1.6`、`AC-S12-3.1`、`AC-S12-3.2`、`AC-S12-3.5`。
- 独立对抗审查：首轮完成且所有发现已闭环；保留 4 项真实观察缺口，不将其写成全部 AC 达成。
- RTM：`./环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-可追溯矩阵.md`。

## 5. 实现摘要

- queue/build 恢复与真实时间：`back-end/metrics/jenkins_service.py` 的 `_recover_build_from_expired_queue`、`_build_times`、`fetch_jenkins_task_result`。
- 同步状态机、快照/历史与锁：`back-end/metrics/views.py` 的 `refresh_module_execution_state`、`apply_module_summary`、`sync_task_with_result`、`release_task_lock`、`JenkinsTaskSyncView`、`JenkinsTaskBulkSyncView`、`ModuleSnapshotTrendView`。
- worker：`back-end/metrics/jenkins_sync.py:run_jenkins_sync_cycle` 与 `back-end/metrics/management/commands/sync_jenkins_results.py:Command`。
- Jenkins/Docker：`jenkins/scripts/configure-local-mounted-jobs.groovy` 与 `docker-compose.yml`；`.env.example` 增补 worker 间隔和 Daily Job 前缀说明。
- 前端：未修改 Vue 产品源码；新增 `front-end/e2e/stage12-snapshot-date-jenkins-sync-real-acceptance.spec.ts` 验证既有 DOM。
- 数据修复：Stage12 历史补同步脚本复用正式服务，不新增 API、数据库表或迁移。
- 文档：根 README、Jenkins README、Docker 部署文档与 Swagger 测试已同步到实现阶段；最终一致性由独立审查确认。
- 独立对抗审查结论：首轮 `0 Critical / 6 Important / 3 Minor`，所有发现已完成修复与集成验证。

## 6. 容器化兼容验收

| 检查项 | 验收要求 | 当前结论 | 证据 |
| --- | --- | --- | --- |
| 配置入口 | 可变配置来自根 `.env`/私有 CI 变量；通用变量同步 `.env.example` | 通过（静态） | Jenkins/Docker 54 passed；`.env.example` |
| Jenkins init | Compose 使用仓库相对路径只读挂载脚本 | 通过（自动+真实） | Jenkins 静态与真实初始化证据 |
| 服务寻址 | worker 通过配置和 Compose 服务名访问 MySQL/Jenkins，不写死宿主机端口 | 通过（静态） | `docker-compose.yml`、静态测试 |
| 文件路径 | 不绑定个人本机绝对路径；Job 名不含宿主机路径 | 通过（静态） | 静态测试与真实 Job 名 |
| 凭据与运行产物 | 真实 `.env`、数据库数据、Jenkins home、日志和报告不打包进镜像或业务提交 | 通过（静态） | `.gitignore` 与 Docker 静态测试；worker 日志只用于本机验收 |
| 未来 worker service | 可复用 backend 镜像运行 `python manage.py sync_jenkins_results --watch` | 通过（命令可迁移） | 管理命令、README、`docker/DEPLOYMENT.md`；本阶段 backend 尚未整体容器化 |

## 7. 待主人确认项（熔断遗留）

当前冻结需求 §0 的 6 项裁决均已闭环，测试设计未发现需要新增裁决的关键歧义。若实现阶段无法满足以下任一冻结语义，必须暂停并回到需求 §0 上报，不得自行变更：

- queue 404 的精确恢复优先级和禁止选最新 build；
- Jenkins 实际完成时间与失败重试时间规则；
- 独立 management command worker；
- 分模块 Daily Job 与遗留共享 Job 的 TimerTrigger 处理；
- 只补同步可验证的真实 artifact。

## 8. 已知限制 / 后续项

- `AC-S12-3.5` 尚未执行两个真实 worker 进程并发发现同一 build；当前只有唯一键冲突自动测试。
- `AC-S12-3.2` 的新分模块 Job 尚未经历下一次真实 02:00 调度，不能用 timer 配置存在替代实际触发证据。
- `AC-S12-3.1` 的 watch 已运行 200 轮并经历 Jenkins 暂时失败/恢复，但运行窗口没有新 active task 或新 Daily build，因此真实自动落库时延仍待观察。
- `AC-S12-1.6` 缺少“旧任务恢复终结后立即创建新任务”的单条组合证据；恢复、终结、锁释放组件与真实数据已分别验证。
- 历史补同步的自动幂等测试已通过，真实第二次执行输出未单独归档。
- 首轮独立对抗审查发现已全部闭环；修复后独立复审代理受工具限制，验收包已如实记录，未伪造复审结论。
- 前端仅做受影响回归，不新增 Vue 产品源码；UI 范围继续以 Stage12 映射文档为准。

---

## 验收结论（主人签字）

- [ ] 全部 23 个 AC 达成（当前 18 通过、5 部分通过）
- [x] 后端 pytest、覆盖率和 RED/GREEN 证据充分
- [x] Jenkins/Docker 静态与真实 Job 配置证据充分
- [ ] worker once/watch 与真实新 build 自动落库时延证据充分
- [ ] build 20/21/28/29 真实补同步及真实重复执行幂等证据充分
- [x] Playwright/真实接口证据充分
- [x] RTM 实现位置完整且无需求漂移
- [ ] 独立对抗审查无未闭环 Critical/Important

**验收人（主人）**：`__________`　**日期**：`__________`　**结论**：`通过 / 打回（附原因）`
