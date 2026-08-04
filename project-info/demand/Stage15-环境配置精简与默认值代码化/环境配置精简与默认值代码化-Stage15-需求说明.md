# 环境配置精简与默认值代码化-Stage15-需求说明

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境配置精简与默认值代码化-Stage15 |
| 需求分级 | L |
| 裁剪说明 | 本需求跨 `back-end`、`front-end`、`docker`、`jenkins`、启动脚本、流程规则与安全配置契约，按 L 档执行完整 loop。无新增产品页面，UI 阶段计划输出同名 `N/A + 理由` 适用性说明；无 DRF 业务 API 变更，API 契约记录为 `N/A + 理由`。其余质量门禁不裁剪。 |
| 关联模块 | `back-end` / `front-end` / `docker` / `jenkins` / `api-test` / `scripts` / `project-info` |
| 文档状态 | 已冻结 |
| 负责人 | Codex |

## §0 待澄清清单（澄清门禁）

> 本节全部闭环并由主人完成 §14 冻结前，不进入测试用例、TDD 实现或运行环境变更。

| 编号 | 待澄清点 | 可选方案 / 影响面 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- |
| Q1 | 服务地址是继续逐服务配置，还是收敛为平台主机与端口后统一派生？ | A：保留平台绑定主机、公开主机/协议及 MySQL、Jenkins、backend、frontend 对外端口，代码派生服务 URL、API URL、前端代理和 Playwright 地址；不支持每个服务不同域名/路径前缀。B：保留每个服务独立 bind host 与 public URL。 | 选择 A；当前平台采用统一主机/协议与端口模型，反向代理前缀另立需求。 | 已确认 |
| Q2 | 哪些运维调优项仍属于“必要可选配置”？ | A：只保留 `PROJECT_WORKSPACE`、`DOCKER_GID`、`CI_RUN_RETENTION_DAYS`、`FRONTEND_PLAYWRIGHT_BASE_IMAGE`；其余固定默认值代码化。B：额外保留 Jenkins executors、超时和 Cookie 策略。 | 选择 A；Jenkins executors、请求/轮询/心跳超时、Cookie 固定策略、Job 名、API 路径和内部 workspace 全部代码化。 | 已确认 |
| Q3 | 已完成验收的 Stage13 旧 Daily Job 受控删除开关如何处理？ | A：退役两个 env 键及一次性删除分支。B：env 移除但代码固定为禁止删除。 | 选择 A；当前受管 Jenkins 已完成删除，其他遗留 Jenkins home 由人工迁移处理。 | 已确认 |
| Q4 | “`.env` 与 `.env.example` 一致”的可执行定义是什么？ | A：公共区键名、顺序、分组和注释完全一致；值可按实际部署不同；`.env` 额外包含私有区。B：公共值也逐行完全一致。 | 选择 A；模板使用安全通用值，私有文件保留实际部署值。 | 已确认 |
| Q5 | 是否在本次关闭环境目录同步服务令牌未注入 backend 的既有缺口？ | A：新增私有令牌并在启用同步时条件必填、注入 backend。B：排除该既有缺口。 | 选择 A；未启用同步时允许为空，启用时必须与 Jenkins service credential 形成闭环。 | 已确认 |

## §1 需求背景与目标

- **背景**：根 `.env` 当前有 55 个键，`.env.example` 有 51 个键，合并后涉及 78 个不同变量；两文件的键、顺序、分组和说明已经漂移。大量 Job 名、内部容器地址、API 路径、默认超时、Cookie 名称、运行模式和 workspace 常量同时存在于 env、Compose、Python/TypeScript/Groovy 默认值和静态测试中，维护者无法快速判断真正需要修改的项目。
- **历史承接**：Stage2 已建立根 env 单一入口；Stage13 已冻结“外部地址/端口由环境提供，服务名、Job 名、Compose project 与固定默认值由代码维护”。本需求在不改变平台执行协议的前提下继续收敛该边界。
- **目标**：
  - 根配置只保留实际部署差异、必要运维选择和私有凭据。
  - 固定值迁移到明确的模块所有者，不再保留可覆盖但不应修改的伪配置。
  - `.env` 与 `.env.example` 建立可自动检查、不会泄露值的一致性契约。
  - 所有被删除、保留或改名的变量都同步修改消费者、Compose、脚本、文档和测试。
  - 私有 `.env` 的现有真实值在重构中仅按键迁移，禁止输出、提交或写入验收资料。
- **成功指标**：公共配置项数量显著低于当前 51 项；不存在已退休键的生产读取/Compose 插值；Platform Bootstrap 预检能在 Docker 操作前识别配置契约漂移；完整静态、后端、前端和固定 Jenkins Job 回归通过。

## §2 范围

- **做（in scope）**：
  - 重构 `.env`、`.env.example` 的公共区与私有区。
  - 将通用固定项迁入 Django settings、Vue/Vite/Playwright 配置、Compose、Jenkins Init/Pipeline 和 Bootstrap helper 的代码常量。
  - 删除废弃兼容项，例如无生产消费者的 `JENKINS_PYTHON_VENV_DIR`、`JENKINS_API_TEST_DIR` 以及重复代理别名 `VITE_DEV_API_PROXY`。
  - 收紧 MySQL 凭据传播：`MYSQL_ROOT_PASSWORD` 仅供 MySQL 管理/健康检查，backend、worker 与一次性 bootstrap 只使用应用专用 `DB_USER` / `DB_PASSWORD`。
  - 增加脱敏配置契约测试和 Platform Bootstrap 预检门禁。
  - 同步根/模块规则、部署说明、Jenkins 说明、快速启动资料、RTM 与验收包。
- **不做（out of scope）**：
  - 不新增或改变 DRF 业务 API、Vue 页面、权限、数据表、Allure 报告协议和 `api-test` 执行协议。
  - 不启动、停止、重建 MySQL/Jenkins，不删除 volume，不执行旁路 migration 或管理员初始化。
  - 不改变固定 Platform Bootstrap Job 的八阶段、唯一入口和服务生命周期边界。
  - 不把真实凭据、内部私有 URL、实际 token 或本机绝对路径写入受版本控制文件。
  - 不顺带改变当前 Django local settings 的实际 DEBUG 行为；如需生产安全 settings，另立需求。

## §3 用户角色与权限矩阵

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| 主人/平台运维 | 配置公共部署差异和私有凭据；bootstrap MySQL/Jenkins；触发固定环境 Job | 提交私有 `.env`；绕过安全边界删除 volume | 当前本地平台配置与 Jenkins 证据 |
| AI 协作代理 | 修改受版本控制的配置契约与代码默认值；通过固定 helper 触发环境验收 | 输出 `.env` 实际值；直接管理应用服务或基础服务 | 键名、脱敏状态、静态与 Jenkins 证据 |
| 普通平台用户 | 使用平台业务能力 | 查看或修改平台环境配置 | 已授权业务数据 |

## §4 功能清单与验收标准

### F1 最小公共配置契约

- **要求**：公共配置只表达无法安全代码化的部署差异；所有保留项都有生产消费者、清晰中文说明和唯一所有者。
- **关联数据表**：不涉及持久化。
- **验收标准**：
  - `AC1.1` — Given 新公共键集合已冻结 When 解析 `.env.example` Then 键集合、顺序、分组和注释与契约完全一致，且无固定项或私有项。
  - `AC1.2` — Given 私有 `.env` 存在 When 忽略私有区和值差异后 Then 公共区与模板的键、顺序、分组和注释一致。
  - `AC1.3` — Given 任一保留公共键 When 扫描仓库 Then 存在明确生产消费者，不允许仅有文档/测试引用。
  - `AC1.4` — Given 服务地址基础量 When 生成 Compose、Summary、helper、Vite 和 Playwright 配置 Then 派生结果一致且不绑定个人路径。

### F2 固定默认值代码化

- **要求**：固定 Job 名、内部服务名、API 路径、超时、运行模式、Cookie 固定策略和默认 workspace 归属对应模块代码；旧 env 值不得继续覆盖行为。
- **关联数据表**：不涉及持久化。
- **验收标准**：
  - `AC2.1` — Given `.env` 中残留已退休键 When 加载后端、前端或 Jenkins 配置 Then 产品行为仍使用冻结代码常量，且契约门禁报告残留键。
  - `AC2.2` — Given Compose 配置 When 静态扫描 Then 不再插值已退休固定键，容器内地址继续使用 Compose 服务名。
  - `AC2.3` — Given Jenkins 启动与 helper When 查找固定 Job Then Init Groovy 与 helper 使用同一代码级 Job 名，不能被 `.env` 改名形成旁路。
  - `AC2.4` — Given backend/worker/bootstrap 容器配置 When 检查凭据注入 Then 不含 MySQL root 密码，数据库连接仅使用应用专用账号。

### F3 私有配置与安全一致性

- **要求**：账号、密码、token、密钥和初始化账号只在私有 `.env`/Jenkins Credentials 中存在；检查和错误输出仅报告键名及状态。
- **关联数据表**：不涉及持久化。
- **验收标准**：
  - `AC3.1` — Given `.env.example` When 扫描私有键与敏感模式 Then 不包含私有键、真实值或可用凭据占位。
  - `AC3.2` — Given 配置缺失、错序、多余或重复 When Platform Bootstrap Preflight 运行 Then 在任何 Docker 检查前以 `CONFIG_ENV_CONTRACT_DRIFT` 失败，并只输出键名/行号/类型。
  - `AC3.3` — Given 配置契约检查失败 When 查看 pytest/Jenkins 输出 Then 不出现 `.env` 的任何配置值。
  - `AC3.4` — Given `.env` 已有真实私有值 When 执行迁移 Then 保留这些值且不在 Git diff、日志或验收资料中出现。

### F4 文档、兼容性和受控迁移

- **要求**：所有引用配置入口的规则与使用说明同步到新契约，旧变量不再被指导使用。
- **关联数据表**：不涉及持久化。
- **验收标准**：
  - `AC4.1` — Given 新增、删除或改名变量 When 扫描仓库 Then `.env.example`、消费者、Compose、模块文档和静态测试一致。
  - `AC4.2` — Given 既有平台环境 When 通过固定 Platform Bootstrap Job 验收 Then 八阶段、三项应用服务、MySQL/Jenkins 生命周期边界和报告归档协议不变。
  - `AC4.3` — Given `.env` 不存在 When 主人运行基础服务 bootstrap helper Then 生成的初始文件不会被误认为已补齐私有凭据，文档明确要求人工配置后再启动。

## §5 状态机定义

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| 旧配置契约 | 新测试先行并取得有效 RED | 待迁移 | 失败原因必须是旧键集合或旧可覆盖行为 | 不改变运行环境 |
| 待迁移 | 完成代码默认值、两文件与消费者迁移 | 新配置契约 | 目标测试 GREEN、无敏感泄露 | 私有 `.env` 在本机更新但不提交 |
| 新配置契约 | 固定 Jenkins 环境 Job 全绿并完成独立复审 | 可验收 | 阻断问题为零 | 归档 Jenkins build/artifact 索引 |
| 任意状态 | 发现规格外安全/部署关键决策 | 已熔断 | 回写 §0 并等待主人裁决 | 不继续实现 |

## §6 数据表设计

不新增或变更数据库表、字段、索引、迁移和数据状态；现有 MySQL volume 保持不变。

## §7 API 契约

`N/A`：不新增或修改 DRF 业务接口、请求/响应字段、错误码、分页、权限或状态流转。现有健康接口与环境目录内部接口路径保持不变；仅可能调整它们读取配置的来源。

## §8 UI 字段级规格

`N/A`：不新增页面、路由、组件、弹窗或 DOM，不改变视觉和交互。UI 阶段输出同名适用性说明并引用现有页面基线；不需要原型图、区域语义拆解或前端实现映射。

## §9 架构影响评估

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | 配置所有权从根 env 下沉到 DRF、Vue、Compose、Jenkins/helper；业务职责边界不变。 |
| 数据模型 | 否 | 无 migration、数据导入或表结构变化。 |
| 权限 | 否 | 平台角色权限不变；私有配置访问边界收紧。 |
| Jenkins 执行链路 | 是 | Init/Pipeline/helper 与 Preflight 配置读取变化；固定唯一入口和八阶段不变。 |
| `api-test` 执行协议 | 否 | pytest、重试、node id、summary 与 Allure 协议不变；仅检查相关运行参数不要误纳入根 env。 |
| 报告 / Allure 协议 | 否 | 构建摘要地址来源可能改为派生，但字段、归档和入口不变。 |
| Docker Compose 部署 | 是 | 大量插值项改为代码常量；公开端口、私有凭据、workspace 与 GID 继续受控注入。 |
| 安全 | 是 | 减少 root 密码传播；建立私有键禁入模板和脱敏漂移诊断。 |

## §10 容器化兼容检查

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 是，私有 `PROJECT_WORKSPACE` 可配置 | 模板使用相对安全默认；代码和文档不写个人路径。 |
| 宿主机固定端口 | 否（目标） | 宿主机公开端口继续作为最小公共配置；容器内部端口代码化。 |
| 真实凭据 | 是，仅私有 `.env` / Jenkins Credentials | 模板完全不出现私有键；日志只输出键名/状态。 |
| 不可迁移业务常量 | 否 | 只固化项目身份、内部服务名、固定 API 路径和协议默认，不固化业务环境或个人地址。 |
| 手工 Jenkins 配置依赖 | 否 | 继续由版本化 Init Groovy 幂等创建/修复固定 Job。 |

## §11 非功能要求

- **安全**：禁止任何测试失败 diff、异常文本、日志或文档输出 `.env` 值；敏感扫描覆盖模板、Git diff 和 Jenkins artifact 摘要。
- **兼容性**：Windows PowerShell、Linux/macOS/Git Bash helper 采用相同键集合；Compose service name 与固定 project identity 不变。
- **可维护性**：每个保留键有唯一中文说明、类型/格式、默认语义、消费者和修改后影响；每个已退休键有代码归属和回归断言。
- **可观测性**：配置漂移诊断使用稳定错误码，只报告缺失、多余、重复、错序的键名和行号。

## §12 验收口径汇总

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| AC1.1-AC1.4 | 最小公共配置及两文件公共区一致 | F1 |
| AC2.1-AC2.4 | 固定项不可再由 env 覆盖，内部地址/凭据边界正确 | F2 |
| AC3.1-AC3.4 | 私有项不公开、漂移诊断脱敏、真实值安全迁移 | F3 |
| AC4.1-AC4.3 | 消费者/文档一致，固定 Jenkins 环境回归不退化 | F4 |

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-08-04 | v0.1-draft | 建立 L 级需求草案、依赖盘点结论和五项待澄清决策 | 主人提出根环境配置大规模精简重构 |
| 2026-08-04 | v1.0-frozen | 主人确认 Q1-Q5，冻结统一主机派生模型、最小可选项、Stage13 删除分支退役、公共区一致性和环境目录令牌闭环 | 需求澄清完成，允许进入下游阶段 |

## §14 冻结确认（主人签字门禁）

- [x] §0 待澄清清单全部闭环
- [x] §9 架构影响评估已完成
- [x] §7 API 契约已评估为 `N/A + 理由`
- [x] §10 容器化兼容检查已形成目标与整改项
- [x] §4 功能点具备可测验收标准草案

**冻结人（主人）**：`主人（会话确认）`
**冻结日期**：`2026-08-04`

> 冻结前禁止进入下游实现；冻结后按“功能测试用例与 UI 适用性说明 -> TDD RED/GREEN/REFACTOR -> 独立对抗审查/修复/同 reviewer 复审 -> 固定 Jenkins Job 验收 -> 验收包 -> 单独 commit/push”自动推进。
