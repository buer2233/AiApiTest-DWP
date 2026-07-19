# Stage13-Daily-Full-Module-单一流水线编排-测试用例

## 文档信息

- **需求来源**：`../../demand/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-需求说明.md`，已于 2026-07-19 冻结。
- **覆盖范围**：单一 Daily 父流水线、父任务与报告聚合、环境目录 MySQL/YAML 双向同步、受控迁移。
- **测试层次**：Jenkins Pipeline/Job DSL 静态与集成测试、`api-test` 契约测试、后端 API/同步任务测试、前端组件与 Playwright 测试；不使用真实环境、凭据或运行产物。
- **通用脱敏数据**：`env_key=stage13-qa`、`base_url=https://stage13-qa.example.invalid/api`、`url_name=Stage13 QA`、`url_desc=自动化回归测试环境`；所有 Git、Jenkins 与服务令牌均以 `<PRIVATE_...>` 占位，不写入日志断言。
- **优先级**：P0 为发布阻断，P1 为高风险回归，P2 为一般回归。

## F1 单一 Daily 父流水线（P0）

### TC-S13-F1-001：唯一父 Job 的定时器与 Worker Job 拓扑

- **关联 AC**：AC1.1
- **测试目标**：确认只有唯一 Daily 父 Job 被每日定时调度，Worker 仅由父 Job 触发。
- **优先级**：P0
- **前置条件**：使用隔离 Jenkins 测试实例完成版本化 init Groovy 初始化；保留旧分模块 Daily Job 作为迁移前基线。
- **脱敏测试数据**：父 Job 名 `AiApiTest-DWP-Daily-Full-Module`；模块 fixture 为 `module-alpha`、`module-beta`。
- **操作步骤**：
  1. 执行 Jenkins Job 初始化/修复流程。
  2. 查询全部 Daily 父、Daily Worker 和旧分模块 Daily Job 的 Job 配置、定时器与上游触发器。
  3. 手动构建唯一父 Job，并读取本次产生的 Worker 构建原因。
- **可观察预期**：
  - 仅父 Job 配置 `0 2 * * *`；Daily Worker 无 cron/timer，且无按模块新建的 Daily 定时 Job。
  - Worker 的上游原因为本次父构建，不能独立被定时调度。
  - 初始化幂等执行后 Job 数量、名称和定时器不重复、不漂移；旧 Job 未被删除，符合 AC4.1 的迁移前约束。
- **备注**：断言 Job XML/DSL 与 Jenkins 查询结果，不依赖具体 Jenkins 公网地址或执行器编号。

### TC-S13-F1-002：三类 Pipeline 独立十并发并排队

- **关联 AC**：AC1.2
- **测试目标**：验证 Daily、模块重试、失败重试分别具有独立的最大 10 个 Job 并发额度。
- **优先级**：P0
- **前置条件**：Jenkins 测试 executor 容量不少于 30；三类 Job 已绑定不同限流分类；Worker 使用可控阻塞 fixture，完成后可人工放行。
- **脱敏测试数据**：每个类别各提交 12 个构建请求；模块名使用 `module-01` 至 `module-12`；目标 URL 使用通用脱敏 URL。
- **操作步骤**：
  1. 并发触发 12 个 Daily Worker、12 个模块重试 Job、12 个失败重试 Job。
  2. 在所有阻塞 fixture 尚未放行时，分别采集三类 Job 的运行中和排队数量。
  3. 放行任一 Daily Worker，观察队首 Daily Worker；再分别放行一条模块重试与失败重试构建。
- **可观察预期**：
  - 每一类别恰有 10 个运行中构建、2 个处于 Jenkins 队列；类别间可同时达到 10 个，系统总运行数可为 30。
  - 第 11、12 个仅因自身类别达到配额而排队，不被另一类别的运行数拒绝或错误阻塞。
  - 放行后只唤醒同类别队首任务；Jenkins 队列原因可观察且指向所属限流分类。
- **备注**：此用例验证上限边界和队列语义，不以操作系统进程数量代替 Jenkins Job 并发数。

### TC-S13-F1-003：单模块测试失败仍完成全量执行并使父任务失败

- **关联 AC**：AC1.3
- **测试目标**：验证测试失败不短路其余模块，父构建在汇总和 Allure 归档后才标记失败。
- **优先级**：P0
- **前置条件**：父 Job 与三个 Worker 可用；`module-beta` fixture 返回确定的测试失败，其他模块成功；聚合与归档 fixture 可用。
- **脱敏测试数据**：模块顺序 `module-alpha`、`module-beta`、`module-gamma`；失败 node id 使用 `tests/test_placeholder.py::test_expected_failure`。
- **操作步骤**：
  1. 触发一次 Daily 父构建并等待 `module-beta` 失败。
  2. 在其失败后检查 `module-alpha`、`module-gamma` 的调度和完成状态。
  3. 等待父 Job 汇总模块明细、生成聚合 Allure 并归档。
- **可观察预期**：
  - 三个 Worker 均被调度且都有终态，`module-beta` 的失败不会取消或跳过其余模块。
  - 父目录存在完整摘要和聚合 Allure；摘要明确标注失败模块与成功模块。
  - 所有 Worker 和聚合阶段结束后父构建才为 `FAILURE`/`test_failed`，而不是在第一项失败时提前结束。
- **备注**：覆盖 Daily 状态机 `running -> test_failed`；基础设施失败场景由 TC-S13-F1-007 覆盖。

### TC-S13-F1-004：默认与参数覆盖 URL 均执行全量模块

- **关联 AC**：AC1.4
- **测试目标**：验证默认目标 URL 与已登记覆盖 URL 使用同一全量模块集合，且覆盖值沿用 `--base-url` 校验。
- **优先级**：P0
- **前置条件**：环境 YAML 有两个已同步且启用的环境；私有默认 URL 指向第一个环境；模块 YAML 含至少三个活跃模块。
- **脱敏测试数据**：默认 URL `<DEFAULT_BASE_URL>`；覆盖 URL `https://stage13-qa.example.invalid/api/`；模块 `module-alpha`、`module-beta`、`module-gamma`。
- **操作步骤**：
  1. 不传 `TARGET_BASE_URL` 构建父 Job，读取预检输出和调度清单。
  2. 传入带尾斜杠的已登记 `TARGET_BASE_URL` 再构建，读取标准化后的目标和调度清单。
  3. 对比两次构建的模块集合和 Worker 参数。
- **可观察预期**：
  - 空参数解析为当前私有默认 URL；覆盖 URL 经既有 `--base-url` 规则规范化后精确匹配环境 YAML。
  - 两次均调度模块 YAML 的全部模块，数量与集合一致；不支持模块子集参数，也不因 URL 覆盖变更模块清单。
  - 构建摘要记录脱敏的环境标识，不输出私有默认 URL 或任何凭据。
- **备注**：默认 URL 仅在私有配置提供；测试日志使用环境 key/占位符断言。

### TC-S13-F1-005：Daily 预检拒绝无效模块、环境和未登记 URL

- **关联 AC**：AC1.5
- **测试目标**：覆盖模块/环境 YAML 空、格式错误、URL 未登记和环境未同步四类调度前失败。
- **优先级**：P0
- **前置条件**：可逐一装载测试专用 YAML fixture；数据库中可构造启用但未同步的 `TestEnvironment`；观察器可读取 Worker 触发、任务、快照写入记录。
- **脱敏测试数据**：空清单、缩进错误 YAML、未知 `env_key`、`https://unregistered.example.invalid/api`、状态为 `pending` 的环境投影。
- **操作步骤**：
  1. 分别以四类无效 fixture 启动父 Job。
  2. 对每次构建采集预检结构化诊断、Worker 触发记录、Daily `JenkinsTask`/`TestRun` 创建记录和模块快照更新时间。
  3. 将 YAML 恢复为合法且已同步状态后再次启动，确认失败不会污染下一次运行。
- **可观察预期**：
  - 每个无效输入均在调度任何 Worker 前终止，诊断包含稳定的类别、脱敏原因和修复建议。
  - 无 Worker 构建、无新的 Daily 父任务/TestRun、无模块快照或趋势更新；不存在部分调度。
  - 恢复后合法构建可正常进入 `queued -> running`，说明预检失败没有残留锁或半状态。
- **备注**：不冻结需求未命名的具体错误码，只断言结构、可区分性和无副作用。

### TC-S13-F1-006：Daily 取消状态不创建模块子任务

- **关联 AC**：AC1.3、AC2.1
- **测试目标**：验证父构建在排队和运行中取消时遵循状态机，且不产生平台模块子任务。
- **优先级**：P1
- **前置条件**：一条父 Job 可保持 `queued`，另一条已触发至少一个阻塞 Worker；后端同步可见。
- **脱敏测试数据**：模块 `module-alpha`、`module-beta`；取消操作者 `admin-test-user`。
- **操作步骤**：
  1. 在预检前取消一条队列中的父构建，等待 Jenkins 返回取消结果。
  2. 在另一父构建已有 Worker 运行时取消，等待 Worker 和父构建达到终态。
  3. 同步后查询父 `JenkinsTask`、`TestRun` 与任务列表。
- **可观察预期**：
  - 两条构建均只经历 `queued/running -> canceling -> canceled` 的合法转换，并保存可观察取消诊断。
  - 不创建 Daily 模块子 `JenkinsTask`；已完成模块结果不会被伪造为通过。
  - 未开始模块不会被当作已执行统计；列表仅呈现一条对应父任务。
- **备注**：取消后的归档/同步行为应按实际已产出内容呈现，不能冒充成功 Allure。

### TC-S13-F1-007：Worker、聚合或归档基础设施故障的父任务诊断

- **关联 AC**：AC1.3、AC1.5、AC2.2
- **测试目标**：验证 Worker 异常、聚合失败、归档失败均有结构化诊断并保留可用模块结果。
- **优先级**：P1
- **前置条件**：以受控 stub 分别注入 Worker 启动异常、聚合输入不可读、Allure 归档异常；不操作真实 Docker 服务或主机目录。
- **脱敏测试数据**：相对工作区路径 `daily-runs/<run-id>/`；模拟异常 `<WORKER_UNAVAILABLE>`、`<AGGREGATION_ERROR>`、`<ARCHIVE_ERROR>`。
- **操作步骤**：
  1. 对三种异常分别运行父 Job。
  2. 检查父 Job 是否继续等待仍可调度的模块，并读取摘要、Jenkins 控制台与后端任务诊断。
  3. 审核 Pipeline 脚本的工作区路径、环境变量引用和归档规则。
- **可观察预期**：
  - 父构建为 `failed`，错误可区分且脱敏；已完成模块的摘要与后端快照仍可同步。
  - Worker/聚合/归档异常不得被误报为测试失败，也不得掩盖其他模块成功或失败结果。
  - Pipeline 仅使用 Jenkins workspace 相对路径、服务变量和 Credentials 注入；不包含本机绝对路径、宿主机固定端口、真实凭据或直接 Docker Compose 应用管理命令。
- **备注**：覆盖 Jenkins/Docker 协议兼容性；环境启动和服务管理仍只走固定环境 Job。

## F2 父任务、模块快照与报告聚合（P0）

### TC-S13-F2-001：一次 Daily 构建只同步一条父任务与空模块 TestRun

- **关联 AC**：AC2.1
- **测试目标**：验证后端数据模型将多模块 Daily 运行投影为唯一父任务，而不是模块子任务。
- **优先级**：P0
- **前置条件**：合法环境和三个模块的 Daily 构建已完成；后端 Jenkins 同步任务可执行。
- **脱敏测试数据**：`job_type=daily_full`、环境 `stage13-qa`、模块 `module-alpha/module-beta/module-gamma`。
- **操作步骤**：
  1. 同步同一父构建两次，查询该 job/build 对应的 `JenkinsTask` 与 `TestRun`。
  2. 按父构建编号、模块为空/非空、任务类型过滤任务列表。
  3. 比对模块 Worker 的 Jenkins 原始构建与平台任务数量。
- **可观察预期**：
  - 仅一条 `daily_full` `JenkinsTask`，其 `module` 为空且环境非空；仅一条对应 module 为空的 `TestRun`。
  - 不创建 Daily 模块子任务，也不将 Worker 原始构建投影为平台任务；重复同步幂等。
  - 重试类型绑定仍要求环境和模块，未因 Daily 可空模型而放宽。
- **备注**：数据层和 API 列表均应证实这一不变量。

### TC-S13-F2-002：父运行目录聚合稳定摘要与唯一 Allure 入口

- **关联 AC**：AC2.2
- **测试目标**：验证父 Job 的目录协议、模块明细和前端报告入口范围。
- **优先级**：P0
- **前置条件**：所有 Worker 成功并写出可读取的测试结果与 Allure 原始结果。
- **脱敏测试数据**：父运行标识 `<daily-parent-run-id>`；相对目录 `daily-runs/<daily-parent-run-id>/`；三份模块结果 fixture。
- **操作步骤**：
  1. 执行 Daily 父构建并下载其构建归档清单。
  2. 检查 `summary.json` schema、模块明细数、合并后的 Allure 原始结果位置和唯一报告链接。
  3. 以登录用户打开任务列表和环境页面，检查报告入口与 DOM。
- **可观察预期**：
  - 父目录存在稳定可解析的 `summary.json`、全部模块明细和合并 Allure 原始结果；路径按父运行标识隔离，不互相覆盖。
  - Jenkins/平台仅为父任务发布一个 Allure 入口；模块明细保留为父构建归档而不作为独立平台报告链接。
  - 页面不渲染模块子任务、模块级 Allure 入口或不存在的 Daily 平台触发按钮。
- **备注**：前端断言应在后续 UI 区域映射冻结后落为 Playwright 用例。

### TC-S13-F2-003：按模块摘要同步快照、失败用例与趋势并隔离解析失败

- **关联 AC**：AC2.3
- **测试目标**：验证单模块解析失败不会覆盖其他模块的已完成快照或趋势。
- **优先级**：P0
- **前置条件**：目标环境已有三个模块的历史快照；聚合摘要中两个模块有效、一个模块明细损坏。
- **脱敏测试数据**：`module-alpha=passed`、`module-beta=failed`、`module-gamma=<malformed-detail>`；历史快照日期使用 `<prior-date>`。
- **操作步骤**：
  1. 将该摘要回传/同步至后端。
  2. 查询三模块的最新快照、失败用例、运行历史和父任务诊断。
  3. 再次同步同一摘要，核对计数与趋势是否重复累加。
- **可观察预期**：
  - `module-alpha`、`module-beta` 均按摘要更新快照、失败用例和趋势；`module-gamma` 保留可追溯解析错误，不以伪造数据覆盖历史。
  - 父任务包含解析失败诊断并为失败；有效模块结果不被掩盖。
  - 重复同步幂等，不重复创建历史或失败用例记录。
- **备注**：需覆盖 `passed/failed/skipped/not_displayed` 的既有统计规则，未展示状态不得被错误计入失败。

### TC-S13-F2-004：父摘要缺失或重复模块键的同步拒绝与数据保全

- **关联 AC**：AC2.2、AC2.3
- **测试目标**：验证聚合协议的边界校验和同步原子性。
- **优先级**：P1
- **前置条件**：存在已完成模块的基线快照；可提供缺失 `summary.json`、重复模块键和未知模块 fixture。
- **脱敏测试数据**：`summary.json=<missing>`、模块键 `module-alpha` 重复、未知键 `module-unknown`。
- **操作步骤**：
  1. 分别同步三类非法父归档。
  2. 读取父任务错误、模块快照和趋势变更记录。
  3. 以合法完整摘要再次同步作为恢复验证。
- **可观察预期**：
  - 非法父归档产生明确、脱敏的父任务诊断，不生成模块子任务，不进行不完整的模块覆盖更新。
  - 基线快照、趋势和失败用例保持一致；没有半写入或重复计数。
  - 合法摘要可被后续正常处理，说明失败未占用同步状态。
- **备注**：错误码以冻结契约为准；未命名错误仅断言可区分诊断。

## F3 测试环境目录双向同步（P0）

### TC-S13-F3-001：环境 YAML 合法 schema、去尾斜杠和稳定序列化

- **关联 AC**：AC3.1
- **测试目标**：验证合法环境目录解析、URL 规范化和确定性 YAML 输出。
- **优先级**：P0
- **前置条件**：环境 YAML 解析与导出单元测试环境可用。
- **脱敏测试数据**：两个无序 key 的环境，`base_url=https://stage13-qa.example.invalid/api/`、`url_name=Stage13 QA`、`url_desc=自动化回归测试环境`。
- **操作步骤**：
  1. 解析包含两个合法环境、一个 URL 带尾斜杠的 YAML。
  2. 导出规范化后的 YAML 两次并比对字节内容、编码、缩进、末尾换行与 key 顺序。
  3. 检查得到的环境投影值。
- **可观察预期**：
  - 顶层 key 映射为唯一 `env_key`，`base_url` 去除尾斜杠，名称和描述完整保留。
  - 两次导出内容完全一致，使用 UTF-8、两空格缩进、确定性 key 排序和末尾换行。
  - YAML 中仅有 `base_url`、`url_name`、`url_desc` 三项必填配置，不写入数据库 id、凭据或内部状态。
- **备注**：校验 Git blob SHA 基于该 YAML 文件内容，而非仓库 HEAD。

### TC-S13-F3-002：环境 YAML 非法输入拒绝矩阵

- **关联 AC**：AC3.1
- **测试目标**：验证所有 schema 与 URL 唯一性边界被拒绝且无持久化副作用。
- **优先级**：P0
- **前置条件**：空数据库或可回滚测试事务；读取 YAML/数据库状态的观察器可用。
- **脱敏测试数据**：空 YAML、重复 URL、空 `url_name`、`base_url=stage13-qa.example.invalid`、`base_url=https:///api`、缺少 `url_desc`、未知字段 `secret_hint`、非映射顶层值。
- **操作步骤**：
  1. 逐个载入非法 fixture，并记录解析/API 返回。
  2. 查询 `TestEnvironment`、目录状态和同步请求数量。
  3. 紧接着载入一份合法 YAML 验证恢复能力。
- **可观察预期**：
  - 每个 fixture 以字段级、脱敏的 `validation_error` 被拒绝；重复 key/URL、无协议或域名、空名、缺字段和未知字段不可通过。
  - 不创建/更新环境、目录状态或同步审计，不产生部分 YAML 导出。
  - 合法 YAML 仍可成功处理，失败不残留全局锁。
- **备注**：URL 比较应采用去尾斜杠后的规范化值。

### TC-S13-F3-003：admin 新增环境先提交 MySQL 再创建同步请求

- **关联 AC**：AC3.2
- **测试目标**：验证新增 API 的事务、响应契约与异步写回边界。
- **优先级**：P0
- **前置条件**：以 admin Cookie JWT 登录；没有活动的环境同步请求；Jenkins 回调尚未执行。
- **脱敏测试数据**：`env_key=stage13-qa`、`url_name=Stage13 QA`、`base_url=https://stage13-qa.example.invalid/api/`、`url_desc=自动化回归测试环境`。
- **操作步骤**：
  1. 调用 `POST /api/v1/test-environments` 并保存响应。
  2. 在同步 Job 开始前查询环境、`EnvironmentCatalogState` 与 `EnvironmentCatalogSyncAttempt`。
  3. 读取同步请求的方向、冻结 payload 摘要、请求人和状态。
- **可观察预期**：
  - 返回 `202`，成功体为 `{ "data": ... }`，环境已在 MySQL 中以规范化 URL 创建，并有唯一 `mysql_to_yaml` 请求。
  - 环境和同步请求在同一事务可见；请求状态为 `pending`，目录状态相应更新，尚未假称 YAML 已写回。
  - 审计含请求人、非敏感 payload 摘要和创建时间，不含 Cookie、Git Token 或真实内部地址。
- **备注**：写入应只触发受控 Jenkins 配置同步 Job，后端容器不得直接改工作区 YAML。

### TC-S13-F3-004：admin 编辑、停用、恢复及 API 校验边界

- **关联 AC**：AC3.2
- **测试目标**：验证环境生命周期、不可改 key、重复约束和活动同步互斥。
- **优先级**：P0
- **前置条件**：存在两个启用环境与一条可关闭/可设置活动状态的同步请求；以 admin 登录。
- **脱敏测试数据**：原 key `stage13-qa`；新名称 `Stage13 QA v2`；重复 URL `https://stage13-other.example.invalid/api`；非法 body `env_key=renamed-key`。
- **操作步骤**：
  1. PATCH 名称、URL、描述并检查 `202` 与新同步请求。
  2. PATCH 尝试改 `env_key`，以及创建/修改为重复 URL。
  3. DELETE 环境后检查历史关联、导出候选清单；再 PATCH `is_active=true` 恢复。
  4. 在 `pending/queued/running` 请求存在时分别新增、编辑、导入和重试。
- **可观察预期**：
  - 合法编辑、停用和恢复均在单一事务更新环境并创建一条 `mysql_to_yaml` 请求；`env_key` 创建后不可改。
  - 改 key、重复 key/URL 或非法字段返回 `400 validation_error` 或 `409 duplicate_environment`，无数据变更。
  - DELETE 为逻辑停用，保留任务/快照/趋势历史并从后续 YAML 导出移除；恢复回到 active。
  - 活动请求期间所有新写入返回 `409 environment_config_sync_busy`，不重排异步写入。
- **备注**：同时验证 `active -> inactive -> active` 状态机和不物理删除约束。

### TC-S13-F3-005：MySQL 到 YAML 同步的隔离 checkout、快进推送与状态回写

- **关联 AC**：AC3.3
- **测试目标**：验证配置同步 Job 的安全工作区、SHA 守卫、确定性写回和成功审计。
- **优先级**：P0
- **前置条件**：存在 `pending` 的 `mysql_to_yaml` 请求与匹配期望 blob SHA；测试 Git 远端允许快进推送；Jenkins Credentials 使用占位测试凭据。
- **脱敏测试数据**：期望 SHA `<expected-yaml-blob-sha>`、提交说明 `chore: sync test environments`、隔离路径 `workspace/<job>/<build>/checkout`。
- **操作步骤**：
  1. 触发专用环境配置同步 Job，记录 queue id、build number 和 checkout 位置。
  2. 检查 Job 对预期 blob SHA 的比较、规范化 YAML 生成和 Git diff。
  3. 等待快进推送与后端回调完成，查询目录状态和同步审计。
- **可观察预期**：
  - Job 仅在干净、隔离 SCM checkout 操作，使用相对 workspace；不访问 MySQL、不执行 pytest、不写 `LOCAL_WORKSPACE_REPO` 或宿主机挂载目录。
  - SHA 匹配时生成确定性 YAML，自动提交并快进推送受控主干；审计保存 job/build、commit SHA、实际 blob SHA 和结束时间。
  - 目录和请求最终均为 `synced`，`last_synced_at`/`last_commit_sha` 可查询；日志不泄露 Credentials。
  - Job 参数不携带导出或回调 URL；内部端点只由私有服务基址和已校验请求 ID 构造。独立 Git push 用户名/密码凭据仅作用于静默 fetch/push，不写入 remote、Git 配置或日志。
- **备注**：自动提交是冻结决策；Git 身份与凭据只从私有 Jenkins Credentials/环境变量获取。

### TC-S13-F3-006：同步 Job 非快进、不可用或凭据失败时不半写入

- **关联 AC**：AC3.3、AC3.5
- **测试目标**：验证 Git 拉取、提交、推送与 Jenkins 调度失败的失败边界和可重试性。
- **优先级**：P0
- **前置条件**：已提交 MySQL CRUD 与 `pending` 请求；分别可模拟 Jenkins 不可用、Git 非快进、提交失败和推送失败，不接触真实远端。
- **脱敏测试数据**：`<JENKINS_UNAVAILABLE>`、`<NON_FAST_FORWARD>`、`<GIT_PUSH_FAILED>`、`<REDACTED_CREDENTIAL_ERROR>`。
- **操作步骤**：
  1. 分别注入上述失败并运行/提交同步请求。
  2. 查询 MySQL 环境字段、YAML/远端 commit、目录状态、错误摘要与 retry 入口。
  3. 消除故障后调用 retry，核对产生新请求而非复用旧审计。
- **可观察预期**：
  - MySQL 已提交的 CRUD 不回滚，远端 YAML/commit 不发生部分更新；目录/请求为 `failed` 或保留 `pending`，并有脱敏可观察诊断。
  - 失败请求不阻塞管理员查看状态；可重试时重试接口创建新的不可变请求并最终可 `synced`。
  - 输出中不包含 Git URL 中的凭据、Token、Cookie 或宿主机绝对路径。
  - 非法同步方向、包含 shell 元字符的请求 ID 或非 40 位小写十六进制 SHA 在任何 curl、YAML 写入、Git 提交或 push 前明确失败。
- **备注**：只验证受控测试远端；不对主人基础设施执行破坏性 Git/Docker 操作。

### TC-S13-F3-007：YAML 导入原子新增、更新和停用缺失环境

- **关联 AC**：AC3.4
- **测试目标**：验证手工 YAML 修改通过页面导入后正确投影至 MySQL 并保留历史。
- **优先级**：P0
- **前置条件**：MySQL 中有 `env-keep`、`env-update`、`env-retire` 三项及 `env-retire` 历史快照；隔离 checkout YAML 已手工改为只含前两项和新 `env-new`；admin 登录。
- **脱敏测试数据**：`env-update.base_url=https://updated.example.invalid/api`；`env-new.base_url=https://new.example.invalid/api`；`env-retire` 不在 YAML 中。
- **操作步骤**：
  1. 调用 `POST /api/v1/test-environments/sync-from-yaml`。
  2. 等待 Jenkins Job 读取隔离 checkout、校验 YAML 并回调后端。
  3. 查询各环境、`env-retire` 历史关联、目录状态与审计。
- **可观察预期**：
  - 返回 `202` 的 `yaml_to_mysql` 请求；完成后新增 `env-new`、更新 `env-update`、保持 `env-keep`，将缺失的 `env-retire` 逻辑停用。
  - 所有导入投影在单一事务完成；`env-retire` 的历史任务、快照和趋势仍可查询。
  - 目录记录新的 YAML blob SHA 和 `synced` 状态，且导入过程不自动覆写手工 YAML。
- **备注**：运行时手工变更只经页面触发 Jenkins 导入，后端容器不直接读取宿主机文件。

### TC-S13-F3-008：YAML 导入校验失败不改变 MySQL 并支持重试

- **关联 AC**：AC3.4、AC3.5
- **测试目标**：验证导入失败的事务原子性和状态反馈。
- **优先级**：P0
- **前置条件**：环境表有可比较的基线；隔离 checkout 中可替换为 TC-S13-F3-002 的非法 YAML；admin 登录。
- **脱敏测试数据**：缺 `url_desc` 的 `env-invalid`、重复 URL、未知字段 `secret_hint`。
- **操作步骤**：
  1. 发起 YAML 导入并等待 Job 回调失败。
  2. 比对导入前后 MySQL 环境列表、启停状态、历史关联和目录状态。
  3. 将 YAML 修正为合法版本后发起新的导入/重试。
- **可观察预期**：
  - 请求状态为 `failed` 并记录字段级脱敏错误；环境表不新增、更新或停用任何项目，目录无错误 blob SHA 覆盖。
  - 页面/API 能查看失败状态与 Jenkins 链接，允许按状态机创建新的可重试请求。
  - 合法导入后才一次性应用全部变更，无残留半导入。
- **备注**：`failed` 不等于 `conflict`；前端需显示不同的可执行操作。

### TC-S13-F3-009：YAML blob SHA 冲突拒绝自动覆盖

- **关联 AC**：AC3.6
- **测试目标**：验证并发手工修改与平台写回的冲突保护。
- **优先级**：P0
- **前置条件**：存在持有 `<expected-yaml-blob-sha>` 的 `mysql_to_yaml` 请求；在 Job 写入前由另一提交改变 YAML blob。
- **脱敏测试数据**：期望 SHA `<sha-a>`、观测 SHA `<sha-b>`、环境 key `stage13-qa`。
- **操作步骤**：
  1. 启动同步 Job 并在 SHA 校验前模拟受控主干的 YAML 内容变更。
  2. 等待 Job 读取观测 SHA 并完成回调。
  3. 检查 Git 提交数、YAML 内容、目录状态、页面提示与 retry 行为。
- **可观察预期**：
  - 请求和目录状态为 `conflict`，保存预期/观测 blob SHA；不改 YAML、不创建 Git 提交、不推送。
  - 页面仅引导“先导入 YAML”或“重新提交平台修改”；直接 retry 返回 `409 sync_not_retryable`。
  - 完成 YAML 导入或重新编辑后才可创建新的 `pending` 请求。
- **备注**：禁止使用仓库 HEAD SHA 替代文件 Git blob SHA。

### TC-S13-F3-010：环境同步请求全状态机、串行与幂等边界

- **关联 AC**：AC3.2、AC3.3、AC3.4、AC3.5、AC3.6
- **测试目标**：验证 `pending -> queued -> running -> synced/failed/conflict` 合法流转、全局串行和终态重试。
- **优先级**：P1
- **前置条件**：admin、Jenkins 同步 Job 和状态查询接口可用；测试可暂停 Job 各阶段。
- **脱敏测试数据**：两个连续 CRUD 请求 `request-a/request-b`；同步状态 `pending/queued/running/synced/failed/conflict`。
- **操作步骤**：
  1. 发起 `request-a`，依次观察 Jenkins 接受、开始、成功回调三个事件。
  2. 在 `pending`、`queued`、`running` 三个时点分别发起 `request-b`、导入和 retry。
  3. 分别让新请求成功、失败和冲突，观察是否只能按规定从终态创建新请求。
- **可观察预期**：
  - 状态只按冻结状态机前进，记录 queue id、build number、Jenkins 链接和完成时间；不存在跳过 `queued/running` 的假成功。
  - 任一非终态期间新增/导入/重试均为 `409 environment_config_sync_busy`，系统始终至多一个活动请求。
  - `failed` 可重试；`conflict` 必须先导入 YAML 或重新提交；成功回调重复投递不重复写入或重复提交。
- **备注**：状态查询结果必须为脱敏数据，不能以控制台日志代替 API 状态。

### TC-S13-F3-011：member 环境页面与写接口权限隔离

- **关联 AC**：AC3.7
- **测试目标**：验证 member 只读范围和 admin 管理范围一致。
- **优先级**：P0
- **前置条件**：存在一个启用、一个停用环境及同步审计；分别以 admin 和 member Cookie JWT 登录。
- **脱敏测试数据**：member `member-test-user`；admin `admin-test-user`；环境 `stage13-qa`。
- **操作步骤**：
  1. member 请求环境列表、创建/编辑/删除/导入/重试接口，并打开 `/environments`。
  2. admin 打开相同页面及同步状态详情。
  3. 检查页面 DOM、键盘可达操作与网络请求。
- **可观察预期**：
  - member 只能查看启用环境、快照和既有父任务/报告；所有环境写接口和同步审计/retry 返回 `403 admin_required`。
  - member 页面不渲染新增、编辑、停用、恢复、导入、冲突处理或重试控件，不能通过前端隐藏元素绕过 API。
  - admin 可看到管理表、目录状态、脱敏错误及对应操作；停用环境的可见性遵循已冻结权限/筛选契约。
- **备注**：前端测试需同时断言 DOM 不存在和 API 403，避免仅做视觉隐藏。

### TC-S13-F3-012：首次环境初始化读取镜像内 YAML 而非硬编码种子

- **关联 AC**：AC3.8
- **测试目标**：验证初始投影来源、幂等性和运行时变更边界。
- **优先级**：P0
- **前置条件**：空测试数据库；构建输入含随镜像复制的合法 `package_environment.yaml`；可替换为第二份 fixture。
- **脱敏测试数据**：初始环境 `bootstrap-qa`，URL `https://bootstrap-qa.example.invalid/api`；第二份运行时 YAML 含 `runtime-new`。
- **操作步骤**：
  1. 执行首次环境初始化并查询环境投影来源和数据。
  2. 再执行一次初始化，检查唯一性和审计。
  3. 修改隔离 checkout 的运行时 YAML 后，不点击页面导入，观察后端；随后由 admin 发起导入。
- **可观察预期**：
  - 初始环境完全由镜像内 YAML 建立，`seed_environment` 不再包含硬编码环境；重复初始化不产生重复 key/URL。
  - 运行时手工 YAML 变化不会被后端容器直接读取、写入或自动导入。
  - 页面发起的 Jenkins 导入成功后，`runtime-new` 才进入 MySQL 投影。
- **备注**：镜像构建、服务启停和依赖安装均不由本测试直接操作，环境验收只走固定 Jenkins 环境 Job。

### TC-S13-F3-013：环境列表、同步状态和尝试详情 API 契约

- **关联 AC**：AC3.2、AC3.5、AC3.7
- **测试目标**：验证浏览器 API 的响应封装、筛选、404 和权限错误语义。
- **优先级**：P1
- **前置条件**：存在启用/停用环境以及成功、失败同步审计；admin 与 member 会话可用。
- **脱敏测试数据**：`is_active=true`、`is_active=false`、未知 id `<missing-id>`、同步 attempt `<attempt-id>`。
- **操作步骤**：
  1. 使用登录用户请求 `GET /api/v1/test-environments`，分别传入两个筛选值和非法筛选值。
  2. 使用 admin 查询 `GET /api/v1/environment-catalog-sync-attempts/{id}`，再查询未知 id；使用 member 重复查询。
  3. 检查所有成功体、错误体和字段脱敏情况。
- **可观察预期**：
  - 列表返回 `{ "data": ... }`，正确包含筛选后的环境及当前目录状态；未登录请求为 `401`。
  - admin 可读取本次请求状态、错误、Jenkins 追溯和 commit 摘要；未知资源为 `404`；member 访问管理审计为 `403 admin_required`。
  - 错误体统一使用既有 `api_error_response`，不会暴露服务令牌、Git 凭据、私有 URL 或绝对工作区路径。
- **备注**：分页/排序若由既有列表基础设施提供，实施时应保持原契约并补相应测试。

### TC-S13-F3-014：环境管理页面的表单、状态反馈和冲突操作范围

- **关联 AC**：AC3.2、AC3.5、AC3.6、AC3.7
- **测试目标**：验证 `/environments` 的管理 UX 与冻结的 R1-R4 范围一致。
- **优先级**：P1
- **前置条件**：已冻结 UI 映射；admin 下有 `pending`、`running`、`failed`、`conflict` 审计 fixture，member 会话可用。
- **脱敏测试数据**：表单 `env_key=stage13-qa`、URL `https://stage13-qa.example.invalid/api`；错误 `<validation_error>`、`<conflict>`。
- **操作步骤**：
  1. admin 依次新增、编辑、停用/恢复环境，并观察编辑弹窗中 key 字段。
  2. 观察同步状态从 `pending` 到 `queued/running`、`failed` 与 `conflict` 的页面反馈，分别尝试 retry/导入。
  3. member 打开同一路由，并检查管理区域与弹窗不可见。
- **可观察预期**：
  - R1 保留环境快照主体；R2 仅 admin 显示 key、名称、URL、描述、启停、状态、最近脱敏错误和操作；R3 编辑时 key 只读。
  - R4 仅对 `failed` 提供可重试入口；`conflict` 只显示导入 YAML 或重新提交，不提供会覆盖 YAML 的直接操作。
  - 不出现模块子任务、模块级 Allure、Daily 平台触发按钮或设计标注层内容；member 无管理 DOM。
- **备注**：本用例在 UI 原型完成后校准元素语义，避免把设计标注层实现为产品 UI。

## F4 受控迁移（P1）

### TC-S13-F4-001：最终验收前保留旧分模块 Daily Job 与历史

- **关联 AC**：AC4.1
- **测试目标**：验证新流水线尚未签字时所有初始化、同步和日常运行均不删除旧 Job。
- **优先级**：P1
- **前置条件**：Jenkins 有旧分模块 Daily Job 和至少一份历史构建；迁移开关/验收记录为未最终签字。
- **脱敏测试数据**：旧 Job 名 `<legacy-daily-prefix>-module-alpha`；历史构建号 `<legacy-build-number>`。
- **操作步骤**：
  1. 执行版本化 Jenkins init 修复和一次环境目录同步。
  2. 查询旧 Job 配置、构建历史及新唯一父 Job。
  3. 审核迁移脚本/Job DSL 的删除守卫。
- **可观察预期**：
  - 新父 Job 可被创建/修复，但旧分模块 Daily Job 和全部已有构建历史保持存在、可访问。
  - 未签字状态下不存在删除 Job、清空历史或隐式替换旧 Job 的副作用。
  - 删除守卫使用受控、可审计的最终验收条件，不能仅以新 Job 存在作为条件。
- **备注**：该测试只在隔离 Jenkins fixture 验证删除守卫，不删除主人环境中的任何 Job 或历史。

### TC-S13-F4-002：最终签字后的版本化受控删除

- **关联 AC**：AC4.2
- **测试目标**：验证最终签字后仅删除旧分模块 Daily Job 和其 Jenkins 历史，保留新父 Job 与平台历史。
- **优先级**：P1
- **前置条件**：隔离 Jenkins 中有旧 Job、构建历史和唯一父 Job；验收包具有主人最终签字的可验证受控标记；平台数据库有历史任务与快照。
- **脱敏测试数据**：旧 Job 列表 `<legacy-daily-jobs>`；父 Job `AiApiTest-DWP-Daily-Full-Module`；签字标记 `<approved-acceptance-record>`。
- **操作步骤**：
  1. 在隔离环境执行版本化迁移并记录计划删除列表。
  2. 检查迁移后的 Jenkins Job 清单、父 Job 定时器和旧 Job 历史。
  3. 查询平台数据库的既有任务、环境、快照与趋势。
- **可观察预期**：
  - 仅计划中的旧分模块 Daily Job 及其 Jenkins 构建历史被删除；唯一父 Job、Daily Worker、重试 Job 和其限流分类仍存在。
  - 平台数据库的历史任务、快照、趋势和审计不被物理删除。
  - 迁移输出包含脱敏删除清单、签字依据和可追溯结果；缺签字时必须拒绝执行并回到 TC-S13-F4-001 行为。
- **备注**：生产删除必须在主人最终验收后按受控发布流程执行；本阶段不执行实际删除。

## 覆盖与交接

| 覆盖类别 | 测试用例 |
| --- | --- |
| 正常路径 | TC-S13-F1-001~004、TC-S13-F2-001~003、TC-S13-F3-001/003/005/007/012、TC-S13-F4-002 |
| 异常与恢复 | TC-S13-F1-005/007、TC-S13-F2-004、TC-S13-F3-002/006/008/009/013 |
| 边界与并发 | TC-S13-F1-002/004、TC-S13-F3-001/002/004/010 |
| 权限与 UI 范围 | TC-S13-F3-011/014 |
| 状态机与幂等 | TC-S13-F1-003/006、TC-S13-F2-001/003、TC-S13-F3-004/006/008/009/010 |
| Jenkins / Docker 协议 | TC-S13-F1-001/002/007、TC-S13-F3-005/006/007/012、TC-S13-F4-001/002 |

后端 pytest、Pipeline/`api-test` 测试和前端 Playwright 用例应以本文件编号拆分；实际日志、截图、Allure 原始结果和 Jenkins 输出仅作为构建 artifact 保存，不提交到本目录。
