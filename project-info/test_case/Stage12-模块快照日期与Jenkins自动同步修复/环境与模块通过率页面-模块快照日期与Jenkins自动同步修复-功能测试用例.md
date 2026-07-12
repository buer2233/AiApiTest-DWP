# 环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-功能测试用例

## 1. 文档信息

| 项 | 内容 |
| --- | --- |
| 需求来源 | `../../demand/Stage12-模块快照日期与Jenkins自动同步修复/环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-需求说明.md` |
| 需求状态 | 已冻结 |
| 需求分级 | M，不裁剪完整 loop |
| 测试设计日期 | 2026-07-12 |
| 覆盖范围 | F1 queue 精确恢复、F2 Jenkins 实际时间、F3 自动同步 worker、F4 Daily Job 初始化、F5 趋势窗口与真实补同步 |
| 不在本阶段执行 | 业务代码实现、自动化测试运行、真实补同步和真实凭据配置；对应证据均在验收包中标记待补 |

## 2. 测试层级与证据约定

| 层级代码 | 验证方式 | 主要验证对象 | 阶段证据 |
| --- | --- | --- | --- |
| `BE-PY` | pytest / pytest-django，必要时 mock Jenkins HTTP | DRF API、同步服务、时间换算、状态机、事务和幂等约束 | pytest 输出、失败转绿记录、覆盖率 |
| `WK-CMD` | Django management command 测试与受控进程测试 | `--once`、`--watch`、间隔、退出码、故障隔离、结构化脱敏输出 | 命令测试输出、单轮/watch 运行日志 |
| `JD-STATIC` | Jenkins/Docker/Groovy/Compose 静态测试 | init 脚本挂载、Job 命名、TimerTrigger、幂等和配置可迁移性 | 静态测试输出、`compose config` 结果 |
| `REAL` | 本地 Compose Jenkins + Docker MySQL + 真实 artifact 的受控验收 | queue 恢复、Daily discovery、worker 时延、build 20/21/28/29 补同步 | 脱敏命令输出、前后数据对比、Jenkins Job 配置证据 |
| `FE-PW` | Playwright 使用真实后端接口 | 既有模块表格、趋势图和任务弹窗的可见结果；不新增 DOM | Playwright 结果和关键页面截图 |

所有自动化数据使用隔离环境、占位符 Job 名和脱敏账号。真实验收只从根 `.env` 或 CI/Jenkins 私有变量读取凭据，不在命令、日志或本文档中展开。

## 3. 通用前置条件与测试数据

- 已存在管理人员、普通成员两个测试身份；worker 不使用用户 Cookie。
- 准备 active 模块 `module-1`、`module-2` 及与之同名契约的 Daily binding；Job 名使用 `${JENKINS_DAILY_FULL_JOB_PREFIX}<package>` 形式。
- 准备 queued、running、canceling、success、test_failed、failed、canceled 状态任务以及关联 `TestRun`、执行锁、模块快照和历史记录。
- mock build 必须显式给出 `queueId`、`RUN_ID`、`timestamp`、`duration`、`building`、`result` 和 summary；未声明字段不得由测试替实现补齐。
- 真实补同步对象限定为冻结需求指定的 Daily build 20/21 和模块重试 build 28/29；执行前必须核验 artifact 的模块 node id 路径。
- 日期断言使用项目时区；测试时冻结请求当天，避免依赖执行机器当前日期。

## 4. F1 queue 过期后的 build 精确恢复

| 编号 | 类型 / 优先级 | 关联 AC | 层级 | 前置条件与测试数据 | 操作步骤 | 预期结果与后置状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S12-F1-001` | 正常 / P0 | `AC-S12-1.1` | `BE-PY`、`REAL` | 管理员；任务为 queued、无 `build_number`；queue API 返回 404；同 Job 近期 build 中仅一条 `queueId` 等于本地 `queue_id`，artifact 完整 | 1. POST 单任务 sync。<br>2. 记录 Jenkins 调用顺序。<br>3. 查询任务、TestRun、锁和模块结果。 | HTTP 200；同次同步先保存正确 build number/URL/started_at，再读取 build 与 artifact 并进入真实终态；任务与 TestRun 一致；终态释放锁；不要求再次点击同步。 |
| `TC-S12-F1-002` | 正常 / P0 | `AC-S12-1.2` | `BE-PY` | queue 404；候选 build 无可用 `queueId`，仅一条参数 `RUN_ID` 精确等于 `TestRun.run_key` | 调用单任务 sync，并检查候选 build 参数解析和保存结果。 | 恢复该 build，不选择其它 RUN_ID 或最新 build；在同次请求继续同步 artifact，HTTP 200。 |
| `TC-S12-F1-003` | 并发隔离 / P0 | `AC-S12-1.3` | `BE-PY` | 同 Job 按时间倒序存在 3 条并发 build；最新一条属于其它任务，中间一条 queueId 匹配，最旧一条 RUN_ID 相似但不相等 | 同步目标任务，分别验证 queueId 优先和精确字符串比较。 | 只绑定 queueId 精确匹配 build；不得因排序选择最新 build；其它任务、模块快照和锁均不受影响。 |
| `TC-S12-F1-004` | 状态保持 / P0 | `AC-S12-1.4` | `BE-PY` | queue 404；有限近期 build 暂无精确匹配；任务未超过既有 2 小时超时阈值 | POST 单任务 sync 两次并检查响应和状态。 | 两次均 HTTP 200，任务保持 queued，仅更新允许的同步时间/诊断信息；不返回 503、不释放锁、不创建历史。 |
| `TC-S12-F1-005` | 异常 / P0 | `AC-S12-1.5` | `BE-PY` | 分别模拟 Jenkins 连接失败、认证失败、请求超时和 5xx；记录调用前任务完整状态 | 对每类异常调用单任务 sync。 | HTTP 503，业务码 `jenkins_unavailable`；原任务状态、build_number、模块指标和锁保持不变；响应与日志不含凭据或 Authorization。 |
| `TC-S12-F1-006` | 状态迁移 / P0 | `AC-S12-1.6` | `BE-PY` | 模块旧锁指向 queued 旧任务；旧 queue 已 404，但存在唯一真实终态 build；用户准备触发新模块任务 | 触发新任务，使服务先刷新旧锁关联任务；检查旧任务同步及新触发结果。 | 先恢复并同步旧 build 到真实终态、释放旧锁；不得直接把旧任务标 failed；随后按既有互斥规则决定是否创建新任务，且无双 active 锁。 |
| `TC-S12-F1-007` | 异常歧义 / P0 | `AC-S12-1.3` | `BE-PY` | 构造两个候选 build 的精确条件都匹配同一 queueId 或 RUN_ID | 分别调用单任务 sync 和批量 sync，捕获响应、错误摘要和数据库差异。 | 不猜测、不更新 build_number、任务/TestRun 状态、模块数据或锁；记录可诊断且脱敏的歧义错误；单任务返回 409 `jenkins_build_ambiguous`；批量隔离该 build 并返回 200 计数，不得误报 `jenkins_unavailable`。 |
| `TC-S12-F1-008` | 边界 / P1 | `AC-S12-1.4` | `BE-PY` | queued 任务同时无 queue_id 和 run_key；分别构造未超时、刚好 2 小时、超过 2 小时 | 冻结时间后逐组同步。 | 未超时不猜测 build并保持 queued；达到既有超时判定边界时按仓库既有规则处理；超时后进入 failed、记录原因并释放锁，且不创建历史。 |
| `TC-S12-F1-009` | 权限与参数 / P0 | `AC-S12-1.1`、`AC-S12-1.5` | `BE-PY` | 管理员、普通成员、未登录身份；存在任务 ID 和不存在的正整数任务 ID | 分别调用 `POST /api/v1/jenkins-tasks/{task_id}/sync`，body 使用空对象。 | 管理员有效任务按同步语义返回 200；普通成员返回 403 `admin_required`；未登录沿用认证错误；不存在任务返回 404 `jenkins_task_not_found`；拒绝路径不调用 Jenkins。 |
| `TC-S12-F1-010` | 幂等回归 / P0 | `AC-S12-1.1`、`AC-S12-3.3` | `BE-PY` | 已终态任务已应用完整 summary，并存在唯一当前用例与 source_run 历史 | 连续调用单任务 sync 3 次，统计 Jenkins artifact 读取与各表行数。 | 仅允许刷新 `last_synced_at` 等既有字段；不重复应用 summary，不新增 JenkinsTask、TestRun、当前用例或历史；唯一键无冲突。 |

## 5. F2 Jenkins 实际完成时间与模块快照更新

| 编号 | 类型 / 优先级 | 关联 AC | 层级 | 前置条件与测试数据 | 操作步骤 | 预期结果与后置状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S12-F2-001` | 正常 / P0 | `AC-S12-2.1` | `BE-PY` | build 在项目时区 7 月 12 日完成，平台时间冻结为 7 月 13 日；summary 完整 | 同步 Daily 或模块重试并查询任务、快照、历史。 | JenkinsTask/TestRun `finished_at` 使用 7 月 12 日实际完成时间；ModuleSnapshot 日期和 ModuleRunHistory `run_date` 均为 7 月 12 日，不使用 7 月 13 日同步日。 |
| `TC-S12-F2-002` | 数据一致性 / P0 | `AC-S12-2.2` | `BE-PY` | 分别准备 Daily、模块重试成功 summary；build 有合法毫秒 `timestamp`、`duration` | 同步两类任务并跨表比较完成时间。 | `started_at=timestamp`；JenkinsTask、TestRun、ModuleSnapshot、ModuleRunHistory 的相关 `completed_at/finished_at` 均等于 `timestamp + duration` 的带时区值。 |
| `TC-S12-F2-003` | 规则回归 / P0 | `AC-S12-2.3` | `BE-PY`、`FE-PW` | 失败重试任务完成；同步前记录模块日期、`duration_seconds`、当前用例和趋势 | 同步失败重试；刷新模块列表和趋势。 | 任务按真实结果终结，但模块日期和执行时间保持原值；模块趋势和当前模块指标不被失败重试覆盖；页面显示值不变化。 |
| `TC-S12-F2-004` | 异常兜底 / P0 | `AC-S12-2.4` | `BE-PY` | 分别缺失 `timestamp`、缺失 `duration`、字段为 null 或非法字符串；冻结平台同步时刻 | 同步每组 build，捕获日志并查询落库时间。 | 使用冻结的平台同步时刻兜底，生成合法带时区时间；记录不含敏感信息的 warning；任务仍按 artifact 真实结果处理。 |
| `TC-S12-F2-005` | 边界 / P1 | `AC-S12-2.4` | `BE-PY` | 合法 `duration=0`，`timestamp` 为有效毫秒值 | 同步 build。 | `started_at` 与 `finished_at` 相等且合法；不得把 0 当缺失或错误；历史日期按该时间计算。 |
| `TC-S12-F2-006` | 边界异常 / P0 | `AC-S12-2.4` | `BE-PY` | duration 分别为负数、非数字、超出可表示范围；timestamp 分别为负数或溢出值 | 逐组同步并监控异常与数据库写入。 | 不生成倒退或溢出的完成时间，不抛出未处理异常；按冻结语义使用平台时刻兜底并记录脱敏警告。 |
| `TC-S12-F2-007` | 指标语义 / P0 | `AC-S12-2.2` | `BE-PY`、`FE-PW` | Jenkins build 总 duration 为 600 秒，summary 模块 `duration_seconds` 为 37.5 秒 | 同步后查询 API 并刷新模块列表。 | 完成时间使用 build timestamp+duration；模块“执行时间”保持 summary 的 37.5 秒，不得改成 600 秒；页面显示与接口一致。 |
| `TC-S12-F2-008` | 异常 / P0 | `AC-S12-2.2` | `BE-PY` | 分别构造 artifact 404/归档失败、summary 缺少关键统计、当前用例契约字段缺失；同步前保存模块指标和用例快照 | 逐组同步终态 build。 | 保留原模块指标和当前用例；任务保存明确、脱敏的错误摘要；不得写入半套快照或历史，也不得把报告归档失败误记为成功同步。 |
| `TC-S12-F2-009` | 时区边界 / P0 | `AC-S12-2.1` | `BE-PY` | 构造 UTC 日期与项目本地日期跨日的两个完成时间 | 同步并查询趋势。 | 数据库存带时区 datetime；`run_date` 按项目本地日期转换；趋势日期与模块表格本地展示一致。 |
| `TC-S12-F2-010` | 幂等 / P0 | `AC-S12-2.2`、`AC-S12-3.3` | `BE-PY` | 同一 source_run 已存在历史，第二次 summary 的事实字段相同 | 重复应用同一 summary 并统计历史、当前用例和归档记录。 | ModuleRunHistory 通过既有唯一键 update_or_create，保持一条 source_run 记录；当前用例不重复；完成时间保持 Jenkins 真实值。 |

## 6. F3 轻量 Jenkins 自动同步 worker

| 编号 | 类型 / 优先级 | 关联 AC | 层级 | 前置条件与测试数据 | 操作步骤 | 预期结果与后置状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S12-F3-001` | 正常 / P0 | `AC-S12-3.1` | `WK-CMD` | 存在 queued/running/canceling 任务和 active Daily binding；canceling 对应 Jenkins ABORTED | 分别执行不带模式参数及 `--once`；记录处理顺序、状态变化和计数。 | 两者都只执行一轮并正常退出；先同步 active 平台任务，再发现 Daily build；canceling 进入 canceled、释放锁且不更新模块指标；输出 discovered/synced/recovered/failed/skipped 等结构化计数。 |
| `TC-S12-F3-002` | 正常 / P0 | `AC-S12-3.1` | `WK-CMD` | 设置安全的轮询间隔；首轮无新 build，次轮出现终态 build | 运行 `--watch --interval 10`，等待至少两轮后终止。 | 每轮按 10 秒附近间隔执行且不重叠；次轮自动同步新 build；终止后进程正常退出。 |
| `TC-S12-F3-003` | 自动闭环 / P0 | `AC-S12-3.1` | `WK-CMD`、`FE-PW` | 模块重试 build 已完成；summary 同时含失败、通过、跳过和按既有协议不展示的用例；浏览器未打开任务弹窗；记录同步前任务、快照、当前用例、趋势 | 1. worker 运行前仅刷新模块列表 GET，确认无 Jenkins 调用或数据库写副作用。<br>2. 执行 worker 下一轮。<br>3. 普通成员打开模块页、当前用例和趋势。 | 无人工 sync 即更新任务终态、快照、当前用例和趋势；失败/通过/跳过/不展示的显示和统计影响沿用既有协议；普通成员看见新日期/执行时间/趋势；DOM 不出现 worker 说明或新按钮。 |
| `TC-S12-F3-004` | Daily 发现 / P0 | `AC-S12-3.2` | `WK-CMD`、`BE-PY` | active 分模块 Daily Job 02:00 build 已完成，数据库无对应 task | 执行单轮 worker并查询相关表。 | 创建或更新唯一 `daily_full` JenkinsTask/TestRun，读取 artifact，刷新模块快照、当前用例和趋势；job_full_name/build_number 与 Jenkins 一致。 |
| `TC-S12-F3-005` | 多轮幂等 / P0 | `AC-S12-3.3` | `WK-CMD`、`BE-PY` | 同一终态 Daily build 可在最近 50 条列表中连续出现 | 连续执行 3 轮 worker，统计任务、运行、历史和 artifact 请求次数。 | 数据库仅一条对应 JenkinsTask/TestRun/source_run 历史；已终态且已落库 build 被 skipped，不重复读取 artifact。 |
| `TC-S12-F3-006` | 故障隔离与批量 API / P0 | `AC-S12-3.4` | `BE-PY`、`WK-CMD` | 3 个 active Job：A 正常、B 暂时不可达、C 正常；下一轮 B 恢复；另备精确匹配歧义 build 和普通成员身份 | 1. 管理员调用 `POST /api/v1/jenkins-tasks/sync` 并执行一轮 worker。<br>2. 恢复 B 后再执行一轮。<br>3. 构造全部配置 Job 不可达。<br>4. 构造全部 build 均为精确匹配歧义。<br>5. 普通成员调用批量 sync。 | 单个 B 失败时 API/worker 均记录脱敏错误并继续 A/C，API 返回 200 及既有计数；恢复后补同步 B且 A/C 不重复；全部 Job 真不可达时 API 才返回 503；全部 build 匹配歧义时记录任务诊断并返回 200，不误报 `jenkins_unavailable`；普通成员返回 403 且不调用 Jenkins。 |
| `TC-S12-F3-007` | 并发 / P0 | `AC-S12-3.5` | `BE-PY`、`WK-CMD` | 两个 worker 同时发现同一 Job/build 或同步同一 active task | 使用并发屏障同时进入创建/应用事务，待两进程结束后核对数据库。 | 可发生受控唯一键竞争或重复外部读取，但最终仅一套任务、运行、当前用例和历史；任务终态一致，无悬挂锁。 |
| `TC-S12-F3-008` | 依赖异常 / P0 | `AC-S12-3.4` | `WK-CMD` | 模拟数据库连接在轮次开始或事务提交时失败 | 执行 `--once`。 | 命令非零退出或明确标记当前轮失败；异常不被静默吞掉；不输出凭据；不得声称 synced 成功。 |
| `TC-S12-F3-009` | 参数边界 / P1 | `AC-S12-3.4` | `WK-CMD` | 环境变量轮询间隔分别为空、0、负数、非整数和超大非法值 | 启动 watch 或解析配置。 | 非正整数不进入忙循环；按冻结需求回退安全默认值并输出明确错误；合法正整数被采用。 |
| `TC-S12-F3-010` | 命令契约 / P0 | `AC-S12-3.1` | `WK-CMD`、`JD-STATIC` | 无业务任务即可 | 分别执行 `--once --watch`、只带 `--interval`、无参数和帮助命令；静态扫描 worker 依赖和启动说明。 | once/watch 互斥组合被参数解析拒绝；`--interval` 仅 watch 使用；无参数默认单轮；帮助文本包含冻结的三种调用方式且不暴露配置值；实现不引入 Celery、Redis 或 APScheduler。 |
| `TC-S12-F3-011` | 停止语义 / P1 | `AC-S12-3.4` | `WK-CMD`、`REAL` | watch 正在空闲等待或刚完成一轮 | 分别发送 Ctrl+C 和可用环境下的 SIGTERM，随后检查进程和数据库锁。 | 正常、可诊断地退出；不启动下一轮，不遗留 management command 自身数据库锁或半提交事务。 |
| `TC-S12-F3-012` | 安全可观测 / P0 | `AC-S12-3.4` | `WK-CMD` | Jenkins 配置中存在占位符用户名、token、带查询参数 URL；Job/任务各一项失败 | 执行一轮并扫描 stdout/stderr。 | 输出结构化计数、任务 id、脱敏 Job 标识和错误类型；不得出现用户名、token、Cookie、Authorization header、完整 artifact 或敏感 URL 查询参数。 |
| `TC-S12-F3-013` | 性能回归 / P1 | `AC-S12-3.3` | `WK-CMD` | 每个 active binding 最近列表有 50 条 build，其中 49 条已终态落库，1 条新 build | 执行一轮并统计 Jenkins 请求。 | 只对新 build或未终态任务读取详情/artifact；已终态已落库项计入 skipped；不全量重复应用 50 条 artifact。 |
| `TC-S12-F3-014` | 真实时延 / P0 | `AC-S12-3.1` | `REAL`、`FE-PW` | 本地 Compose Jenkins、Docker MySQL、worker 正常运行；记录 build 完成时刻和轮询间隔 | 完成一个真实模块重试，等待 worker 落库，再通过真实 API/UI查看。 | 落库完成时间不超过“配置轮询间隔 + 单次同步耗时”；页面无需打开任务弹窗即可看到终态、快照、当前用例和趋势更新；证据记录脱敏时间点。 |

## 7. F4 Daily Job 与 binding 自动一致

| 编号 | 类型 / 优先级 | 关联 AC | 层级 | 前置条件与测试数据 | 操作步骤 | 预期结果与后置状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S12-F4-001` | 容器化 / P0 | `AC-S12-4.1` | `JD-STATIC` | 使用仓库 Compose 配置，不加载真实 `.env` 内容到输出 | 渲染 Compose 配置并检查 Jenkins volumes。 | `configure-local-mounted-jobs.groovy` 通过仓库相对路径挂载到正确 init 目录且为只读；无宿主机硬编码绝对路径、固定凭据或打包数据卷。 |
| `TC-S12-F4-002` | 正常 / P0 | `AC-S12-4.1` | `JD-STATIC`、`REAL` | package YAML 有多个 active 模块；后端 binding 同步已运行 | 启动 Jenkins init，列出每模块 Job 与 binding 的 `job_full_name`。 | 每个 active 模块均有且仅有一个同名 Daily Job；命名同时遵守 YAML package 和 `JENKINS_DAILY_FULL_JOB_PREFIX`；无额外共享触发任务。 |
| `TC-S12-F4-003` | 定时器 / P0 | `AC-S12-4.2` | `JD-STATIC`、`REAL` | 新建分模块 Job 尚未人工 Build | 检查 init 后 Job config。 | Job 创建时已存在且仅存在一个 `0 2 * * *` TimerTrigger；无需首次 Build；重复配置不追加第二个 trigger。 |
| `TC-S12-F4-004` | 历史兼容 / P0 | `AC-S12-4.3` | `JD-STATIC`、`REAL` | 遗留共享 Daily Job 含历史 build 和 TimerTrigger | 执行 init 后检查 Job config 和历史 build 列表。 | 共享 Job 仍存在且历史 build 数量/编号保留；TimerTrigger 被移除；其它非定时配置不被无关清空。 |
| `TC-S12-F4-005` | 幂等 / P0 | `AC-S12-4.4` | `JD-STATIC`、`REAL` | 首次 init 已创建所有 Job | 连续重启 Jenkins 或重复执行 init 3 次，比较 Job、JobProperty 和 TimerTrigger 数量。 | 每次结果一致；不产生重复 Job、属性或触发器；已有历史 build 不删除。 |
| `TC-S12-F4-006` | 配置异常 / P0 | `AC-S12-4.4` | `JD-STATIC` | 分别模拟模块 YAML 缺失、语法非法、结构缺字段 | 运行 init 并捕获日志，比较执行前后已有 Job 配置。 | 明确记录错误并跳过 Daily Job 变更；不覆盖、删除或重建已有 Job；Jenkins 仍可启动或明确失败方式符合脚本契约。 |
| `TC-S12-F4-007` | 安全边界 / P1 | `AC-S12-4.1` | `JD-STATIC` | YAML 含空 package、路径分隔符、`..`、控制字符和超出安全字符集名称 | 执行命名解析/init。 | 非安全 package 被跳过并给出脱敏诊断；不得写入 Job 名或路径；安全 package 继续正常创建，单项失败不污染其它模块。 |
| `TC-S12-F4-008` | 契约一致 / P0 | `AC-S12-4.1`、`AC-S12-4.4` | `JD-STATIC`、`BE-PY` | 自定义非敏感 Job 前缀；同一 YAML 供 Jenkins init 与 `sync_jenkins_job_bindings` 使用 | 分别生成 Job 和 binding 并对比名称；扫描配置文本。 | 两端名称完全一致；变更仅通过环境变量/Compose 服务名/volume 注入；无本机绝对路径、宿主机固定端口或真实凭据。 |

## 8. F5 趋势窗口与真实历史补同步

| 编号 | 类型 / 优先级 | 关联 AC | 层级 | 前置条件与测试数据 | 操作步骤 | 预期结果与后置状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S12-F5-001` | 正常 / P0 | `AC-S12-5.1` | `BE-PY`、`REAL` | 冻结本地请求日为 7 月 12 日；快照完成日仍为 7 月 10 日；历史存在 7 月 11/12 真实记录 | GET 30 天趋势并检查查询边界和 series。 | 窗口结束日为请求当天 7 月 12 日，不依赖快照日；series 可包含 7 月 11/12，日期升序且只来自真实历史。 |
| `TC-S12-F5-002` | 空洞日期 / P0 | `AC-S12-5.2` | `BE-PY`、`FE-PW` | 30 天窗口中间有一天无 ModuleRunHistory，前后两天有不同通过率 | 查询 API 并打开趋势。 | 响应中缺失日没有 0 值、复制前日或补点记录；前端按返回点绘制，不人为补线点或显示伪造统计。 |
| `TC-S12-F5-003` | 真实补同步 / P0 | `AC-S12-5.3` | `REAL` | 已核验真实 build 20/21 artifact 均属于模块 2；记录补同步前任务、历史和快照 | 通过受控 Django shell 复用正式同步服务补同步 20/21；查询数据库和趋势。 | 生成真实 `daily_full` 任务/运行/历史，统计值来自 artifact，按各自 Jenkins 实际完成日期落库；不执行裸 SQL、不手工拼统计值。 |
| `TC-S12-F5-004` | 真实状态恢复 / P0 | `AC-S12-5.4` | `REAL`、`FE-PW` | task 57/58 对应 build 28/29；至少一个任务仅有 queue id；记录两个模块旧快照和锁 | 受控补同步 28/29，随后查询任务、TestRun、快照、用例、历史、锁并刷新 UI。 | 两个任务进入各自真实终态，两个模块快照和当前用例按完整 summary 更新，趋势写入真实日期，执行锁释放；页面显示新日期/执行时间/任务状态。 |
| `TC-S12-F5-005` | 窗口边界与契约 / P0 | `AC-S12-5.1` | `BE-PY` | 分别构造 7 天、30 天窗口边界内外记录；同日包含 daily_full 和多个 module_rerun；准备普通成员、未登录身份和不存在 snapshot id | 1. 请求 `days=7`、`days=30`。<br>2. 请求 `days=0/8/31/abc`。<br>3. 验证未登录、普通成员和不存在 snapshot。 | 有效窗口最多分别返回 7/30 个日期且升序；窗口外记录排除；同日继续“模块重试优先，否则最后一次完整执行”；非法 days 返回 422 `validation_error`；未登录沿用认证错误；已授权普通成员可读；不存在返回 404 `module_snapshot_not_found`。 |
| `TC-S12-F5-006` | 归属异常 / P0 | `AC-S12-5.3` | `BE-PY`、`REAL` | 候选 artifact 的目标模块 node id 路径与预期模块不一致 | 尝试受控补同步并检查数据库差异和错误输出。 | 立即停止该 build 补同步并上报归属不一致；不猜测模块、不改目标快照/用例/历史；错误信息不展开 artifact 内容。 |
| `TC-S12-F5-007` | 补同步幂等 / P0 | `AC-S12-5.3`、`AC-S12-5.4` | `BE-PY`、`REAL` | 20/21/28/29 已成功补同步一次 | 原样再次执行同一受控同步脚本，比较前后行数和关键字段。 | 第二次不产生重复 JenkinsTask、TestRun、ModuleRunHistory、当前用例或锁；事实字段保持一致，仅允许刷新同步审计字段。 |
| `TC-S12-F5-008` | 前端可见结果 / P0 | `AC-S12-5.1`、`AC-S12-5.4` | `FE-PW`、`REAL` | 补同步完成；普通成员已登录；沿用 Stage9/Stage11 既有页面与交互 | 刷新模块列表，打开 7/30 天趋势和 Jenkins 任务弹窗；检查桌面与移动视口。 | 模块日期显示 Jenkins 实际完成日本地值，执行时间显示 summary 时长，趋势包含真实点且无空洞补造，任务显示真实终态；不新增 worker 文案、配置入口或按钮，布局无新增溢出。 |

## 9. JenkinsTask 关键状态迁移覆盖

| 源状态 | 事件 | 目标状态 / 保持 | 主要用例 |
| --- | --- | --- | --- |
| queued | queue 存在且未分配 executable | queued | `TC-S12-F3-001` |
| queued | queue 404，queueId/RUN_ID 唯一恢复到运行中 build | running | `TC-S12-F1-001`、`TC-S12-F1-002` |
| queued/running | 查询到终态且 artifact 完整 | success / test_failed / failed | `TC-S12-F1-001`、`TC-S12-F2-002`、`TC-S12-F3-003` |
| queued/running | Jenkins 网络、认证、超时或 5xx | 原状态 | `TC-S12-F1-005` |
| queued/running | 无精确 build 且超过既有 2 小时 | failed | `TC-S12-F1-008` |
| canceling | Jenkins 确认 canceled/ABORTED | canceled | 纳入 `TC-S12-F3-001` active 任务批量同步断言：释放锁且不更新模块指标 |

## 10. 入口回归清单

- 单任务 sync：200 queue 恢复/保持、403、404、409 `jenkins_build_ambiguous`、503 `jenkins_unavailable` 分类和终态幂等。
- 批量 Daily sync：保留 `discover_daily=true` 与可选 date；单 Job 失败或 build 匹配歧义时继续，其余 Job 可同步；全部歧义仍返回 200，全部配置 Job 真不可达时才返回 503。
- 趋势 API：`days=7|30`、422 非法 days、404 快照不存在、登录权限和既有响应字段不变。
- 模块页面：日期、执行时间、趋势和任务弹窗仅消费既有字段；无新增页面、路由、组件、按钮和说明文案。
- 安全与容器化：`.env`/私有变量不进入文档或日志；Compose、Job 和 worker 不写死个人路径、宿主机端口或真实地址。
