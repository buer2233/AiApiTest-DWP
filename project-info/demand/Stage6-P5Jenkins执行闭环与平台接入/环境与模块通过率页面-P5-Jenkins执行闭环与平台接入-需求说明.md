# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入 需求说明书

## 元信息 [必填]

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入 |
| 需求分级 | M |
| 裁剪说明 | 不裁剪。本阶段承接 P4 已验收的三条 Jenkins 流水线，并把 Jenkins 执行、任务记录、执行互斥、结果同步、报告入口、失败重试和模块重试接入 DRF/Vue，涉及后端数据模型、API 契约、前端交互、Jenkins API、报告链接、安全和容器化配置。 |
| 关联模块 | `api-test` / `back-end` / `front-end` / `jenkins` / `docker` |
| 文档状态 | 已冻结 |
| 负责人 | 主人 |

---

## §0 待澄清清单（澄清门禁）[必填]

> 本清单未全部闭环前，本阶段不得进入功能测试用例、UI 原型、后端或前端开发。

| 编号 | 待澄清点 | 可选方案 / 影响面 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- |
| Q1 | P5 是否拆分为 P5-A / P5-B | 方案 A：本阶段一次性打通任务记录、触发、同步、前端入口；优点是闭环完整，缺点是本阶段较大。方案 B：拆 P5-A 任务记录与入口、P5-B 触发与同步；优点是风险小，缺点是主人验收次数增加且重试按钮继续延期。推荐方案 A。 | 采纳方案 A：P5 不拆分，本阶段一次性打通平台接入闭环。 | 已确认 |
| Q2 | 每日 02:00 全量执行如何进入平台任务记录 | 方案 A：Jenkins cron 触发后由平台同步任务定时轮询 Jenkins builds；优点是不改 P4 Job 参数和脚本，缺点是同步有延迟。方案 B：Jenkins 构建时回调 DRF 内部接口；优点是实时，缺点是要给 Jenkins 配后端地址和回调凭据。推荐方案 A，本阶段先做后端同步接口/命令，下一步可演进回调。 | 采纳方案 A：Daily 由后端同步/轮询 Jenkins builds，不改 P4 脚本做回调。 | 已确认 |
| Q3 | 平台是否提供“手动触发每日全量”入口 | 方案 A：不提供，Daily Job 只由 Jenkins cron 或 Jenkins 手工触发，本平台只同步展示；范围更符合 P4 决策。方案 B：平台也能触发 Daily 全量 Job；需新增 UI 与 API。推荐方案 A。 | 采纳方案 A：平台不提供手动触发每日全量入口。 | 已确认 |
| Q4 | Jenkins 构建 `SUCCESS` 但 `summary.json.status=failed` 时平台任务状态 | 方案 A：新增 `test_failed`，区分 Jenkins 基础设施成功但测试用例失败；最利于排障。方案 B：直接记为 `failed`；简单但混淆基础设施失败和测试失败。推荐方案 A。 | 采纳方案 A：映射为 `test_failed`。 | 已确认 |
| Q5 | 取消任务时执行锁释放时机 | 方案 A：取消接口成功调用 Jenkins 后任务进入 `canceling`，锁保持到同步确认 `canceled` 后释放；更安全。方案 B：进入 `canceling` 即释放锁；用户可更快重试但可能并发。推荐方案 A。 | 采纳方案 A：`canceling` 后先保留锁，确认 `canceled` 后释放。 | 已确认 |
| Q6 | 失败重试/模块重试触发权限 | 方案 A：仅管理人员可触发重试，普通成员只读；更安全。方案 B：登录用户均可触发，沿父需求草案。推荐方案 A，取消任务仍允许管理人员或任务触发人。 | 采纳方案 A：失败重试/模块重试仅管理人员可触发。 | 已确认 |
| Q7 | Jenkins Job 映射存放方式 | 方案 A：新增 `jenkins_job_binding` 表，按环境、模块、任务类型维护 Job full name；最清晰，支持每日全量每模块一个 Job。方案 B：在 `TestModule` 增字段；简单但扩展性弱。方案 C：仅环境变量前缀拼接；最省表但不适合模块差异。推荐方案 A。 | 采纳方案 A：新增 `jenkins_job_binding` 表维护 Job 映射。 | 已确认 |
| Q8 | 后端读取 Jenkins artifact 的方式 | 方案 A：通过 Jenkins artifact API / URL 读取 `summary.json` 和 `failed_nodeids.json`，只保存摘要和链接，不复制 HTML 报告入库；范围可控。方案 B：复制 artifact 到平台存储；更完整但需要报告服务/存储策略。推荐方案 A。 | 采纳方案 A：通过 Jenkins artifact API 读取 summary，不复制报告入库。 | 已确认 |
| Q9 | Allure 报告链接来源 | 方案 A：优先使用 Jenkins Allure 插件 URL；若未安装插件，则使用 artifact 中 `allure-report/index.html` 链接。方案 B：仅使用 artifact 链接。推荐方案 A。 | 采纳方案 A：优先插件 URL，未安装插件则用 artifact HTML 链接。 | 已确认 |
| Q10 | 详情弹窗“一键失败重试”的范围 | 方案 A：当前模块全部当前失败用例，不受页面当前筛选条件影响；与模块行一键失败重试一致。方案 B：当前筛选范围内失败用例；更贴合父需求一句描述但易误解。推荐方案 A。 | 采纳方案 A：重试当前模块全部当前失败用例。 | 已确认 |
| Q11 | 是否新增全局 Jenkins 任务路由 | 方案 A：本阶段只在 `/modules` 提供当前模块今日 Jenkins 任务弹窗，不新增全局路由。方案 B：新增 `/jenkins-tasks` 全局任务列表。推荐方案 A，保留后端全局列表 API 供后续扩展。 | 采纳方案 A：不新增全局 Jenkins 任务路由。 | 已确认 |
| Q12 | 前端触发/取消后的刷新策略 | 方案 A：触发或取消成功后立即刷新模块任务弹窗，并在弹窗打开时每 5 秒轮询运行中任务，关闭弹窗即停止。方案 B：只手工刷新。推荐方案 A。 | 采纳方案 A：弹窗打开时每 5 秒轮询刷新，关闭即停止。 | 已确认 |

---

## §1 需求背景与目标 [必填]

- **背景**：
  - P1-P3 已完成用户权限、测试数据底座、只读通过率页、用例详情、状态审计和趋势数据。
  - P4 已按主人决策先行完成三条 Jenkins 流水线脚本，并在 Jenkins 实例验证通过：每日全量、失败重试、模块重试。
  - 当前平台仍不能从 Vue/DRF 触发 Jenkins，也不能在平台内展示 Jenkins 任务、取消任务、同步结果或启用失败重试/模块重试按钮。
- **目标**：
  - DRF 能记录、触发、取消和同步 Jenkins 任务。
  - Vue 模块页启用失败重试、模块重试和 Jenkins 任务入口。
  - Jenkins 运行结果同步后能更新模块快照、用例结果、历史趋势和报告入口。
  - 同一环境同一模块同一时刻只允许一个执行中任务，冲突提示固定为“已有用例重试，无法执行！”。
  - 失败重试不更新模块“日期”和“执行时间”；模块重试和每日全量更新这两个字段。
- **成功指标 / 价值**：
  - 用户可以从平台完成失败重试和模块重试，无需直接进入 Jenkins 参数页。
  - Jenkins build、Allure 报告、测试 summary、失败 node id 在平台内可追踪。
  - 测试失败和 Jenkins 基础设施失败可以区分，便于定位问题。

## §2 范围 [必填]

- **做（in scope）**：
  - Jenkins 任务记录、Job 映射和模块执行锁数据模型。
  - DRF Jenkins client/service：触发构建、读取 queue/build、取消构建、读取 artifact summary。
  - 平台触发失败重试：模块行一键失败重试、详情弹窗勾选失败重试、详情弹窗一键失败重试，三者共用同一个后端接口。
  - 平台触发模块重试。
  - 同步每日全量、失败重试、模块重试的 Jenkins 结果。
  - 当前模块今日 Jenkins 任务弹窗、取消任务、查看报告、查看 Jenkins 任务。
  - Vue 模块页按钮启用、确认、提交中、成功、失败、锁冲突、轮询刷新和移动端适配。
  - `.env.example`、后端文档、Docker/Jenkins 配置说明同步新增非敏感 Jenkins 接入变量。
  - 后端 pytest、前端 Playwright/Vitest、Jenkins/API-test 静态回归证据。
- **不做（out of scope）**：
  - 不改写 P4 已验收的三条 Jenkins 流水线脚本，除非接入中发现契约缺口并单独回写测试。
  - 不新增 AI 分析报告生成能力。
  - 不让前端直接调用 Jenkins。
  - 不把真实 Jenkins URL、账号、API Token、Cookie、生产地址或报告运行产物提交到仓库。
  - 不新增除管理人员、普通成员之外的角色。
  - 不新增全局 Jenkins 任务页面，除非 Q11 被主人裁决为需要。

## §3 用户角色与权限矩阵 [必填]

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| 管理人员 | 查看模块、用例、趋势和 Jenkins 任务；触发失败重试、模块重试；取消任意可取消任务；查看 Allure/Jenkins 外链；手动同步任务；查看完整错误详情 | 不得在页面维护真实 Jenkins 凭据；不得绕过 Jenkins 直接执行 pytest | 全部环境、全部模块、全部任务 |
| 普通成员 | 查看模块、用例、趋势、Jenkins 任务、Allure 报告和 Jenkins 任务页面 | 默认不允许触发重试、取消他人任务、手动改状态或管理邀请码；若 Q6 裁决为登录用户均可触发，则只允许触发自己的重试任务 | 默认全部测试数据可读 |
| Jenkins / 系统同步 | 写入或更新 Jenkins 任务状态、summary、失败 node id、快照和报告链接 | 不访问用户私有 Cookie；不执行前端操作 | 仅内部服务使用 |

---

## §4 功能清单与验收标准 [必填 · 核心章节]

### F1 Jenkins Job 映射与接入配置

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 平台能按环境、模块和任务类型找到对应 Jenkins Job full name。
  - 失败重试和模块重试可使用全局 Job；每日全量按“一个模块一个 Job”绑定。
  - 后端调用 Jenkins 使用私有配置，前端只接收后端授权后的跳转链接。
- **关联数据表**：`jenkins_job_binding`
- **验收标准（Given-When-Then）**：
  - `AC-P5-1.1` — Given 模块存在 Job 绑定 When 触发失败重试或模块重试 Then DRF 使用绑定的 Jenkins Job full name 调用 Jenkins。
  - `AC-P5-1.2` — Given 模块缺少对应任务类型 Job 绑定 When 用户触发重试 Then 返回 `422 jenkins_job_not_configured`，不创建 Jenkins 构建。
  - `AC-P5-1.3` — Given `.env.example` 被检查 When 查找 Jenkins 接入变量 Then 只包含非敏感 URL、Job 名、超时和轮询配置，不包含用户名、API Token 或 Cookie。
- **异常场景**：
  - Job 绑定禁用或不存在 -> `422 jenkins_job_not_configured`。
  - Jenkins API base URL 未配置 -> `503 jenkins_unavailable`。
- **边界值**：
  - Job full name 允许多级 folder 路径，例如 `folder/job-name`。
- **并发 / 幂等**：Job 映射只读使用，不产生执行并发。

### F2 Jenkins 任务记录与状态同步

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 平台记录 Jenkins queue/build、触发人、任务类型、Jenkins 链接、Allure 链接和 summary 摘要。
  - Jenkins queue/build 轮询能把任务从 `queued` 推进到 `running`、`success`、`test_failed`、`failed`、`canceling`、`canceled`。
  - 同步必须优先读取 Jenkins artifact 中的 `summary.json` 与 `failed_nodeids.json`。
- **关联数据表**：`jenkins_task`、`test_run`
- **验收标准（Given-When-Then）**：
  - `AC-P5-2.1` — Given Jenkins 触发返回 queue id When DRF 创建任务 Then `jenkins_task` 状态为 `queued` 并记录 queue URL。
  - `AC-P5-2.2` — Given queue 已分配 build number When 同步任务 Then 任务状态进入 `running` 并记录 build number、Jenkins build URL。
  - `AC-P5-2.3` — Given Jenkins build 完成且 `summary.json.status=passed` When 同步任务 Then 任务状态变为 `success`。
  - `AC-P5-2.4` — Given Jenkins build 完成但 `summary.json.status=failed` When 同步任务 Then 任务状态变为 `test_failed`，并保存失败 node id。
  - `AC-P5-2.5` — Given Jenkins 基础设施失败、Allure 未生成或 artifact 缺失 When 同步任务 Then 任务状态变为 `failed` 并保存错误摘要。
  - `AC-P5-2.6` — Given Jenkins 任务已取消 When 同步任务 Then 任务状态变为 `canceled` 并释放执行锁。
- **异常场景**：
  - Jenkins API 超时 -> 任务保留原状态，记录同步错误；触发类接口返回 `503 jenkins_unavailable`。
  - artifact 缺失 -> `failed`，错误摘要说明缺少文件。
- **边界值**：
  - 同步重复调用必须幂等，不重复创建同一 build 的任务记录。
- **并发 / 幂等**：同一 `job_name + build_number` 唯一；同一 `queue_id` 同步不可重复创建。

### F3 每日全量结果同步

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 每日全量仍由 Jenkins cron `0 2 * * *` 按模块 Job 触发。
  - 平台通过同步机制发现或更新每日全量任务。
  - 每日全量同步后更新环境快照、模块快照、当前用例结果和模块历史。
- **关联数据表**：`jenkins_task`、`test_run`、`environment_snapshot`、`module_snapshot`、`test_case_result`、`module_run_history`
- **验收标准（Given-When-Then）**：
  - `AC-P5-3.1` — Given 每日全量 Jenkins Job 在 02:00 触发 When 平台同步 Jenkins build Then 产生或更新一条 `daily_full` Jenkins 任务记录。
  - `AC-P5-3.2` — Given 每日全量 summary 同步成功 When 查看环境和模块页面 Then 展示最新统计。
  - `AC-P5-3.3` — Given 某模块每日全量完成 When 查看模块行 Then “日期”和“执行时间”更新为本次完整模块执行结果。
  - `AC-P5-3.4` — Given 每日全量产生失败用例 When 同步当前用例结果 Then 旧当前结果归档，新结果成为当前展示数据。
- **异常场景**：
  - Jenkins cron 没有产生构建 -> 平台不伪造任务；只保留最近一次已知数据。
- **边界值**：
  - 同一天同一模块多次 Daily build 只以最新完成 build 作为模块当前基线。
- **并发 / 幂等**：同步按 `job_name + build_number` 幂等。

### F4 失败重试触发与同步

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 模块行“一键失败重试”、详情弹窗勾选“失败重试”、详情弹窗“一键失败重试”共用后端接口。
  - 后端统一把目标失败用例 node id 列表传入 Jenkins `PYTEST_NODE_IDS`，不使用 `all-failed`。
  - 失败重试不更新模块“日期”和“执行时间”。
- **关联数据表**：`jenkins_task`、`module_execution_lock`、`test_case_result`、`module_snapshot`
- **验收标准（Given-When-Then）**：
  - `AC-P5-4.1` — Given 模块存在当前失败用例 When 管理人员点击模块行一键失败重试 Then DRF 创建 `failed_rerun` Jenkins 任务并传入全部当前失败 node id。
  - `AC-P5-4.2` — Given 详情弹窗勾选 1 条或多条失败用例 When 点击失败重试 Then DRF 仅传入勾选失败用例 node id。
  - `AC-P5-4.3` — Given 详情弹窗点击一键失败重试 When 提交 Then DRF 传入当前模块全部当前失败 node id。
  - `AC-P5-4.4` — Given 模块通过率为 100% When 点击失败重试 Then 不触发 Jenkins，返回 `422 no_failed_cases`。
  - `AC-P5-4.5` — Given 失败重试执行完成且部分用例通过 When 同步结果 Then 更新对应当前用例展示状态、失败数和通过率。
  - `AC-P5-4.6` — Given 失败重试完成 When 查看模块行 Then “日期”和“执行时间”保持失败重试前的完整执行值。
- **异常场景**：
  - 勾选为空、跨模块、非当前结果、非失败状态 -> `422 invalid_case_selection`。
  - 已有有效执行锁 -> `409 module_execution_locked`，消息“已有用例重试，无法执行！”。
- **边界值**：
  - node id 去重后为空 -> `422 invalid_case_selection`。
- **并发 / 幂等**：创建任务前必须获取同环境同模块执行锁。

### F5 模块重试触发与同步

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 模块行点击“模块重试”后，Jenkins 执行当前模块全部用例。
  - 模块重试完成后更新模块“日期”和“执行时间”，并以本次完整结果刷新当前用例结果。
- **关联数据表**：`jenkins_task`、`module_execution_lock`、`module_snapshot`、`test_case_result`、`module_run_history`
- **验收标准（Given-When-Then）**：
  - `AC-P5-5.1` — Given 模块无执行锁 When 管理人员点击模块重试 Then 创建 `module_rerun` Jenkins 任务并传入模块 `CASE_PATH`。
  - `AC-P5-5.2` — Given 模块重试同步成功 When 查看模块行 Then 统计、日期和执行时间全部更新。
  - `AC-P5-5.3` — Given 模块重试产生新失败用例 When 同步结果 Then 旧当前用例结果归档，新结果成为当前展示数据。
  - `AC-P5-5.4` — Given 同一模块已有失败重试运行中 When 点击模块重试 Then 返回 `409 module_execution_locked`，消息“已有用例重试，无法执行！”。
- **异常场景**：
  - Jenkins 不可用 -> `503 jenkins_unavailable`，锁回滚释放。
- **边界值**：
  - 模块没有 `case_path` -> `422 module_case_path_missing`。
- **并发 / 幂等**：创建任务前必须获取同环境同模块执行锁。

### F6 当前模块今日 Jenkins 任务弹窗

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 模块行点击“Jenkins任务”打开当前模块今日任务弹窗。
  - 弹窗展示任务编号、任务名、任务类型、测试环境 URL、状态、触发人、开始/结束时间、Jenkins 链接、Allure 报告链接和操作。
  - 可取消 `queued` / `running` 任务；查看报告和查看 Jenkins 任务新页打开。
- **关联数据表**：`jenkins_task`
- **验收标准（Given-When-Then）**：
  - `AC-P5-6.1` — Given 当前模块今天存在 Jenkins 任务 When 点击 Jenkins 任务 Then 弹窗分页展示任务列表。
  - `AC-P5-6.2` — Given 任务状态为 `queued` 或 `running` When 有权限用户点击取消 Then 后端调用 Jenkins 取消接口，任务进入 `canceling`。
  - `AC-P5-6.3` — Given 任务有 Allure 报告链接 When 点击查看报告 Then 浏览器新页打开后端返回的可信链接。
  - `AC-P5-6.4` — Given 任务有 Jenkins build 链接 When 点击查看 Jenkins 任务 Then 浏览器新页打开后端返回的可信链接。
  - `AC-P5-6.5` — Given 弹窗存在运行中任务 When 弹窗保持打开 Then 前端按轮询策略刷新任务状态。
- **异常场景**：
  - 无任务 -> 展示空态。
  - 无报告链接 -> 查看报告按钮禁用。
  - 非管理人员且非触发人取消 -> `403 forbidden`。
- **边界值**：
  - 默认 `date=today`，支持 `YYYY-MM-DD` 查询。
- **并发 / 幂等**：重复取消同一任务，如果已进入 `canceling`，返回当前状态，不重复调用无效操作。

### F7 操作按钮状态与前端反馈

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 模块行按钮按后端 actions、权限和锁状态启用或禁用。
  - 触发类操作必须有确认弹窗、提交中状态、成功提示、失败提示和可恢复刷新。
  - 移动端卡片中操作不溢出、不重叠。
- **关联数据表**：不直接持久化，依赖 `module_snapshot`、`jenkins_task`、`module_execution_lock`
- **验收标准（Given-When-Then）**：
  - `AC-P5-7.1` — Given 后端 actions 返回可触发 When 页面渲染模块行 Then 失败重试、模块重试、Jenkins 任务按钮可点击。
  - `AC-P5-7.2` — Given 后端返回 disabled reason When 页面渲染按钮 Then 展示禁用态并通过 tooltip 或提示说明原因。
  - `AC-P5-7.3` — Given 用户确认触发重试 When 请求进行中 Then 对应按钮展示提交中并避免重复提交。
  - `AC-P5-7.4` — Given 后端返回锁冲突 When 前端展示错误 Then 文案为“已有用例重试，无法执行！”。
  - `AC-P5-7.5` — Given 移动端宽度 When 操作按钮展示 Then 文本不溢出、不遮挡其它内容。
- **异常场景**：
  - API 返回 401 -> 跳转登录或展示登录失效。
  - API 返回 403 -> 展示无权限。
- **边界值**：
  - 长模块名、长 Job 名不撑破布局。
- **并发 / 幂等**：前端提交中禁止重复点击；后端仍以锁为准。

---

## §5 状态机定义 [必填（若存在状态流转）]

### 实体：`jenkins_task.status`

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| 无 | 平台成功触发 Jenkins queue | `queued` | 获取执行锁成功 | 创建 `jenkins_task`、关联 `test_run`、记录 queue URL |
| `queued` | Jenkins queue 分配 build | `running` | build number 存在 | 写入 build number、build URL |
| `running` | build 完成且 summary passed | `success` | artifact 存在且可解析 | 写入 summary，释放锁，按运行类型刷新数据 |
| `running` | build 完成且 summary failed | `test_failed` | artifact 存在且可解析 | 写入失败 node id，释放锁，按运行类型刷新数据 |
| `queued` / `running` | 用户取消 | `canceling` | 有取消权限且 Jenkins 接受取消 | 暂不释放锁，等待同步确认 |
| `canceling` | Jenkins 确认取消 | `canceled` | build/queue 已取消 | 释放锁 |
| `queued` / `running` / `canceling` | Jenkins API 或 artifact 基础设施失败 | `failed` | 同步达到失败条件 | 记录错误摘要，释放锁 |
| `success` / `test_failed` / `failed` / `canceled` | 重复同步 | 原状态 | 终态 | 幂等更新同步时间，不重复刷新已处理数据 |

### 实体：`module_execution_lock.status`

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| 无 | 创建失败重试或模块重试任务 | `active` | 同环境同模块无 active 锁 | 写入 `active_lock_key` |
| `active` | 任务进入 `success` / `test_failed` / `failed` / `canceled` | `released` | 任务终态 | 清空 `active_lock_key`，写入释放时间 |
| `active` | 锁超时回收 | `expired` | 超过配置超时且 Jenkins 无运行中 build | 清空 `active_lock_key`，记录原因 |

### 实体：`test_case_result.display_status`

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| `failed` | 失败重试后该 node id 通过 | `passed` | 仅失败重试影响选中失败用例 | 刷新模块失败数和通过率，不更新日期/执行时间 |
| 任意当前状态 | 模块重试或每日全量同步 | 新执行结果状态 | 本次完整执行结果存在 | 旧当前结果归档，新结果成为当前数据 |
| `failed` / `passed` / `skipped` | 管理人员手动改状态 | 目标状态 | P3 既有规则 | 刷新统计并写审计 |

---

## §6 数据表设计 [必填（若涉及持久化）]

### 表 `jenkins_job_binding`

- **用途**：维护环境、模块、任务类型到 Jenkins Job full name 的映射。
- **写入策略**：管理配置或种子数据写入；运行时只读。
- **关键约束**：`environment_id + module_id + task_type` 唯一；每日全量允许每模块独立 Job。

| 字段 | 类型建议 | 必填 | 默认 | 说明 | 索引 / 约束 |
| --- | --- | --- | --- | --- | --- |
| `id` | bigint pk | 是 | | 主键 | PK |
| `environment_id` | bigint fk | 是 | | 测试环境 | idx / uniq |
| `module_id` | bigint fk | 是 | | 测试模块 | idx / uniq |
| `task_type` | varchar(32) | 是 | | `daily_full` / `failed_rerun` / `module_rerun` | uniq |
| `job_full_name` | varchar(255) | 是 | | Jenkins Job full name，支持 folder 路径 | idx |
| `default_retry_count` | integer | 是 | 0 | 默认 pytest rerun 次数 | |
| `is_active` | boolean | 是 | true | 是否启用 | idx |
| `created_at` / `updated_at` | datetime | 是 | now | 时间戳 | |

### 表 `jenkins_task`

- **用途**：记录平台可见的 Jenkins 执行任务、状态、链接、summary 和同步错误。
- **写入策略**：触发时创建；同步时按 queue/build 幂等更新；不物理删除。
- **关键约束**：`job_full_name + build_number` 非空时唯一；`queue_id` 非空时唯一。

| 字段 | 类型建议 | 必填 | 默认 | 说明 | 索引 / 约束 |
| --- | --- | --- | --- | --- | --- |
| `id` | bigint pk | 是 | | 主键 | PK |
| `run_id` | bigint fk nullable | 否 | | 关联 `test_run` | idx |
| `environment_id` | bigint fk | 是 | | 测试环境 | idx |
| `module_id` | bigint fk | 是 | | 测试模块 | idx |
| `task_type` | varchar(32) | 是 | | `daily_full` / `failed_rerun` / `module_rerun` | idx |
| `trigger_source` | varchar(32) | 是 | | `platform_user` / `jenkins_cron` / `manual_sync` | idx |
| `triggered_by_id` | bigint fk nullable | 否 | | 平台触发人；Jenkins cron 可为空 | idx |
| `job_full_name` | varchar(255) | 是 | | Jenkins Job full name | idx |
| `queue_id` | varchar(128) | 否 | | Jenkins queue id | unique nullable |
| `build_number` | integer | 否 | | Jenkins build number | unique with job |
| `jenkins_queue_url` | varchar(1024) | 否 | | Jenkins queue URL | |
| `jenkins_build_url` | varchar(1024) | 否 | | Jenkins build URL | |
| `artifact_base_url` | varchar(1024) | 否 | | Jenkins artifact 根 URL | |
| `summary_artifact_url` | varchar(1024) | 否 | | `summary.json` URL | |
| `failed_nodeids_artifact_url` | varchar(1024) | 否 | | `failed_nodeids.json` URL | |
| `allure_report_url` | varchar(1024) | 否 | | Allure 报告 URL | |
| `status` | varchar(32) | 是 | `queued` | `queued/running/success/test_failed/failed/canceling/canceled` | idx |
| `jenkins_result` | varchar(64) | 否 | | Jenkins build result 原值 | |
| `summary_json` | json | 否 | | `summary.json` 摘要 | |
| `failed_nodeids_json` | json | 否 | | 失败 node id 列表 | |
| `error_summary` | text | 否 | | Jenkins/API/artifact 同步错误摘要 | |
| `started_at` / `finished_at` | datetime | 否 | | Jenkins 执行时间 | idx |
| `last_synced_at` | datetime | 否 | | 最近同步时间 | idx |
| `created_at` / `updated_at` | datetime | 是 | now | 时间戳 | |

### 表 `module_execution_lock`

- **用途**：保证同一环境同一模块同一时刻只有一个执行中 Jenkins 任务。
- **写入策略**：创建任务时写 active 锁；任务终态或超时后释放。
- **关键约束**：MySQL 兼容唯一约束，使用可空 `active_lock_key` 表达仅 active 锁唯一。

| 字段 | 类型建议 | 必填 | 默认 | 说明 | 索引 / 约束 |
| --- | --- | --- | --- | --- | --- |
| `id` | bigint pk | 是 | | 主键 | PK |
| `environment_id` | bigint fk | 是 | | 测试环境 | idx |
| `module_id` | bigint fk | 是 | | 测试模块 | idx |
| `task_id` | bigint fk | 是 | | 关联 Jenkins 任务 | idx |
| `lock_type` | varchar(32) | 是 | | `module_execution` | |
| `status` | varchar(32) | 是 | `active` | `active/released/expired` | idx |
| `active_lock_key` | varchar(128) nullable | 否 | | active 时为 `env:{id}:module:{id}`，释放后为空 | unique nullable |
| `locked_at` / `released_at` | datetime | 否 | | 锁定与释放时间 | idx |
| `release_reason` | varchar(255) | 否 | | 释放原因 | |
| `created_at` / `updated_at` | datetime | 是 | now | 时间戳 | |

### 既有表调整

| 表 | 调整 | 说明 |
| --- | --- | --- |
| `test_run` | 状态枚举增加 `test_failed`、`canceling`；补充 Jenkins task 关联或通过 `jenkins_task.run_id` 关联 | 区分测试失败、基础设施失败和取消中 |
| `test_case_result` | 可选增加 `source_task_id`、`last_retry_task_id` | 追溯用例结果来源和最近重试任务 |
| `module_snapshot` | actions 增加可用性和 disabled reason | 前端按钮状态由后端授权返回 |

---

## §7 API 契约 [必填（若涉及接口）· 冻结后前后端共同依据]

### `POST /api/v1/module-snapshots/{snapshot_id}/failed-case-retries`

- **用途 / 权限**：触发失败重试；推荐仅管理人员可执行。
- **请求参数**：

| 参数 | 位置 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `snapshot_id` | path | integer | 是 | 存在且环境启用 | 模块快照 |
| `retry_scope` | body | string | 是 | `all_failed` / `selected_failed` | 重试范围 |
| `case_result_ids` | body | array[integer] | 否 | `selected_failed` 必填 | 勾选失败用例 ID |

- **成功响应**：`202 Accepted`

```json
{
  "data": {
    "id": 301,
    "task_type": "failed_rerun",
    "status": "queued",
    "job_full_name": "AiApiTest-DWP-Failed-Rerun",
    "queue_id": "1288",
    "actions": {
      "cancel": true,
      "view_report": false,
      "view_jenkins_task": false
    }
  }
}
```

- **错误码**：

| HTTP | 业务码 | 含义 | 触发条件 |
| --- | --- | --- | --- |
| 401 | `authentication_required` | 未登录 | 无有效 Cookie |
| 403 | `admin_required` | 无触发权限 | 普通成员触发且 Q6 采用推荐方案 |
| 404 | `module_snapshot_not_found` | 模块快照不存在 | snapshot 无效或环境停用 |
| 409 | `module_execution_locked` | 已有用例重试，无法执行！ | 同环境同模块已有 active 锁 |
| 422 | `invalid_case_selection` | 勾选用例不可重试 | 空、跨模块、非当前或非失败 |
| 422 | `no_failed_cases` | 通过率 100% 无需失败重试 | 当前失败数为 0 |
| 422 | `jenkins_job_not_configured` | Jenkins Job 未配置 | 无 active job binding |
| 503 | `jenkins_unavailable` | Jenkins 不可用 | 触发 API 失败 |

- **关键状态流转 / 幂等**：成功触发后创建 `jenkins_task=queued` 和 active lock；Jenkins 触发失败必须回滚锁。

### `POST /api/v1/module-snapshots/{snapshot_id}/module-reruns`

- **用途 / 权限**：触发模块重试；推荐仅管理人员可执行。
- **请求参数**：

| 参数 | 位置 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `snapshot_id` | path | integer | 是 | 存在且环境启用 | 模块快照 |

- **成功响应**：`202 Accepted`，结构同失败重试，`task_type=module_rerun`。
- **错误码**：同失败重试；另包含 `422 module_case_path_missing`。
- **关键状态流转 / 幂等**：成功触发后创建 active lock；终态释放锁。

### `GET /api/v1/module-snapshots/{snapshot_id}/jenkins-tasks`

- **用途 / 权限**：查询当前模块 Jenkins 任务弹窗数据；登录用户可读。
- **请求参数**：

| 参数 | 位置 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `snapshot_id` | path | integer | 是 | 存在 | 模块快照 |
| `date` | query | string | 否 | `today` 或 `YYYY-MM-DD` | 默认 today |
| `status` | query | string | 否 | 任务状态枚举 | 状态筛选 |
| `page` / `per_page` | query | integer | 否 | page >= 1，per_page 1-100 | 分页 |

- **成功响应**：`200 OK`

```json
{
  "data": [
    {
      "id": 301,
      "task_type": "failed_rerun",
      "job_name": "失败重试",
      "environment_url": "https://api.gbif.org",
      "status": "running",
      "triggered_by": "admin",
      "started_at": "2026-07-05T10:00:00+08:00",
      "finished_at": null,
      "jenkins_build_url": "http://localhost:8080/job/AiApiTest-DWP-Failed-Rerun/12/",
      "allure_report_url": null,
      "actions": {
        "cancel": true,
        "view_report": false,
        "view_jenkins_task": true
      }
    }
  ],
  "meta": {
    "total": 1,
    "page": 1,
    "per_page": 20,
    "total_pages": 1
  }
}
```

- **错误码**：`401 authentication_required`、`404 module_snapshot_not_found`、`422 validation_error`。

### `POST /api/v1/jenkins-tasks/{task_id}/cancel`

- **用途 / 权限**：取消 Jenkins queue/build；管理人员或任务触发人可执行。
- **请求参数**：

| 参数 | 位置 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `task_id` | path | integer | 是 | 存在 | Jenkins 任务 |

- **成功响应**：`202 Accepted`

```json
{
  "data": {
    "id": 301,
    "status": "canceling",
    "actions": {
      "cancel": false,
      "view_report": false,
      "view_jenkins_task": true
    }
  }
}
```

- **错误码**：

| HTTP | 业务码 | 含义 | 触发条件 |
| --- | --- | --- | --- |
| 403 | `forbidden` | 无取消权限 | 非管理人员且非触发人 |
| 404 | `jenkins_task_not_found` | 任务不存在 | ID 无效 |
| 409 | `task_not_cancelable` | 任务不可取消 | 任务已终态 |
| 503 | `jenkins_unavailable` | Jenkins 不可用 | Jenkins 取消接口失败 |

### `POST /api/v1/jenkins-tasks/{task_id}/sync`

- **用途 / 权限**：手动同步单个 Jenkins 任务；仅管理人员或内部调用可执行。
- **成功响应**：`200 OK`，返回同步后的 Jenkins task。
- **错误码**：`403 admin_required`、`404 jenkins_task_not_found`、`503 jenkins_unavailable`。
- **关键状态流转 / 幂等**：同步终态任务不重复刷新快照；只更新同步时间和缺失链接。

### `POST /api/v1/jenkins-tasks/sync`

- **用途 / 权限**：批量同步运行中任务或按条件发现 Daily build；仅管理人员或内部命令可执行。
- **请求体**：

| 字段 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- |
| `task_status` | array[string] | 否 | 状态枚举 | 默认 queued/running/canceling |
| `discover_daily` | boolean | 否 | bool | 是否发现 Daily cron build |
| `date` | string | 否 | `YYYY-MM-DD` | 发现 Daily build 的日期 |

- **成功响应**：`200 OK`，返回同步数量、创建数量、失败数量。

### `GET /api/v1/jenkins-tasks`

- **用途 / 权限**：全局 Jenkins 任务列表 API；登录用户可读，本阶段前端不新增路由。
- **请求参数**：`environment_id`、`module_id`、`task_type`、`status`、`date_from`、`date_to`、`page`、`per_page`。
- **成功响应**：`200 OK`，分页返回 Jenkins task。

### 既有接口调整

| 接口 | 调整 |
| --- | --- |
| `GET /api/v1/module-snapshots` | `actions.failed_rerun/module_rerun/jenkins_tasks` 由 `false` 改为依据权限、失败数、Job 配置和锁状态计算；可附 `disabled_reasons`。 |
| `GET /api/v1/module-snapshots/{snapshot_id}/cases` | 失败用例 `actions.can_retry` 依据权限、当前状态和锁状态返回。 |

---

## §8 UI 字段级规格 [必填（若涉及页面）]

### 页面：模块通过率 `/modules`

| 元素 | 字段来源（对应 §7 API 字段） | 状态枚举 / 标签 | 加载/空/错误/权限态 | 操作与反馈 |
| --- | --- | --- | --- | --- |
| 一键失败重试 | `module_snapshot.actions.failed_rerun` | 可用 / 禁用 / 提交中 | 无失败用例、无权限、锁冲突、Job 未配置时禁用或提示 | 二次确认后调用 `POST /failed-case-retries` |
| 模块重试 | `module_snapshot.actions.module_rerun` | 可用 / 禁用 / 提交中 | 无权限、锁冲突、Job 未配置时禁用或提示 | 二次确认后调用 `POST /module-reruns` |
| Jenkins 任务 | `module_snapshot.actions.jenkins_tasks` | 可用 | 加载失败可重试 | 打开 Jenkins 任务弹窗 |
| 日期 / 执行时间 | `module_snapshot.completed_at/duration_seconds` | 时间 / 秒 | 失败重试后不变；模块重试和 Daily 后更新 | 用于验收 AC-P5-4.6 / AC-P5-5.2 |

### 弹窗：用例详情

| 元素 | 字段来源（对应 §7 API 字段） | 状态枚举 / 标签 | 加载/空/错误/权限态 | 操作与反馈 |
| --- | --- | --- | --- | --- |
| 勾选框 | `case.actions.can_retry` | 可勾选 / 禁用 | 仅当前失败用例可勾选 | 选中后启用失败重试 |
| 失败重试 | 本地选中 `case_result_ids` | 禁用 / 可用 / 提交中 | 空选择禁用 | 调用 `POST /failed-case-retries`，`retry_scope=selected_failed` |
| 一键失败重试 | 当前模块失败数 | 禁用 / 可用 / 提交中 | 无失败用例禁用 | 调用 `POST /failed-case-retries`，`retry_scope=all_failed` |

### 弹窗：Jenkins 任务

| 元素 | 字段来源（对应 §7 API 字段） | 状态枚举 / 标签 | 加载/空/错误/权限态 | 操作与反馈 |
| --- | --- | --- | --- | --- |
| 任务表格 | `GET /module-snapshots/{id}/jenkins-tasks` | queued/running/success/test_failed/failed/canceling/canceled | 默认 today；无任务空态 | 分页展示 |
| 取消任务 | `task.actions.cancel` | 可取消 / 禁用 / 取消中 | 非 queued/running 禁用；无权限禁用或 403 | 调用 `POST /jenkins-tasks/{id}/cancel` |
| 查看报告 | `allure_report_url` | 可点击 / 禁用 | 无链接禁用 | 新页打开 |
| 查看 Jenkins 任务 | `jenkins_build_url` | 可点击 / 禁用 | 无链接禁用 | 新页打开 |

### UI 区域语义拆解与前端实现范围映射

| 区域 | 内容 | 前端处理方式 | 路由 / 组件 | 触发动作 | 不得进入当前 DOM 的内容 |
| --- | --- | --- | --- | --- | --- |
| R1 | 模块列表表格和移动端卡片 | 当前页面直接展示 | `/modules` / `ModulesView.vue` | 进入模块页 | Jenkins 参数页、Allure 页面 |
| R2 | 模块行失败重试/模块重试确认 | 弹窗/确认框 | `ModulesView.vue` 或确认组件 | 点击模块行按钮 | Jenkins 构建控制台 |
| R3 | 用例详情勾选与重试 | 弹窗内状态 | `CaseDetailsDialog.vue` | 点击通过率 | 非当前模块用例 |
| R4 | Jenkins 任务弹窗 | 弹窗 | `JenkinsTasksDialog.vue` | 点击 Jenkins 任务 | Jenkins 外部页面 iframe |
| R5 | 取消/锁冲突/任务状态反馈 | 当前页面消息和弹窗状态 | `ModulesView.vue` / `JenkinsTasksDialog.vue` | 触发、取消、轮询 | 设计说明文字 |
| R6 | 报告和 Jenkins 外链 | 新页打开 | 普通 `<a target="_blank">` 或按钮 | 点击查看报告 / 查看 Jenkins 任务 | 平台 Cookie 验证叠加页面 |
| R7 | 移动端布局 | 响应式当前页面 | `ModulesView.vue` / metrics 组件 | 移动端访问 | 桌面表格强制横向溢出 |
| R8 | Jenkins 参数页、构建详情、Allure 外部页面、设计标注层 | 仅设计说明不实现 | 无 | 外链跳转后由外部系统展示 | 不在 Vue DOM、Playwright 截图验收中实现 |

---

## §9 架构影响评估 [必填 · 质量门禁]

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | `api-test` 仍只负责执行和产物；Jenkins 负责编排；DRF 负责触发、记录、同步；Vue 只调用 DRF。 |
| 数据模型 | 是 | 新增 `jenkins_job_binding`、`jenkins_task`、`module_execution_lock`，并调整 `test_run`/actions。 |
| 权限 | 是 | 平台 API 继续 Cookie 验证；重试触发推荐仅管理人员；外链不叠加平台 Cookie。 |
| Jenkins 执行链路 | 是 | 后端通过 Jenkins API 触发/取消/同步，使用 P4 已验收 Job。 |
| `api-test` 执行协议 | 否/轻微 | 不改 runner 协议；消费既有 `summary.json`、`failed_nodeids.json`。若发现字段不足需单独回写需求。 |
| 报告 / Allure 协议 | 是 | 平台保存 Allure/Jenkins 链接，不复制报告运行产物。 |
| Docker Compose 部署 | 是 | `.env.example` 需补 Jenkins API base URL、Job 名、超时和轮询配置；真实凭据仍留私有环境。 |
| 安全 | 是 | 防止开放跳转；不提交真实凭据；错误摘要脱敏；artifact 缺失需可诊断。 |

## §10 容器化兼容检查 [必填 · 质量门禁]

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 否 | 后端通过 Jenkins API/artifact URL 获取产物，不读取本机 Jenkins workspace。 |
| 宿主机固定端口 | 有风险 | `.env.example` 只给默认示例，后端实际从根 `.env` / 环境变量读取；Compose 内可使用服务名 `jenkins:8080`。 |
| 真实凭据 | 否 | `JENKINS_USERNAME/JENKINS_API_TOKEN` 不进入 `.env.example`，只在私有 `.env` 或 CI/Jenkins Credentials 中配置。 |
| 不可迁移业务常量 | 有风险 | Jenkins Job 名通过配置表或环境变量维护，不写死在代码中。 |
| 手工 Jenkins 配置依赖 | 有风险 | P4 已要求 Jenkins 上配置三类 Job；P5 通过 Job binding 显式记录依赖，验收包列出配置检查。 |

## §11 非功能要求 [S可简]

- **性能**：模块任务列表和全局任务列表必须分页；默认 20，最大 100。任务弹窗轮询间隔默认 5 秒，关闭弹窗停止轮询。
- **安全**：平台 API 必须 Cookie 验证；Jenkins/Allure 链接只返回可信 base URL 下的地址；错误摘要不得泄露 token、cookie 或真实凭据。
- **可用性**：Jenkins 不可用不影响只读模块页面；触发/取消/同步失败要返回明确错误码和可读提示。
- **一致性**：执行锁释放必须与任务终态一致；失败重试不更新日期/执行时间；模块重试和 Daily 更新完整执行基线。
- **可观测性**：任务状态、同步时间、错误摘要、summary、失败 node id 和触发人必须可追踪。

---

## §12 验收口径汇总 [必填]

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| AC-P5-1.1 | Job 绑定存在时按绑定触发 Jenkins | F1 |
| AC-P5-1.2 | Job 绑定缺失时不创建构建并返回错误 | F1 |
| AC-P5-1.3 | `.env.example` 只新增非敏感 Jenkins 接入变量 | F1 |
| AC-P5-2.1 | 触发 Jenkins queue 后创建 queued 任务 | F2 |
| AC-P5-2.2 | queue 分配 build 后任务进入 running | F2 |
| AC-P5-2.3 | summary passed 同步为 success | F2 |
| AC-P5-2.4 | summary failed 同步为 test_failed 并保存失败 node id | F2 |
| AC-P5-2.5 | Jenkins / Allure / artifact 基础设施失败同步为 failed | F2 |
| AC-P5-2.6 | Jenkins 取消后任务 canceled 并释放锁 | F2 |
| AC-P5-3.1 | Daily cron build 同步为 daily_full 任务 | F3 |
| AC-P5-3.2 | Daily 同步后环境和模块页展示最新统计 | F3 |
| AC-P5-3.3 | Daily 更新模块日期和执行时间 | F3 |
| AC-P5-3.4 | Daily 新结果归档旧当前用例结果 | F3 |
| AC-P5-4.1 | 模块行一键失败重试传入全部当前失败 node id | F4 |
| AC-P5-4.2 | 详情勾选失败重试只传入勾选 node id | F4 |
| AC-P5-4.3 | 详情一键失败重试传入当前模块全部当前失败 node id | F4 |
| AC-P5-4.4 | 无失败用例时不触发 Jenkins | F4 |
| AC-P5-4.5 | 失败重试同步后更新失败数和通过率 | F4 |
| AC-P5-4.6 | 失败重试不更新日期和执行时间 | F4 |
| AC-P5-5.1 | 模块重试触发 module_rerun Jenkins 任务 | F5 |
| AC-P5-5.2 | 模块重试同步后更新统计、日期和执行时间 | F5 |
| AC-P5-5.3 | 模块重试新结果成为当前展示数据 | F5 |
| AC-P5-5.4 | 运行中失败重试阻止模块重试 | F5 |
| AC-P5-6.1 | 当前模块今日 Jenkins 任务弹窗分页展示 | F6 |
| AC-P5-6.2 | queued/running 任务可取消并进入 canceling | F6 |
| AC-P5-6.3 | 查看报告新页打开可信 Allure 链接 | F6 |
| AC-P5-6.4 | 查看 Jenkins 任务新页打开可信 Jenkins 链接 | F6 |
| AC-P5-6.5 | 弹窗打开时运行中任务自动轮询刷新 | F6 |
| AC-P5-7.1 | 后端 actions 控制按钮启用 | F7 |
| AC-P5-7.2 | disabled reason 能在前端展示 | F7 |
| AC-P5-7.3 | 请求进行中禁止重复提交 | F7 |
| AC-P5-7.4 | 锁冲突提示固定文案 | F7 |
| AC-P5-7.5 | 移动端操作区域不溢出不重叠 | F7 |

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-07-05 | v0.1 | 新建 P5 Jenkins 执行闭环与平台接入需求草案，列出 12 个待澄清点 | P4 Jenkins 脚本先行配置验收通过后，进入 DRF/Vue 平台接入阶段 |

---

## §14 冻结确认（主人签字门禁）

冻结前逐项核对：

- [x] §0 待澄清清单全部闭环（无“待确认”状态）
- [x] §9 架构影响评估已完成
- [x] §7 API 契约完整、可冻结（前端将据此开发）
- [x] §10 容器化兼容检查通过
- [x] §4 每个功能点都有可测的 Given-When-Then 验收标准

**冻结人（主人）**：`主人（对话确认）`　　**冻结日期**：`2026-07-05`

> 冻结后，下游“功能测试用例 -> UI 原型 -> 后端 TDD -> 前端 TDD”按根 `AGENTS.md` 自动衔接推进；过程中如撞到本文件未覆盖的关键决策，必须暂停上报主人并回写本文件 §0 与 §13，严禁脑补。
