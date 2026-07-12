# 环境与模块通过率页面-模块快照日期与Jenkins自动同步修复-需求说明书

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-模块快照日期与Jenkins自动同步修复 |
| 需求分级 | M |
| 裁剪说明 | 不裁剪。本需求跨 DRF 趋势与快照、Jenkins queue/build 同步、后台轮询、Jenkins Job 初始化和真实历史补同步，影响执行状态流转、API 语义和容器化部署。 |
| 关联模块 | `back-end` / `jenkins` / `docker` / `front-end`（仅既有字段刷新验收） |
| 文档状态 | 已冻结 |
| 负责人 | 主人 |
| 需求质量评分 | 96/100（业务目标 29/30、功能要求 25/25、用户体验 18/20、技术约束 15/15、范围优先级 9/10） |

---

## §0 待澄清清单（澄清门禁）

| 编号 | 待澄清点 | 可选方案 / 影响面 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- |
| Q1 | 执行完成后如何自动进入平台 | A：独立轻量 DRF 轮询进程；B：Jenkins 回调；C：页面懒同步 | 2026-07-12 批准方案 A，覆盖 Stage8“不引入常驻 worker”的旧裁决 | 已确认 |
| Q2 | queue item 已清理但 build 已存在时如何恢复 | 按同 Job 的 `queueId` 精确匹配，必要时再按 `RUN_ID` 精确匹配；禁止取最新 build | 采用精确恢复规则 | 已确认 |
| Q3 | “日期”字段使用何种时间 | A：平台同步时间；B：Jenkins 实际完成时间 | 采用 B；执行时间和趋势日期均以 Jenkins 实际完成时间为准 | 已确认 |
| Q4 | 近 7/30 天窗口结束日期 | A：快照日期；B：请求当天本地日期 | 采用 B；不补造无执行记录日期 | 已确认 |
| Q5 | Daily Job 组织方式 | A：继续遗留共享 Job；B：恢复既有每模块一个 Job 契约 | 采用 B；保留历史 build，不删除历史 Job，移除遗留共享 Job 的定时触发以避免重复执行 | 已确认 |
| Q6 | 已存在错误数据如何处理 | A：只修未来；B：补同步可验证的真实 Jenkins build | 采用 B；只同步真实 artifact，不伪造趋势数据 | 已确认 |

---

## §1 需求背景与目标

- **背景**：
  - 2026-07-12 查询模块 2 的近 30 天趋势时，接口只返回至 2026-07-10；模块快照日期也停在 7 月 10 日。
  - Jenkins 实际存在 7 月 11 日和 7 月 12 日凌晨 2 点的成功 Daily build，模块重试 task 57/58 对应 build 28/29 也已成功，但结果没有进入平台。
  - task 58 仅保存 queue id；Jenkins 清理 queue item 后接口返回 404，后端把该可恢复情况错误映射为 `503 jenkins_unavailable`。
  - Stage6 选择后端轮询架构，Stage8 仅实现手动同步并明确不引入常驻 worker，导致自动执行结果落库链路未真正闭环。
- **目标**：
  - Jenkins Daily、模块重试完成后，无需打开任务弹窗或人工点击同步，平台能自动更新任务、模块快照、当前用例和趋势历史。
  - queue item 被清理后仍能精确恢复对应 build，不误报 Jenkins 服务不可用。
  - 模块“日期”和趋势日期统一反映 Jenkins 实际执行完成日，执行时长继续使用真实 summary 数据。
  - Jenkins 本地 Compose 环境自动维护每模块 Daily Job，避免 Job binding 与真实 Job 漂移。
- **成功指标 / 价值**：
  - worker 正常运行时，Jenkins build 完成后不超过 `JENKINS_BUILD_POLL_INTERVAL_SECONDS + 单次同步耗时` 完成平台落库。
  - queue 过期但 build 存在的同步请求返回 200，任务进入真实终态。
  - 近 30 天趋势窗口始终以请求当天结束，并包含窗口内已同步的真实 7 月 11/12 数据。
  - 同一 Jenkins build 重复发现、重复同步不会重复创建任务、历史或当前用例。

## §2 范围

- **做（in scope）**：
  - 新增可单次执行或持续轮询的 Django Jenkins 同步管理命令。
  - 自动同步 active 平台任务，并自动发现、落库和同步每模块 Daily build。
  - queue 404 后按同 Job 的 `queueId`、精确 `RUN_ID` 恢复 build number。
  - 从 Jenkins build `timestamp` 与 `duration` 计算真实开始、完成时间。
  - 统一更新 `JenkinsTask`、`TestRun`、`ModuleSnapshot`、`ModuleRunHistory` 的时间语义。
  - 趋势查询窗口改为以项目本地当天结束。
  - Compose 自动加载本地 Jenkins Job 初始化脚本；创建每模块 Daily Job并配置 `0 2 * * *`，停用遗留共享 Daily Job 的 TimerTrigger。
  - 修复后补同步已验证的真实 Daily build 20/21 和模块重试 build 28/29。
  - 一次性历史补同步通过受控 Django shell 复用已测试的同步服务；执行脚本和输出归档到 Stage12 验收证据，不新增长期事故修复 API。
  - 更新 `.env.example` 注释、后端/Jenkins/Docker 文档、Swagger 描述、静态测试和验收资料。
- **不做（out of scope）**：
  - 不引入 Celery、Redis 或 APScheduler；worker 使用 Django management command 独立进程。
  - 不新增 Jenkins 回调接口、回调 token 或前端直连 Jenkins。
  - 不在模块列表 GET 请求中隐式执行同步，不给读接口增加外部写副作用。
  - 不新增或迁移业务数据表，不删除 Jenkins 历史 build、JenkinsTask 或 ModuleRunHistory。
  - 不改变失败重试不更新模块日期/执行时间的既有规则。
  - 不伪造没有真实 Jenkins artifact 的趋势日期。

## §3 用户角色与权限矩阵

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| 管理人员 | 继续手动同步、触发模块重试、查看任务和趋势 | 不在页面管理 Jenkins 私有凭据 | 全部环境、模块和任务 |
| 普通成员 | 查看自动同步后的模块日期、执行时间、趋势和任务 | 不触发手动同步或重试 | 已授权平台数据 |
| Jenkins 同步 worker | 使用后端私有配置读取 Jenkins build/artifact，写入任务、快照、用例和趋势 | 不持有用户 Cookie；不触发 pytest；不输出凭据 | active 任务与 active Daily binding 对应 build |

---

## §4 功能清单与验收标准

### F1 queue 过期后的 build 精确恢复

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 本地任务没有 `build_number` 且 Jenkins queue API 返回 404 时，后端查询同一 Job 的有限近期 build。
  - 优先按 Jenkins build 的 `queueId` 与本地 `queue_id` 精确匹配；未匹配时按参数 `RUN_ID` 与 `TestRun.run_key` 精确匹配。
  - 不允许把同 Job 最新 build、相邻并发 build 或其它模块 build 错配到当前任务。
- **关联数据表**：`jenkins_task`、`test_run`、`module_execution_lock`。
- **验收标准**：
  - `AC-S12-1.1` — Given queue 404 且存在 `queueId` 精确匹配 build When 同步任务 Then 恢复 build number 并在同次请求继续读取 build/artifact，返回 200。
  - `AC-S12-1.2` — Given `queueId` 不可用但存在 `RUN_ID` 精确匹配 When 同步 Then 恢复正确 build。
  - `AC-S12-1.3` — Given 同 Job 有多个并发 build When 恢复 Then 只匹配当前 queue/RUN_ID，不选择最新 build；同一精确条件匹配多个 build 时返回 `409 jenkins_build_ambiguous`，保留任务状态并写入诊断。
  - `AC-S12-1.4` — Given queue 404 且暂未发现 build、任务未超时 When 同步 Then 保持 queued 并返回 200，不误报 503。
  - `AC-S12-1.5` — Given Jenkins API 整体不可达或认证失败 When 同步 Then 保留原任务状态并返回 `503 jenkins_unavailable`。
  - `AC-S12-1.6` — Given 触发新任务前刷新旧锁、旧任务 queue 已 404 但 build 已存在 When 刷新 Then 先恢复并同步真实 build，不得直接把旧任务标为 failed。
- **异常场景**：精确条件匹配多个 build -> 不更新任务、TestRun、模块数据或锁，仅记录可诊断错误；单任务 sync 返回 409，批量 sync 隔离该 build 并继续。
- **边界值**：无 queue id 且无 run key -> 不猜测 build；按既有超时规则终结任务并释放锁。
- **并发 / 幂等**：同一 `job_full_name + build_number` 唯一；重复同步不得重复写历史。

### F2 Jenkins 实际完成时间与模块快照更新

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - Jenkins client 读取 build `timestamp`、`duration`、`building` 和 `result`。
  - Jenkins `timestamp` 和 `duration` 均按毫秒解析：`started_at = timestamp`；终态 `finished_at = timestamp + duration`，结果保存为带时区 datetime。
  - Daily 和模块重试同步成功后，快照日期、任务完成时间、TestRun 完成时间和趋势历史使用同一个 Jenkins `finished_at`。
  - `duration_seconds` 继续使用 summary 的模块执行时长，不改为 Jenkins 整体构建耗时。
- **关联数据表**：`jenkins_task`、`test_run`、`module_snapshot`、`environment_snapshot`、`module_run_history`。
- **验收标准**：
  - `AC-S12-2.1` — Given Jenkins build 在 7 月 12 日完成、平台 7 月 13 日才同步 When 落库 Then模块日期和趋势 run_date 仍为 7 月 12 日。
  - `AC-S12-2.2` — Given Daily 或模块重试 summary 完整 When 同步 Then `ModuleSnapshot.completed_at` 与 `ModuleRunHistory.completed_at` 均等于 Jenkins 实际完成时间。
  - `AC-S12-2.3` — Given 失败重试完成 When 同步 Then 不修改模块日期和模块执行时间。
  - `AC-S12-2.4` — Given build 时间字段缺失或非法 When 同步 Then 使用平台同步时刻兜底，并记录不含敏感信息的警告。
- **异常场景**：summary 不完整 -> 保留当前模块指标和用例，任务保存明确错误摘要。
- **边界值**：duration 为 0 合法；负数、非数字或溢出值不得生成错误完成时间。
- **并发 / 幂等**：重复应用同一 source_run 时，ModuleRunHistory 使用既有唯一键 update_or_create。

### F3 轻量 Jenkins 自动同步 worker

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 提供 `python manage.py sync_jenkins_results --once` 执行单轮同步。
  - 提供 `python manage.py sync_jenkins_results --watch` 按 `JENKINS_BUILD_POLL_INTERVAL_SECONDS` 持续轮询。
  - 每轮先同步 queued/running/canceling 平台任务，再读取每个 active Daily binding 最近 50 个 build；通过 `job_full_name + build_number` 跳过已终态且已落库 build，不重复读取 artifact。
  - 单个 Job 或单个任务同步失败不得中断本轮其它任务；命令输出结构化计数和脱敏错误。
- **关联数据表**：`jenkins_job_binding`、`jenkins_task`、`test_run`、`module_execution_lock` 及同步后的业务表。
- **验收标准**：
  - `AC-S12-3.1` — Given 模块重试已完成且页面未打开 When worker 下一轮执行 Then 任务、快照、当前用例和趋势自动更新。
  - `AC-S12-3.2` — Given 每模块 Daily Job 02:00 完成 When worker 发现 build Then 创建或更新 `daily_full` 任务并刷新模块数据。
  - `AC-S12-3.3` — Given worker 重复发现相同 build When 多轮同步 Then 数据库只存在一条对应 JenkinsTask 和一条 source_run 趋势记录。
  - `AC-S12-3.4` — Given worker 暂时无法访问某个 Job When 本轮执行 Then 记录错误并继续其它 Job，后续恢复后可补同步。
  - `AC-S12-3.5` — Given 两个 worker 误启动 When 同步同一任务 Then 唯一约束和事务保证最终结果一致，不产生重复业务数据。
- **异常场景**：数据库不可用 -> 命令以非零退出或当前轮明确失败，不吞异常。
- **边界值**：轮询间隔必须为正整数；非法环境变量回退安全默认值并给出错误。
- **并发 / 幂等**：部署建议单 worker；正确性不依赖单实例，重复外部读取允许但落库必须幂等。

### F4 Daily Job 与 binding 自动一致

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - Compose 将 `configure-local-mounted-jobs.groovy` 作为只读 init 脚本挂载。
  - Jenkins 启动时按 `api-test/utils/package_module.yaml` 和 `JENKINS_DAILY_FULL_JOB_PREFIX` 幂等创建每模块 Daily Job。
  - 每模块 Job 在创建时即配置 `0 2 * * *`，不依赖首次人工 Build 才获得定时器。
  - 遗留共享 Daily Job 保留历史 build，但移除 TimerTrigger，防止与分模块 Job 重复执行。
  - 后端 `sync_jenkins_job_bindings` 继续生成相同命名契约。
- **关联数据表**：`jenkins_job_binding`；Jenkins Job 配置不进入业务数据库。
- **验收标准**：
  - `AC-S12-4.1` — Given Compose 启动 Jenkins When 初始化完成 Then 每个 active 模块均存在与 binding 同名的 Daily Job。
  - `AC-S12-4.2` — Given 新建分模块 Job When 检查配置 Then 已存在单个 `0 2 * * *` TimerTrigger。
  - `AC-S12-4.3` — Given 遗留共享 Daily Job 存在 When 初始化 Then 历史 build 保留但 TimerTrigger 被移除。
  - `AC-S12-4.4` — Given 重启 Jenkins 多次 When 重复执行 init Then 不产生重复 JobProperty、TimerTrigger 或 Job。
- **异常场景**：模块 YAML 缺失或非法 -> 明确日志并跳过 Daily Job 变更，不覆盖已有 Job。
- **边界值**：仅处理安全的 package name 字符集，不把宿主机路径写入 Job 名。
- **并发 / 幂等**：Jenkins 初始化脚本幂等。

### F5 趋势窗口与真实历史补同步

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 近 7/30 天窗口以 `timezone.localdate()` 为结束日。
  - 窗口仅返回真实 ModuleRunHistory，继续执行 Stage11 的“同日模块重试优先，否则最后一次完整执行”规则。
  - 修复部署后通过受控 Django shell 调用正式同步服务补同步可验证的 build 20、21、28、29；不直接手工拼装统计值或执行裸 SQL。
- **关联数据表**：`module_run_history`、`module_snapshot`、`jenkins_task`、`test_run`、`test_case_result`。
- **验收标准**：
  - `AC-S12-5.1` — Given 快照日期停在 7 月 10 日且存在 7 月 11/12 历史 When 查询 30 天趋势 Then 窗口可包含 7 月 11/12。
  - `AC-S12-5.2` — Given 某日期无真实执行记录 When 查询趋势 Then 不生成 0 值或复制前日记录。
  - `AC-S12-5.3` — Given build 20/21 artifact 属于模块 2 When 补同步 Then 生成真实 daily_full 历史并按实际完成日期落库。
  - `AC-S12-5.4` — Given task 57/58 对应 build 28/29 When 补同步 Then 两个模块快照更新，task 终结并释放执行锁。
- **异常场景**：artifact 与目标模块 node id 路径不一致 -> 停止补同步并上报，不猜测模块归属。
- **边界值**：30 天最多返回 30 个日期；同日多条继续每日优选。
- **并发 / 幂等**：补同步可重复执行，第二次不产生重复数据。

---

## §5 状态机定义

- **实体**：`JenkinsTask.status`。

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| queued | queue 存在但未分配 executable | queued | 未超时 | 更新 last_synced_at |
| queued | queue 404，精确恢复到 running build | running | queueId/RUN_ID 唯一匹配 | 保存 build_number/build URL/started_at |
| queued/running | 精确恢复或查询到终态 summary | success/test_failed/failed | artifact 契约校验完成 | 更新任务；Daily/模块重试更新快照、用例、趋势；释放锁 |
| queued/running | 同一精确条件匹配多个 build | 原状态 | queueId/RUN_ID 匹配不唯一 | 记录歧义诊断；单任务 API 返回 409；不更新 build_number 或释放锁 |
| queued/running | Jenkins API 真正不可用 | 原状态 | 网络、认证、5xx | API 返回 503或 worker 记录错误，等待下轮 |
| queued/running | 超过既有 2 小时且无法恢复 | failed | 无 queue/build 精确匹配 | 记录过期原因，释放锁 |
| canceling | Jenkins 确认 canceled/ABORTED | canceled | 取消已生效 | 释放锁，不更新模块指标 |

---

## §6 数据表设计

本需求不新增或迁移数据表，只修正现有表的写入语义。

| 表 | 写入规则变更 | 关键约束 |
| --- | --- | --- |
| `jenkins_task` | 恢复 build 后写入 `build_number`；使用 Jenkins 实际 started_at/finished_at | `queue_id` 唯一；`job_full_name + build_number` 唯一 |
| `test_run` | 与 JenkinsTask 使用相同真实完成时间和终态 | `run_key` 唯一 |
| `module_snapshot` | Daily/模块重试使用 Jenkins 实际完成时间更新 `completed_at`；失败重试不更新 | `environment + module` 唯一 |
| `module_run_history` | run_date 由真实完成时间按项目时区转换；按 source_run 幂等更新 | 既有组合唯一约束 |
| `test_case_result` | 继续按完整 summary 归档旧当前结果并写入新结果 | 当前 node key 唯一 |
| `module_execution_lock` | 真实终态或超时后释放；queue 404 不再立即误判失败 | active_lock_key 唯一 |

---

## §7 API 契约

### POST `/api/v1/jenkins-tasks/{task_id}/sync`

- **用途 / 权限**：管理人员手动同步单个任务；路径、认证和成功响应字段不变。
- **请求参数**：`task_id` 为正整数 path 参数；body 可为空对象。
- **成功响应**：HTTP 200，`data` 为既有 JenkinsTaskSerializer。
- **语义变更**：queue 404 且可恢复时继续同步；暂未找到 build 且未超时时返回 200 queued，不返回 503。

| HTTP | 业务码 | 含义 | 触发条件 |
| --- | --- | --- | --- |
| 403 | `admin_required` | 需要管理员权限 | 非管理员调用 |
| 404 | `jenkins_task_not_found` | 本地任务不存在 | task_id 无记录 |
| 409 | `jenkins_build_ambiguous` | Jenkins build 精确匹配不唯一 | 同一 queueId 或 RUN_ID 匹配到多个 build；任务状态和锁保持不变 |
| 503 | `jenkins_unavailable` | Jenkins 服务真实不可用 | 网络、认证、超时或服务端错误；不包含单个 queue 404 |

- **关键状态流转 / 幂等**：重复调用已终态任务仅刷新 last_synced_at；不会重复应用 summary。

### POST `/api/v1/jenkins-tasks/sync`

- **用途 / 权限**：保留管理员手动 Daily discovery 入口；worker 与管理命令复用同一同步服务，不通过 HTTP 自调用。
- **请求参数**：现有 `discover_daily=true` 和可选 `date` 不变。
- **成功响应**：HTTP 200，保留 created_count/updated_count/synced_count。
- **错误处理变更**：单个 Job 404/失败或 build 匹配歧义应可记录并继续其它 Job；全部 build 均为匹配歧义时仍返回 200 计数，不得误报 `jenkins_unavailable`；所有配置 Job 均真实不可访问时才返回 503。

### GET `/api/v1/module-snapshots/{snapshot_id}/trend?days=7|30`

- **用途 / 权限**：登录用户读取模块真实趋势。
- **请求与响应字段**：路径、参数、外层结构和 series 字段不变。
- **语义变更**：窗口结束日固定为项目本地请求当天，不再读取 snapshot.completed_at 作为结束日。
- **错误码**：继续使用 404 `module_snapshot_not_found`、422 `validation_error`。

### 管理命令契约

```text
python manage.py sync_jenkins_results --once
python manage.py sync_jenkins_results --watch
python manage.py sync_jenkins_results --watch --interval 10
```

- `--once` 与 `--watch` 互斥；未指定时默认单轮，避免误启动常驻进程。
- `--interval` 仅 watch 模式使用，默认读取 `JENKINS_BUILD_POLL_INTERVAL_SECONDS`。
- 命令不输出 Jenkins 用户名、token、Cookie、Authorization header 或 artifact 内容。

---

## §8 UI 字段级规格

本需求不新增页面、路由、组件或弹窗，不改变 Stage9/Stage11 UI 区域语义拆解。

| 元素 | 字段来源 | 状态 | 加载/错误态 | 操作与反馈 |
| --- | --- | --- | --- | --- |
| 模块表格“日期” | `ModuleSnapshot.completed_at` | Jenkins 实际完成时间的本地展示 | 沿用现有列表状态 | worker 同步后由既有刷新机制更新 |
| 模块表格“执行时间” | `duration_seconds` | summary 模块执行时长 | 沿用现有状态 | Daily/模块重试更新；失败重试不更新 |
| 7/30 天趋势 | trend `series` | 真实历史；同日优选 | 沿用 Stage11 空/错态 | 不展示 worker 说明文字 |
| Jenkins 任务弹窗 | JenkinsTask fields | queued/running/终态 | 沿用现有轮询 | queue 恢复对用户透明；不增加新按钮 |

前端实现范围冻结：不把 worker、轮询间隔、Jenkins Job 初始化说明放入产品 DOM；仅补受影响 Playwright 断言。

---

## §9 架构影响评估

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | 后端新增独立 management worker，但同步职责仍属于 DRF 数据中心；不下沉到前端或 api-test |
| 数据模型 | 否 | 无迁移，只修正时间和幂等写入语义 |
| 权限 | 否 | 手动 API 权限不变；worker 为内部进程，不使用用户身份 |
| Jenkins 执行链路 | 是 | 自动初始化每模块 Daily Job；queue/build 恢复；停用遗留共享 Job 定时器 |
| `api-test` 执行协议 | 否 | CASE_PATH、RUN_ID、summary、failed_nodeids 和 Allure 协议不变 |
| 报告 / Allure 协议 | 否 | 继续读取既有 artifact 和插件 URL |
| Docker Compose 部署 | 是 | Jenkins 新增只读 init 脚本挂载；worker 未来可复用 backend 镜像作为独立 service |
| 安全 | 是 | worker 使用私有 `.env` Jenkins 凭据；日志必须脱敏；不新增回调 token |

API 契约冻结结论：路径和响应字段不变，仅修正错误分类、时间语义和趋势窗口；Swagger 描述与回归测试必须同步。

---

## §10 容器化兼容检查

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 否 | management command 仅使用 Django 配置；Jenkins Job 脚本继续使用 `AIAPITEST_LOCAL_WORKSPACE` 和仓库挂载 |
| 宿主机固定端口 | 否 | Jenkins 地址来自 `JENKINS_API_BASE_URL`；worker 不写死端口 |
| 真实凭据 | 否 | 仅从根 `.env`/CI 私有变量读取，不进入 `.env.example`、日志或文档 |
| 不可迁移业务常量 | 否 | Job 前缀、轮询间隔、超时均使用既有环境变量或命令参数 |
| 手工 Jenkins 配置依赖 | 是，需消除 | Compose 自动挂载并执行幂等 Job 初始化脚本；不再依赖 Script Console 手工执行 |

- 当前阶段后端仍在宿主机运行：本地以独立命令启动 worker。
- 后续 backend 容器化时：使用相同镜像增加 `jenkins-sync-worker` service，命令为 `python manage.py sync_jenkins_results --watch`，通过 Compose 服务名访问 MySQL/Jenkins。
- 启动后不建议修改 Jenkins Job 前缀；修改会导致 binding 与历史任务链接漂移，需重新执行 Job/binding 同步并评估历史兼容。

---

## §11 非功能要求

- **性能**：每轮只同步 active 任务、新发现 Daily build和未终态 Daily 任务；已终态任务不重复读取 artifact。
- **安全**：不输出真实 URL 中可能携带的凭据、Authorization、token、Cookie 或完整 artifact 内容。
- **可用性**：单任务、单 Job 失败隔离；Jenkins 恢复后自动补同步。
- **兼容性**：pytest 使用 SQLite；正式运行支持 MySQL；Windows 宿主机和未来 Linux Compose 均使用同一 management command。
- **可观测性**：每轮输出 discovered/synced/recovered/failed/skipped 计数、任务 id、脱敏 Job 名和错误类型。
- **停止语义**：watch 模式响应 Ctrl+C/SIGTERM 并正常退出，不留下数据库锁。

---

## §12 验收口径汇总

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| AC-S12-1.1~1.6 | queue 404 精确恢复、旧锁刷新、并发隔离和错误分类 | F1 |
| AC-S12-2.1~2.4 | Jenkins 实际完成时间和失败重试时间规则 | F2 |
| AC-S12-3.1~3.5 | 自动 worker、Daily discovery、故障隔离和幂等 | F3 |
| AC-S12-4.1~4.4 | 分模块 Daily Job、cron、遗留 Job和初始化幂等 | F4 |
| AC-S12-5.1~5.4 | 趋势当天窗口与真实 build 补同步 | F5 |

最终验收必须包含：

1. 后端目标测试 RED/GREEN、全量 pytest 与覆盖率证据。
2. Jenkins/Docker 静态测试与真实 Jenkins Job 配置证据。
3. worker 单轮和 watch 模式真实运行证据。
4. task 57/58 从 queued 恢复为真实终态，锁释放。
5. module2 近 30 天接口包含 7 月 11/12 的真实记录，并遵守同日模块重试优先。
6. 模块列表日期和执行时间与 Jenkins 实际完成时间、summary 一致。
7. 独立 review subagent 无未闭环 Critical/Important。
8. 历史补同步脚本、命令输出和补同步前后数据对比归档在 Stage12 验收证据目录。

---

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-07-12 | 0.1 | 建立 Stage12 根因与方案 A 可执行规格 | 主人报告趋势、日期和 sync 503 问题 |
| 2026-07-12 | 0.2 | 冻结轻量 worker、queue 恢复、真实时间、Daily Job 初始化和补同步范围 | 主人批准方案 A |

---

## §14 冻结确认（主人签字门禁）

- [x] §0 待澄清清单全部闭环
- [x] §9 架构影响评估已完成
- [x] §7 API 契约完整
- [x] §10 容器化兼容检查完成
- [x] §4 每个功能点均有可测 Given-When-Then 验收标准
- [x] 主人已复核本书面规格

**方案方向批准人（主人）**：主人　　**批准日期**：2026-07-12

**书面规格冻结人（主人）**：主人　　**冻结日期**：2026-07-12

> 主人确认本文件后，文档状态改为“已冻结”，下游功能测试、UI 范围校准、后端 TDD、Jenkins/Docker 实现、独立审查和真实验收自动连续推进。
