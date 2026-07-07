# 环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入 需求说明书

## 元信息 [必填]

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入 |
| 父需求 | 环境与模块通过率页面（`project-info/demand/环境与模块通过率页面-需求说明.md` v0.3 已冻结） |
| 关联历史阶段 | P3 趋势数据、P5 Jenkins 执行闭环与平台接入 |
| 需求分级 | M |
| 裁剪说明 | 不裁剪。本阶段涉及 `/modules` 页面筛选与列顺序调整、DRF 查询契约、Jenkins Job binding 初始化、Jenkins 任务弹窗增强、趋势数据持久化口径校准和验收证据，横跨 `back-end`、`front-end`、`jenkins`、`docker`，按 M 档完整 loop 推进。 |
| 关联模块 | `back-end` / `front-end` / `jenkins` / `docker`；`api-test` 执行协议本阶段默认不变。 |
| 文档状态 | 已冻结 |
| 负责人 | 主人 |
| 阶段目录 | `Stage8-模块通过率筛选与Jenkins趋势接入` |

---

## §0 待澄清清单（澄清门禁）[必填]

> 本清单未全部闭环前，不得进入功能测试用例、UI 原型、后端或前端开发阶段。截图中的红字、红框和箭头是设计标注层，只用于说明需求，不进入产品 DOM、截图断言或 Playwright 验收。

| 编号 | 待澄清点 | 可选方案 / 影响面 | 推荐裁决 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- | --- |
| Q1 | 7 天 / 30 天趋势“单独数据库表”的落点 | 方案 A：继续使用 P3 已建 `module_run_history`，它已是模块趋势专用表；方案 B：再新增一张趋势展示表。方案 B 会造成双写和数据源冲突。 | 采用方案 A：`module_run_history` 作为趋势单独表，本阶段补齐写入/展示验收，不新增重复表。 | 采纳推荐方案 A：继续使用 `module_run_history` 作为趋势单独表，不新增重复趋势表。 | 已确认 |
| Q2 | 趋势写入范围 | 方案 A：每日全量必须写入每天每模块通过率；模块重试作为完整模块基线也写入；失败重试不写入趋势，避免非完整执行污染日趋势。方案 B：失败重试也写入。 | 采用方案 A：`daily_full` 和 `module_rerun` 写 `module_run_history`，`failed_rerun` 只刷新当前失败数/通过率，不写趋势。 | 采纳推荐方案 A：`daily_full` 和 `module_rerun` 写趋势，`failed_rerun` 不写趋势。 | 已确认 |
| Q3 | Jenkins Job binding 初始化方式 | 方案 A：新增 `sync_jenkins_job_bindings` 管理命令，读取 `.env` 中 `JENKINS_FAILED_RERUN_JOB_NAME`、`JENKINS_MODULE_RERUN_JOB_NAME`、`JENKINS_DAILY_FULL_JOB_PREFIX` 并按当前环境/模块 upsert `jenkins_job_binding`；方案 B：新增管理页面维护。 | 采用方案 A：先用管理命令补齐本地和 CI 初始化，不新增管理页面。 | 采纳推荐方案 A：新增 `sync_jenkins_job_bindings` 管理命令，不新增管理页面。 | 已确认 |
| Q4 | 多选筛选语义 | 方案 A：名称、包名、模块开发、模块测试均为下拉多选，后端按逗号分隔 query 做精确 `IN` 匹配；方案 B：多选后仍做模糊匹配。 | 采用方案 A：多选精确匹配，URL 参数如 `module_name=示例模块1,示例模块2`，避免多选语义不确定。 | 采纳推荐方案 A：四个多选筛选使用逗号分隔 query，后端精确 `IN` 匹配。 | 已确认 |
| Q5 | 多选下拉选项来源 | 方案 A：新增 `GET /api/v1/module-snapshots/filter-options?environment_id=`，后端按环境聚合去重选项；方案 B：前端只从当前页数据去重。 | 采用方案 A：后端提供完整选项，避免分页导致选项缺失。 | 采纳推荐方案 A：新增后端筛选选项 API，按环境聚合完整选项。 | 已确认 |
| Q6 | `pass_rate_lte` 上限筛选处理 | 方案 A：前端删除上限筛选且不再发送；后端保留兼容但从 Stage8 Swagger/验收中移除主路径。方案 B：后端同步删除并让旧 URL 报错。 | 采用方案 A：UI 删除，后端兼容旧 URL，降低破坏面。 | 采纳推荐方案 A：前端删除上限筛选，后端兼容旧 URL，Stage8 主路径不再强调。 | 已确认 |
| Q7 | Jenkins 同步增强范围 | 方案 A：本阶段补齐手动/命令式同步 queued/running/canceling 和 Daily discovery，可通过 API 或管理命令触发；不引入后台常驻 worker。方案 B：引入 Celery/APScheduler。 | 采用方案 A：不扩基础设施，先保证可验收同步入口。 | 采纳推荐方案 A：补齐手动/命令式同步入口，不引入后台常驻 worker。 | 已确认 |
| Q8 | Jenkins 任务弹窗增强范围 | 方案 A：补状态筛选、日期筛选和任务类型列；保持当前模块弹窗，不新增全局 Jenkins 页面。方案 B：新增全局任务页。 | 采用方案 A：当前模块弹窗增强，延续 P5 不新增全局路由的裁决。 | 采纳推荐方案 A：增强当前模块 Jenkins 任务弹窗，不新增全局 Jenkins 页面。 | 已确认 |
| Q9 | 失败重试与模块重试触发确认 | 方案 A：失败重试不做二次确认，点击“失败重试”后直接调用接口触发 Jenkins 对应 Job，并提示“开始执行失败重试”；模块重试必须弹出确认框。方案 B：失败重试和模块重试均二次确认。 | 采用方案 A：失败重试保持高频操作效率；模块重试影响全量用例、测试时间和执行时间，必须确认。 | 采纳方案 A：失败重试无需二次确认，直接触发并提示“开始执行失败重试”；模块重试确认文案为“模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？”。 | 已确认 |

---

## §1 需求背景与目标 [必填]

- **背景**：
  - P3 已建立 `module_run_history` 并提供 7 天 / 30 天趋势 API，P5 已完成 Jenkins 触发、取消、同步、执行锁、失败重试和模块重试闭环。
  - 主人在当前截图中标注 6 点新需求：前 5 点是模块通过率页面筛选区和列顺序调整；第 6 点要求前后端接入 Jenkins 构建执行，并保证 7 天 / 30 天趋势按独立表沉淀每天通过率数据。
  - 现状代码已经具备 Jenkins 触发接口，但本地演示数据默认缺少 `jenkins_job_binding` 初始化，可能导致按钮禁用；筛选区仍保留上限筛选和文本输入；通过率列仍位于执行时间前。
- **目标**：
  - `/modules` 页面删除筛选描述文案和“上限筛选”，新增“模块开发”筛选。
  - 名称、包名、模块开发、模块测试四个筛选改为下拉多选，选项来自后端聚合。
  - “重置”按钮视觉风格与“查询”一致但尺寸更小，并放在筛选操作区最左侧。
  - 表格列顺序调整为“通过率”位于“跳过”之后、“后置能力”之前。
  - 补齐 Jenkins Job binding 初始化和同步入口，使失败重试、模块重试、Jenkins 任务弹窗在平台内可稳定触发、查询和验收。
  - 继续使用趋势专用表沉淀每天模块通过率，并确保 7 天 / 30 天趋势展示来自后端历史表。
- **成功指标 / 价值**：
  - 主人截图中 6 点标注均可被测试用例、UI 原型、后端和前端验收追溯。
  - 平台用户不需要手动进入 Jenkins 参数页即可从模块行触发失败重试和模块重试。
  - 7 天 / 30 天趋势不是前端临时计算，且每天通过率数据可在数据库中追溯。

---

## §2 范围 [必填]

- **做（in scope）**：
  - `/modules` 页面标题说明文案调整，删除“筛选与分页状态会同步到地址栏”等筛选描述。
  - 删除前端“上限筛选”输入框；新增“模块开发”筛选。
  - 名称、包名、模块开发、模块测试使用 Element Plus 下拉多选，支持清空、重置、URL 同步。
  - 新增模块筛选选项 API，并调整模块列表筛选契约。
  - 调整桌面表格和移动端卡片中通过率的展示位置。
  - 新增或补齐 Jenkins Job binding 初始化命令，使用 `.env.example` 已声明的非敏感 Job 名变量。
  - 校准 Jenkins 任务弹窗：状态/日期筛选、任务类型展示、同步后刷新。
  - 校准趋势表写入和趋势弹窗数据来源，确保每天通过率数据写入 `module_run_history`。
  - 补齐后端 pytest、前端 Vitest/Playwright、截图证据、RTM 和验收包。
- **不做（out of scope）**：
  - 不新增全局 Jenkins 任务独立页面。
  - 不新增 Jenkins Job 管理页面。
  - 不新增 Celery、APScheduler 或常驻后台 worker。
  - 不修改 `api-test` runner 执行协议，除非开发阶段发现 P5 已冻结契约无法满足并触发熔断。
  - 不把 Jenkins / Allure 页面 iframe 嵌入 Vue。
  - 不提交真实 Jenkins URL、账号、API Token、Cookie、报告运行产物或本机绝对路径。

---

## §3 用户角色与权限矩阵 [必填]

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| 管理人员（admin） | 使用模块多选筛选；查看趋势；触发失败重试、模块重试；查看 Jenkins 任务；取消可取消任务；手动/命令式同步 Jenkins 任务 | 不得在前端维护 Jenkins 凭据；不得绕过 Jenkins 直接执行 pytest | 全部环境、全部模块、全部 Jenkins 任务 |
| 普通成员（member） | 使用模块多选筛选；查看模块列表、趋势、Jenkins 任务和外链 | 不得触发失败重试、模块重试；不得取消他人任务；不得执行同步命令 | 全部只读测试数据，操作按钮按后端权限禁用 |
| Jenkins / 系统同步 | 写入每日全量、模块重试的运行结果和趋势历史；同步任务状态 | 不访问用户 Cookie；不写真实凭据入库 | 内部服务使用 |

---

## §4 功能清单与验收标准 [必填 · 核心章节]

### F1 模块通过率筛选区调整

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 页面不再展示筛选说明文案和“上限筛选”。
  - 筛选项包含测试环境、名称、包名、模块开发、模块测试。
  - 名称、包名、模块开发、模块测试均为下拉多选，支持搜索、清空、选择多个值。
  - 筛选查询提交后同步 URL query，刷新页面后可还原筛选条件。
  - “重置”按钮使用与“查询”一致的主按钮视觉语言，尺寸更小，位于操作区最左侧；点击后清空四个多选筛选并保留当前或默认测试环境。
- **关联数据表**：复用 `test_module`、`module_snapshot`
- **验收标准（Given-When-Then）**：
  - `AC-S8-1.1` — Given 用户打开 `/modules` When 页面渲染 Then 页面说明中不出现“筛选与分页状态会同步到地址栏”或等价筛选描述。
  - `AC-S8-1.2` — Given 用户打开筛选区 When 查看筛选项 Then 不展示“上限筛选”，且展示“模块开发”筛选。
  - `AC-S8-1.3` — Given 后端返回名称、包名、模块开发、模块测试选项 When 用户展开任一下拉 Then 可多选并可清空。
  - `AC-S8-1.4` — Given 用户选择多个模块名称和模块开发 When 点击查询 Then URL query 和后端请求携带逗号分隔多值，列表只展示匹配模块。
  - `AC-S8-1.5` — Given 用户已选择多个筛选 When 点击重置 Then 四个多选筛选清空、页码回到 1，并重新查询当前环境模块列表。
- **异常场景**：
  - 筛选选项 API 失败 -> 下拉显示错误/空态，模块列表已有查询不崩溃。
  - query 中包含不存在的选项 -> 后端返回空列表，不报前端运行时错误。
- **边界值**：
  - 单个筛选字段最多接收 50 个值；单个值长度最多 128。
  - `per_page` 仍限制 1-100。

### F2 模块表格列顺序调整

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 桌面表格列顺序调整为：日期、用例包名、模块名称、执行时间、模块开发、模块测试、总数、失败、跳过、通过率、后置能力。
  - 通过率仍可点击打开用例详情弹窗，视觉和可访问性标签保持。
  - 移动端卡片中通过率位置也放在总数/失败/跳过之后、后置能力之前。
- **关联数据表**：不直接持久化，复用模块快照响应字段。
- **验收标准**：
  - `AC-S8-2.1` — Given 桌面端打开模块表格 When 查看表头顺序 Then “通过率”位于“跳过”之后、“后置能力”之前。
  - `AC-S8-2.2` — Given 用户点击通过率 When 模块存在用例详情 Then 仍打开对应模块用例详情弹窗。
  - `AC-S8-2.3` — Given 移动端访问模块页 When 查看模块卡片 Then 通过率不遮挡、不溢出，且位于统计字段之后。

### F3 Jenkins Job binding 初始化与触发可用性

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 后端提供 `sync_jenkins_job_bindings` 管理命令，根据当前启用环境、启用模块和 `.env` 中非敏感 Job 名变量 upsert `jenkins_job_binding`。
  - 失败重试、模块重试按钮的可用性由 `jenkins_job_binding`、权限、失败数和执行锁共同决定。
  - 触发失败重试或模块重试时，继续调用 P5 已冻结的 DRF 接口，由 DRF 调 Jenkins，不允许前端直连 Jenkins。
- **关联数据表**：`jenkins_job_binding`、`jenkins_task`、`module_execution_lock`
- **验收标准**：
  - `AC-S8-3.1` — Given `.env` 配置了 `JENKINS_FAILED_RERUN_JOB_NAME` 和 `JENKINS_MODULE_RERUN_JOB_NAME` When 执行 `sync_jenkins_job_bindings` Then 每个启用环境和启用模块都存在 active 失败重试、模块重试 Job binding。
  - `AC-S8-3.2` — Given `.env` 配置了 `JENKINS_DAILY_FULL_JOB_PREFIX` When 执行命令 Then 每个启用环境和启用模块存在 active Daily Job binding，Job 名按 `{JENKINS_DAILY_FULL_JOB_PREFIX}-{module.package_name}` 生成。
  - `AC-S8-3.3` — Given Job binding 存在且用户为管理人员 When 点击失败重试或模块重试 Then 后端创建 `queued` Jenkins task 并调用 Jenkins 构建。
  - `AC-S8-3.4` — Given Job binding 缺失 When 管理人员触发重试 Then 后端返回 `422 jenkins_job_not_configured`，前端展示可读禁用原因或错误提示。
  - `AC-S8-3.5` — Given 普通成员打开模块页 When 查看触发按钮 Then 失败重试和模块重试不可触发。
- **异常场景**：
  - Job 名环境变量为空 -> 命令不写对应 task type，并输出跳过原因。
  - Jenkins API 不可用 -> 触发接口返回 `503 jenkins_unavailable`，锁不残留。
- **边界值**：
  - 命令可重复执行，重复执行只更新 Job full name、默认重试次数和 active 状态，不重复创建同一唯一键记录。

### F4 Jenkins 任务弹窗筛选与同步入口

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 当前模块 Jenkins 任务弹窗新增状态筛选、日期筛选和任务类型展示。
  - 默认仍查询今天任务；用户可切换日期或状态后查询。
  - 弹窗打开时继续对 `queued/running/canceling` 任务按 P5 规则轮询。
  - 管理人员可触发单任务同步或批量同步入口；若实现为命令而非前端按钮，验收包必须记录命令输出。
- **关联数据表**：`jenkins_task`
- **验收标准**：
  - `AC-S8-4.1` — Given 当前模块存在多种任务 When 打开 Jenkins 任务弹窗 Then 表格展示任务类型、任务名、环境 URL、状态、触发人、开始/结束时间和操作。
  - `AC-S8-4.2` — Given 用户选择状态为 `running` When 查询 Then 弹窗只展示运行中任务。
  - `AC-S8-4.3` — Given 用户选择指定日期 When 查询 Then 弹窗只展示该日期任务。
  - `AC-S8-4.4` — Given 存在 `queued/running/canceling` 任务 When 执行同步入口 Then 后端更新 Jenkins task 状态且不重复创建任务。
  - `AC-S8-4.5` — Given 弹窗关闭 When 存在轮询定时器 Then 前端停止轮询。
- **异常场景**：
  - 日期格式非法 -> `422 validation_error`。
  - Jenkins 同步失败 -> 保留原任务状态，展示错误摘要。

### F5 趋势表沉淀与 7/30 天展示校准

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 每日全量执行完成后，每个模块当天通过率写入 `module_run_history`。
  - 模块重试完成后，以完整模块重跑结果写入 `module_run_history`。
  - 失败重试只更新当前失败数和通过率，不写入趋势表，不更新模块日期和执行时间。
  - 7 天 / 30 天趋势弹窗继续通过 `GET /api/v1/module-snapshots/{snapshot_id}/trend?days=7|30` 获取，不从前端当前列表临时计算。
- **关联数据表**：`module_run_history`
- **验收标准**：
  - `AC-S8-5.1` — Given Daily 全量同步成功 When 查询数据库 Then 当前模块当天存在 `run_type=daily_full` 的 `module_run_history` 记录。
  - `AC-S8-5.2` — Given 模块重试同步成功 When 查询数据库 Then 当前模块存在 `run_type=module_rerun` 的历史记录。
  - `AC-S8-5.3` — Given 失败重试同步成功 When 查询趋势历史 Then 不新增 `failed_rerun` 趋势点，模块日期和执行时间保持不变。
  - `AC-S8-5.4` — Given 当前模块有近 7 天历史 When 点击 7 天趋势 Then 弹窗展示后端返回的 7 天序列。
  - `AC-S8-5.5` — Given 当前模块有近 30 天历史 When 点击 30 天趋势 Then 弹窗展示后端返回的 30 天序列。
- **异常场景**：
  - 趋势接口 days 非 7/30 -> `422 validation_error`。
  - 模块无历史 -> 趋势弹窗空态。

### F6 失败重试直接触发与模块重试确认

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 点击“失败重试”无需二次确认，前端直接调用失败重试接口触发 Jenkins 对应 Job。
  - 失败重试触发后显示提示文案：`开始执行失败重试`。
  - 用例详情弹窗中，勾选失败用例后点击失败重试直接触发选中失败用例重试。
  - 用例详情弹窗中的一键失败重试直接触发全部失败用例重试。
  - 点击“模块重试”必须弹出二次确认，确认文案为：`模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？`
- **关联数据表**：`jenkins_task`、`test_case_result`
- **验收标准**：
  - `AC-S8-6.1` — Given 用户点击失败重试 When 操作触发 Then 前端不弹二次确认，直接调用失败重试接口，并提示“开始执行失败重试”。
  - `AC-S8-6.2` — Given 用户在详情弹窗勾选失败用例或点击一键失败重试 When 后端返回 202 Then 前端刷新 Jenkins 任务状态。
  - `AC-S8-6.3` — Given 用户点击模块重试 When 确认弹窗出现 Then 文案为“模块重试会全量执行当前模块的所有用例，并更新测试时间和执行时间，是否确认重试？”；取消确认不创建 Jenkins 任务，确认后才调用模块重试接口。

---

## §5 状态机定义 [必填（若存在状态流转）]

### 实体：`jenkins_task.status`

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| `queued` | Jenkins 分配 build number | `running` | queue item 可解析 build | 记录 build number 和 Jenkins build URL |
| `queued` / `running` | 用户取消 | `canceling` | 用户有取消权限 | 调用 Jenkins 取消接口，锁暂不释放 |
| `canceling` | 同步确认取消 | `canceled` | Jenkins build 或 queue 已取消 | 释放 `module_execution_lock` |
| `running` | summary passed | `success` | artifact 可读取 | 更新任务、必要时写入快照和趋势 |
| `running` | summary failed | `test_failed` | Jenkins 构建成功但测试失败 | 保存失败 node id，按任务类型刷新统计 |
| `running` | Jenkins 基础设施失败 | `failed` | 构建失败或 artifact 缺失 | 保存错误摘要，释放锁 |

### 实体：`module_run_history`

- `daily_full`：每日全量完整模块执行结果，必须写入趋势。
- `module_rerun`：平台触发的完整模块重跑结果，写入趋势。
- `failed_rerun`：失败用例局部重试，不作为趋势点写入，避免和完整模块质量趋势混淆。

---

## §6 数据表设计 [必填（若涉及持久化）]

> 本阶段优先复用 P3/P5 已有表，不新增重复趋势表。若主人裁决 Q1 为新增表，需回写本节并重新评估迁移。

### 表 `module_run_history`（复用）

- **用途**：模块 7 天 / 30 天趋势的专用历史表，保存每天或完整模块执行后的统计点。
- **写入策略**：Daily 全量和模块重试 upsert/追加；失败重试不写趋势点。
- **关键约束**：建议保持 P3 既有唯一性口径：`environment_id + module_id + run_date + run_type + source_run_id`。

| 字段 | 类型建议 | 必填 | 默认 | 说明 | 索引 / 约束 |
| --- | --- | --- | --- | --- | --- |
| `environment_id` | bigint fk | 是 | | 测试环境 | index |
| `module_id` | bigint fk | 是 | | 测试模块 | index |
| `run_date` | date | 是 | | 趋势日期 | index |
| `run_type` | varchar(32) | 是 | `daily_full` | `daily_full/module_rerun` 为本阶段展示主来源 | index |
| `total_count` / `failed_count` / `passed_count` / `skipped_count` | int | 是 | 0 | 统计值 | |
| `pass_rate` | decimal | 是 | 0 | `(total_count - failed_count) / total_count` | index |
| `duration_seconds` | decimal | 否 | | 完整模块执行耗时 | |

### 表 `jenkins_job_binding`（复用）

- **用途**：环境、模块、任务类型到 Jenkins Job full name 的映射。
- **写入策略**：`sync_jenkins_job_bindings` 幂等 upsert。
- **关键约束**：`environment_id + module_id + task_type` 唯一。

| 字段 | 类型建议 | 必填 | 默认 | 说明 | 索引 / 约束 |
| --- | --- | --- | --- | --- | --- |
| `environment_id` | bigint fk | 是 | | 测试环境 | unique part |
| `module_id` | bigint fk | 是 | | 测试模块 | unique part |
| `task_type` | varchar(32) | 是 | | `daily_full/failed_rerun/module_rerun` | unique part |
| `job_full_name` | varchar(255) | 是 | | Jenkins Job full name | index |
| `is_active` | boolean | 是 | true | 是否启用 | index |

---

## §7 API 契约 [必填（若涉及接口）· 冻结后前后端共同依据]

### `GET /api/v1/module-snapshots`

- **用途 / 权限**：分页查询模块通过率快照；登录用户可读。
- **请求参数**：

| 参数 | 位置 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `environment_id` | query | integer | 是 | 启用环境存在 | 测试环境 |
| `module_name` | query | string | 否 | 逗号分隔，单项 <=128，最多 50 项 | 模块名称精确多选 |
| `package_name` | query | string | 否 | 同上 | 用例包名精确多选 |
| `module_dev` | query | string | 否 | 同上 | 模块开发精确多选 |
| `module_test` | query | string | 否 | 同上 | 模块测试精确多选 |
| `sort` | query | string | 否 | 既有排序字段 | 默认可保持 `pass_rate,-completed_at` |
| `page` / `per_page` | query | integer | 否 | 分页 | 默认 1 / 20 |

- **成功响应**：沿用 P5 `PaginatedModuleSnapshots`。
- **错误码**：

| HTTP | 业务码 | 含义 | 触发条件 |
| --- | --- | --- | --- |
| 401 | `authentication_required` | 未登录 | Cookie 缺失或无效 |
| 422 | `validation_error` | 参数非法 | 多选项过多、字段过长、排序非法 |

- **兼容说明**：`pass_rate_lte` 不作为 Stage8 前端入口；如 Q6 采用推荐方案，后端可继续兼容旧 URL，但 Swagger 和测试主路径不再强调该筛选。

### `GET /api/v1/module-snapshots/filter-options`

- **用途 / 权限**：获取模块通过率筛选下拉选项；登录用户可读。
- **请求参数**：

| 参数 | 位置 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `environment_id` | query | integer | 是 | 启用环境存在 | 按环境聚合选项 |

- **成功响应**：

```json
{
  "data": {
    "module_names": [
      { "label": "示例模块1", "value": "示例模块1", "count": 1 }
    ],
    "package_names": [
      { "label": "test_gbif_case", "value": "test_gbif_case", "count": 1 }
    ],
    "module_devs": [
      { "label": "张三", "value": "张三", "count": 1 }
    ],
    "module_tests": [
      { "label": "王五", "value": "王五", "count": 1 }
    ]
  }
}
```

- **错误码**：`401 authentication_required`、`422 validation_error`。

### `GET /api/v1/module-snapshots/{snapshot_id}/jenkins-tasks`

- **用途 / 权限**：查询当前模块 Jenkins 任务弹窗；登录用户可读。
- **请求参数新增/校准**：

| 参数 | 位置 | 类型 | 必填 | 校验 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `date` | query | string | 否 | `today` 或 `YYYY-MM-DD` | 默认 today |
| `status` | query | string | 否 | Jenkins task 状态枚举 | 状态筛选 |
| `task_type` | query | string | 否 | `daily_full/failed_rerun/module_rerun` | 任务类型筛选 |
| `page` / `per_page` | query | integer | 否 | 分页 | 默认 1 / 20 |

- **成功响应**：分页返回 Jenkins task，字段需包含 `task_type` 和 `job_name`。

### 管理命令：`sync_jenkins_job_bindings`

- **用途 / 权限**：本地、CI 或部署初始化时同步 Jenkins Job binding。
- **输入来源**：
  - `JENKINS_FAILED_RERUN_JOB_NAME`
  - `JENKINS_MODULE_RERUN_JOB_NAME`
  - `JENKINS_DAILY_FULL_JOB_PREFIX`
- **执行要求**：
  - 幂等 upsert。
  - Daily Job full name 使用 `{JENKINS_DAILY_FULL_JOB_PREFIX}-{module.package_name}`，例如前缀为 `AiApiTest-DWP-Daily-Full-Module`、模块包名为 `Species` 时生成 `AiApiTest-DWP-Daily-Full-Module-Species`。
  - 输出创建、更新、跳过数量。
  - 不读取或输出 `JENKINS_USERNAME`、`JENKINS_API_TOKEN` 等敏感值。

---

## §8 UI 字段级规格 [必填（若涉及页面）]

### 页面：模块通过率 `/modules`

| 元素 | 字段来源（对应 §7 API 字段） | 状态枚举 / 标签 | 加载/空/错误/权限态 | 操作与反馈 |
| --- | --- | --- | --- | --- |
| 页面说明 | 本地文案 | 不含筛选描述 | 不适用 | 只说明当前环境模块快照 |
| 测试环境 | `GET /test-environments` | 环境名称 | 加载中禁用 | 切换后刷新筛选选项和列表 |
| 名称筛选 | `filter-options.module_names` | 下拉多选 | 选项加载失败显示空态 | 多选后查询 |
| 包名筛选 | `filter-options.package_names` | 下拉多选 | 同上 | 多选后查询 |
| 模块开发 | `filter-options.module_devs` | 下拉多选 | 同上 | 多选后查询 |
| 模块测试 | `filter-options.module_tests` | 下拉多选 | 同上 | 多选后查询 |
| 重置按钮 | 前端状态 | 主按钮风格，小尺寸 | 筛选提交中禁用 | 位于操作区最左侧，清空多选 |
| 查询按钮 | 前端状态 | 主按钮 | 查询中禁用 | 提交筛选并刷新列表 |
| 表格通过率列 | `row.pass_rate` | 百分比 + 详情入口 | 无数据不展示 | 位于跳过之后，点击打开详情 |
| 后置能力 | `row.actions` / `disabled_reasons` | 失败重试、模块重试、7天趋势、30天趋势、Jenkins 任务 | 按权限、锁、Job binding 禁用 | 触发 DRF API，不直连 Jenkins |

### UI 区域语义拆解与前端实现范围映射

| 区域 | 内容 | 前端处理方式 | 路由 / 组件 | 触发动作 | 不得进入当前 DOM 的内容 |
| --- | --- | --- | --- | --- | --- |
| R1 | 模块通过率页面主体 | 当前页面直接展示 | `/modules` / `ModulesView.vue` | 进入模块页 | 截图红字说明 |
| R2 | 红字编号、红框、箭头 | 仅设计说明不实现 | 无 | 无 | 不进入 DOM、不进截图断言 |
| R3 | 筛选区 | 当前页面直接展示 | `ModulesView.vue` + Element Plus select | 选择筛选、查询、重置 | 旧“上限筛选” |
| R4 | 表格列顺序 | 当前页面直接展示 | `el-table` / 移动端卡片 | 数据加载后渲染 | 旧通过率列位置 |
| R5 | 后置能力按钮 | 当前页面直接展示 | `ReadOnlyActionButtons.vue` | 点击触发趋势/Jenkins/重试 | Jenkins 外部参数页 iframe |
| R6 | Jenkins 任务弹窗 | 弹窗 | `JenkinsTasksDialog.vue` | 点击 Jenkins 任务 | 全局 Jenkins 任务页面 |
| R7 | 7/30 天趋势弹窗 | 弹窗 | `ModuleTrendDialog.vue` | 点击 7天/30天趋势 | 前端临时计算趋势说明 |
| R8 | 失败重试直接触发与模块重试确认 | 提示 / 确认框 | `ModulesView.vue`、`CaseDetailsDialog.vue` | 点击失败重试、勾选失败重试、一键失败重试、模块重试 | 失败重试二次确认弹窗 |

---

## §9 架构影响评估 [必填 · 质量门禁]

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | DRF 负责筛选聚合、Jenkins binding 初始化和同步；Vue 只调用 DRF；Jenkins 继续执行主干。 |
| 数据模型 | 是 | 复用 `module_run_history` 和 `jenkins_job_binding`，可能新增索引或命令写入逻辑；默认不新增趋势重复表。 |
| 权限 | 是 | 触发重试、同步和取消任务继续受 admin/触发人规则限制；普通成员只读。 |
| Jenkins 执行链路 | 是 | 补齐 Job binding 初始化和同步验收，确保平台按钮能触发真实 Jenkins。 |
| `api-test` 执行协议 | 否 | 默认沿用 P5 `summary.json`、`failed_nodeids.json` 和 `RUN_ID` 协议。 |
| 报告 / Allure 协议 | 否/轻微 | 继续复用 P5 Allure/Jenkins 外链；本阶段不复制报告产物。 |
| Docker Compose 部署 | 是 | 命令和服务配置只使用环境变量、Compose 服务名和数据库，不依赖本机路径。 |
| 安全 | 是 | `.env.example` 只保留非敏感 Job 名和 URL 示例；不输出 token；外链仍由后端授权返回。 |

---

## §10 容器化兼容检查 [必填 · 质量门禁]

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 否 | 管理命令读取环境变量和数据库，不读取宿主 Jenkins workspace。 |
| 宿主机固定端口 | 有风险 | `.env.example` 可保留示例端口；实际部署通过根 `.env` 和 Compose 服务名覆盖。 |
| 真实凭据 | 否 | Job binding 命令不得读取或输出 Jenkins 用户名/token；真实凭据仅在本地 `.env` 或私有环境变量。 |
| 不可迁移业务常量 | 有风险 | Job 名通过环境变量生成并入库，不写死在代码；测试数据使用演示名称。 |
| 手工 Jenkins 配置依赖 | 有风险 | P5 已存在 Jenkins Job；本阶段通过 binding 初始化和验收包列出配置检查，后续如需 Job DSL 另走需求。 |

---

## §11 非功能要求 [S可简]

- **性能**：筛选选项 API 在环境范围内聚合，字段建索引；模块列表继续分页，`per_page` 最大 100。
- **安全**：所有 API 需要登录；触发类操作需要 admin；Jenkins URL / Allure URL 由后端可信配置生成。
- **可用性**：筛选选项加载失败不影响基础模块列表错误提示；Jenkins 不可用不影响只读数据。
- **一致性**：URL query、筛选状态、后端筛选条件和 Playwright 断言必须一致；趋势弹窗和表格同源于 `module_run_history`。
- **可观测性**：Job binding 初始化、Jenkins 同步和测试执行证据必须写入验收包。

---

## §12 验收口径汇总 [必填]

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| AC-S8-1.1 | 删除页面筛选描述 | F1 |
| AC-S8-1.2 | 删除上限筛选并新增模块开发筛选 | F1 |
| AC-S8-1.3 | 四个字段为下拉多选 | F1 |
| AC-S8-1.4 | 多选筛选同步 URL 并按后端精确匹配 | F1 |
| AC-S8-1.5 | 重置按钮清空筛选并回到第一页 | F1 |
| AC-S8-2.1 | 通过率列位于跳过之后 | F2 |
| AC-S8-2.2 | 点击通过率仍打开详情弹窗 | F2 |
| AC-S8-2.3 | 移动端通过率位置和布局正确 | F2 |
| AC-S8-3.1 | 失败重试/模块重试 Job binding 可由命令初始化 | F3 |
| AC-S8-3.2 | Daily Job binding 可由命令初始化 | F3 |
| AC-S8-3.3 | Job binding 存在时平台触发 Jenkins 构建 | F3 |
| AC-S8-3.4 | Job binding 缺失时返回可读错误 | F3 |
| AC-S8-3.5 | 普通成员不可触发重试 | F3 |
| AC-S8-4.1 | Jenkins 弹窗展示任务类型等字段 | F4 |
| AC-S8-4.2 | Jenkins 弹窗支持状态筛选 | F4 |
| AC-S8-4.3 | Jenkins 弹窗支持日期筛选 | F4 |
| AC-S8-4.4 | Jenkins 同步入口幂等更新任务 | F4 |
| AC-S8-4.5 | 弹窗关闭停止轮询 | F4 |
| AC-S8-5.1 | Daily 全量写入趋势表 | F5 |
| AC-S8-5.2 | 模块重试写入趋势表 | F5 |
| AC-S8-5.3 | 失败重试不写趋势且不更新日期/执行时间 | F5 |
| AC-S8-5.4 | 7 天趋势来自后端历史表 | F5 |
| AC-S8-5.5 | 30 天趋势来自后端历史表 | F5 |
| AC-S8-6.1 | 失败重试直接触发并提示 | F6 |
| AC-S8-6.2 | 详情失败重试创建 Jenkins 任务并刷新状态 | F6 |
| AC-S8-6.3 | 模块重试必须确认，取消不创建任务 | F6 |

---

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-07-06 | v0.1 | 新建 Stage8 需求草案，基于截图 6 点、P3 趋势表和 P5 Jenkins 执行闭环列出 Q1-Q9 待澄清项 | 进入新需求 loop 的需求分析阶段 |
| 2026-07-06 | v1.0 | 回写主人对 Q1-Q9 的全部裁决，文档状态改为已冻结，API 契约和冻结门禁闭环 | 主人确认 Q1-Q9；Q9 当时采用失败重试二次确认，后续已由 v1.0.2 覆盖 |
| 2026-07-06 | v1.0.1 | 补充 Daily Job binding 命名规则为 `{JENKINS_DAILY_FULL_JOB_PREFIX}-{module.package_name}` | Phase 3 测试用例要求 AC-S8-3.2 可断言，规则沿用 `.env.example` 与 P5 既有示例 |
| 2026-07-07 | v1.0.2 | 回写主人 Phase 4 方案选择：所有待选方案采用方案 A；失败重试取消二次确认，直接触发 Jenkins 并提示“开始执行失败重试”；模块重试保留确认弹窗及固定文案 | 主人明确调整失败重试/模块重试交互口径 |

---

## §14 冻结确认（主人签字门禁）

冻结前逐项核对：

- [x] §0 待澄清清单全部闭环（无“待确认”状态）
- [x] §9 架构影响评估已完成
- [x] §7 API 契约完整、可冻结（前端将据此开发）
- [x] §10 容器化兼容检查通过
- [x] §4 每个功能点都有可测的 Given-When-Then 验收标准

**冻结人（主人）**：`主人（对话确认 Q1-Q9 裁决）`　　**冻结日期**：`2026-07-06`

> 冻结后，下游“功能测试用例 -> UI 原型 -> 后端 TDD -> 前端 TDD”按根 `AGENTS.md` 自动衔接推进；过程中如撞到本文未覆盖的关键决策，必须暂停上报主人并回写 §0 与 §13，严禁脑补。
