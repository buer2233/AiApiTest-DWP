# 初始版本收尾-Stage2-MySQL与环境变量配置收尾-需求说明

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 初始版本收尾-Stage2-MySQL与环境变量配置收尾 |
| 需求分级 | M |
| 裁剪说明 | 本需求跨 `back-end`、`front-end`、`docker`、`jenkins`、`api-test` 和流程文档，影响数据库与启动契约，按 M 档推进；不新增业务页面、不改变用户可见业务功能和 API 响应协议，因此裁剪 UI 原型图阶段，但保留需求澄清冻结、架构影响评估、API 契约冻结、容器化兼容检查、TDD/回归证据和独立审查。 |
| 关联模块 | `back-end` / `front-end` / `docker` / `jenkins` / `api-test` / `project-info` |
| 文档状态 | 已冻结 |
| 负责人 | Codex |

## §0 待澄清清单（澄清门禁）

| 编号 | 待澄清点 | 可选方案 / 影响面 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- |
| Q1 | SQLite 临时库 `back-end/db.sqlite3` 中已有 `user_account=2`、`invitation_code=2`，切换 MySQL 时是否迁移这些验收数据？ | A. 迁移保留：最大限度保持已验收初始版本状态，但需要增加数据迁移/导入步骤和证据；B. 全新初始化：只执行 MySQL migration 和 `init_admin`，流程更干净，但现有用户/邀请码验收数据不保留。 | 迁移到 MySQL 后先保留 `back-end/db.sqlite3` 作为验收备份；待本轮验收确认 MySQL 功能无问题后，再由主人决定是否删除 SQLite 文件。 | 已确认 |
| Q2 | Docker daemon 当前未运行，无法完成 MySQL 实际启动验证；本轮是否等待主人启动 Docker Desktop 后继续？ | A. 主人启动 Docker Desktop 后继续：可完成 MySQL 启动、迁移和服务验证；B. 先提交代码/文档：将 MySQL 实际启动列为阻塞验收项，风险是无法证明正式库已可用。 | 主人已启动 Docker Desktop，继续完成 MySQL 启动、迁移和服务验证。 | 已确认 |
| Q3 | `api-test` 与 Jenkins 中示例业务测试目标 `https://api.gbif.org` 是否本轮一并环境变量化？ | A. Jenkins 本轮一起环境变量化，`api-test` 执行协议暂不动；B. 同步改 `api-test/config.py` 与 Jenkins pipeline 默认值读取环境变量，扩大回归范围。 | Jenkins 本轮一起修改；`api-test` 代码和执行协议本轮暂不修改，仅保留后续项。 | 已确认 |

> §0 已根据主人 2026-07-04 裁决闭环，可以进入后端/前端/脚本实现阶段。

## §1 需求背景与目标

- **背景**：当前初始版本已通过阶段验收，但后端正式运行仍可落到临时 SQLite；前端、后端、Docker、Playwright 和启动文档中仍存在分散的服务地址、端口、数据库路径或样例凭据说明。正式收尾前需要统一到根目录 `.env` / `.env.example`，并通过 Docker MySQL 承载正式数据。
- **目标**：
  - 后端正式运行默认使用 Docker MySQL，数据库连接信息由根 `.env` 驱动。
  - 前端 dev server、API base URL、Playwright baseURL/webServer 不再写死端口和 IP，统一从根 `.env` 读取或派生。
  - `.env.example` 覆盖当前项目启动所需的脱敏变量；真实 `.env` 保持 git 忽略，不提交。
  - 根 `AGENTS.md` 与 `project-info/AGENTS.md` 同步 `.env` 标准开发流程。
  - 启动后不建议修改的配置有明确备注，避免后续改密、换端口或换数据卷导致验收环境断链。
- **成功指标 / 价值**：
  - MySQL 启动、Django migration、`init_admin`、后端检查/测试、前端 typecheck/build/Playwright 回归有实际证据。
  - 静态扫描不再发现新增硬编码本机绝对路径、真实凭据或不可迁移服务地址。
  - 主人可以基于验收包完成初始版本最终验收。

## §2 范围

- **做（in scope）**：
  - 后端 settings 支持从根 `.env` 读取正式 MySQL 配置，并与 Compose `MYSQL_*` 变量对齐。
  - 将 SQLite 中当前验收数据迁移到 MySQL，同时保留 `back-end/db.sqlite3` 文件作为本轮验收备份，不在本次提交中删除。
  - 保留测试 settings 的内存 SQLite，用于 pytest 快速单元/接口测试；正式运行和文档说明使用 MySQL。
  - 前端 Vite 配置使用根 `.env` 中的 dev host/port、代理目标和 `VITE_API_BASE_URL`。
  - Playwright 配置和涉及 origin 的测试从同一组 `PLAYWRIGHT_*` 变量派生。
  - `.env.example` 补齐 Docker、Django、Auth、前端、Playwright、初始化管理员和必要路径变量。
  - 更新根 `AGENTS.md`、`project-info/AGENTS.md`、快速启动/部署文档和相关静态测试。
  - 启动 Docker MySQL 后执行迁移、初始化管理员和必要的冒烟验证。
- **不做（out of scope）**：
  - 不新增业务数据表和业务 API。
  - 不改变 `/api/v1`、`/api/docs/`、`/api/schema/` 等已冻结接口路径。
  - 不在本轮设计完整 CORS/CSRF 跨域 Cookie 方案；当前前端 dev 仍通过 Vite 代理访问后端。
  - 不提交真实 `.env`、真实账号密码、Jenkins Token、Cookie、日志或运行时产物。
  - 不删除 Docker volume，除非主人明确批准。
  - 不修改 `api-test` 代码和执行协议；相关默认测试目标环境变量化留待后续独立需求。

## §3 用户角色与权限矩阵

本需求是平台配置与部署收尾，不新增业务角色权限。

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| 平台开发/验收人员 | 使用 `.env` 启动 Docker MySQL、后端、前端和 Playwright 验证 | 将真实 `.env` 或运行时产物提交到仓库 | 本地验收环境配置与脱敏样例 |
| 后续 AI agent | 按 `AGENTS.md` 与 `.env.example` 增量开发 | 写死本机路径、真实凭据、宿主机固定端口 | 仓库内脱敏配置和流程资料 |

## §4 功能清单与验收标准

### F1 后端正式数据库切换到 MySQL

- **能做什么 / 做到什么程度 / 满足什么要求**：后端正式运行使用 MySQL；数据库名称、账号、密码、主机、端口、连接保活等从 `.env` 读取；变量名和 Docker Compose 保持一致，避免同一数据库信息维护两套名字。
- **关联数据表**：不新增表；使用既有 Django migration 管理的 `user_account`、`invitation_code` 等表。
- **验收标准**：
  - `AC1.1` — Given 根 `.env` 配置了 MySQL 变量 When 执行 Django settings 检查 Then `DATABASES["default"]` 使用 `django.db.backends.mysql` 且库名与 `MYSQL_DATABASE` 一致。
  - `AC1.2` — Given Docker MySQL 可用 When 执行 `python manage.py migrate` Then 所有迁移成功落到 MySQL。
  - `AC1.3` — Given `.env` 中存在初始化管理员变量 When 执行 `python manage.py init_admin` Then 管理员账号可创建或幂等更新，且不输出真实密码。
  - `AC1.4` — Given pytest 使用 `config.settings.test` When 执行后端测试 Then 测试仍使用内存 SQLite，不依赖本机 MySQL。
- **异常场景**：
  - Docker daemon 未运行 → 阻止 MySQL 启动验证，并在验收包中记录为外部环境阻塞。
  - 旧 MySQL volume 密码与 `.env` 不一致 → 明确提示旧 volume 不会因 `.env` 改密。
- **边界值**：
  - `DB_ENGINE` 未设置 → 正式 local settings 默认走 MySQL；test settings 仍强制 SQLite。
  - `MYSQL_HOST_PORT` 与容器内 `3306` 不同 → 宿主机后端用 host port，容器内服务用 Compose 服务名和 `3306`。

### F2 前端与 Playwright 配置从根 `.env` 派生

- **能做什么 / 做到什么程度 / 满足什么要求**：Vite dev server host/port、开发代理目标、客户端 API base URL、Playwright baseURL/webServer 不写死到源码；Vite 配置显式从仓库根目录加载 `.env`。
- **关联数据表**：不涉及持久化。
- **验收标准**：
  - `AC2.1` — Given 根 `.env` 定义了前端 dev host/port When 执行 Vite 配置加载 Then server host/port 使用 env 值。
  - `AC2.2` — Given 根 `.env` 定义了后端服务 URL When 启动前端开发代理 Then `/api` 代理目标来自 env。
  - `AC2.3` — Given Playwright 变量配置 When 执行 E2E Then baseURL、webServer URL 和测试 permission origin 来自同一派生值。
  - `AC2.4` — Given `VITE_API_BASE_URL` 为空或未设置 When 前端构建 Then Axios 默认使用 `/api/v1` 相对路径。
- **异常场景**：
  - env 端口不是数字 → 配置加载使用安全默认值并在测试中暴露。
- **边界值**：
  - `VITE_API_BASE_URL=/api/v1` → 适配 Vite 代理。
  - `VITE_API_BASE_URL=http://example.invalid/api/v1` → 构建期注入完整 API 地址。

### F3 `.env.example` 与流程文档标准化

- **能做什么 / 做到什么程度 / 满足什么要求**：`.env.example` 提供脱敏、可复制的完整变量模板；根 `AGENTS.md` 和 `project-info/AGENTS.md` 记录 `.env` 是项目标准配置入口；快速启动/部署文档不再要求手写一批 `$env:MYSQL_*`。
- **关联数据表**：不涉及持久化。
- **验收标准**：
  - `AC3.1` — Given 新开发者复制 `.env.example` 为 `.env` When 按快速启动文档执行 Then 能看到所有必须配置项及启动后不建议修改项。
  - `AC3.2` — Given 静态测试扫描 `.env.example` When 执行 Jenkins/Docker 静态测试 Then 必要变量齐全且无真实密码、Token、Cookie。
  - `AC3.3` — Given 后续 agent 阅读根 `AGENTS.md` 和 `project-info/AGENTS.md` When 修改服务地址、端口或路径 Then 必须优先更新 `.env.example` 和文档，不得写死配置。
  - `AC3.4` — Given 文档包含本机示例 When 扫描资料 Then 不出现真实绝对路径、真实密码或生产地址。

## §5 状态机定义

本需求不引入业务状态机。配置状态仅在验收包中记录：

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| SQLite 临时运行 | MySQL 配置冻结并完成迁移 | MySQL 正式运行 | Docker MySQL 可用，迁移成功 | 后端正式运行数据源变更为 MySQL |
| MySQL 正式运行 | 修改启动后不建议修改项 | 待迁移/待回归 | 需主人批准 | 需要停机、迁移或重建验证 |

## §6 数据表设计

不新增或变更数据表。既有迁移表保持不变：

| 表 | 处理策略 | 关键约束 |
| --- | --- | --- |
| `user_account` | 由既有 migration 在 MySQL 创建，并导入 SQLite 旧数据；SQLite 文件保留作验收备份 | 用户名唯一、角色枚举不变 |
| `invitation_code` | 由既有 migration 在 MySQL 创建，并导入 SQLite 旧数据；SQLite 文件保留作验收备份 | 邀请码唯一、状态枚举不变 |
| `django_migrations` | MySQL 迁移自动维护 | 不手动写入 |

## §7 API 契约

本需求不新增或修改业务 API 契约。

| 项 | 冻结结论 |
| --- | --- |
| 业务 API 路径 | `/api/v1/...` 不变 |
| Swagger/OpenAPI | `/api/schema/`、`/api/docs/` 不变 |
| 请求/响应字段 | 不变 |
| 错误码 | 不变 |
| 权限 | 不变 |

## §8 UI 字段级规格

本需求不新增页面，不生成 UI 原型。涉及前端的范围仅为启动配置和 API base URL 读取方式，页面 DOM 和交互不变。

## §9 架构影响评估

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | 后端、前端、Docker、文档共享根 `.env` 变量契约；不改变业务模块边界。 |
| 数据模型 | 否 | 不新增/变更表；仅将正式运行数据库从 SQLite 切到 MySQL。 |
| 权限 | 否 | 不改变角色、权限或认证接口；只补 Auth 相关环境变量模板。 |
| Jenkins 执行链路 | 是 | Jenkins 相关默认路径和公开地址本轮环境变量化；同步 Docker 文档和静态测试。 |
| `api-test` 执行协议 | 否 | 主人已裁决本轮不修改 `api-test` 代码和执行协议。 |
| 报告 / Allure 协议 | 轻微影响 | 文档和样例路径改为变量化；不改报告生成协议。 |
| Docker Compose 部署 | 是 | MySQL 是正式数据库，启动后 root 密码、库名、volume、端口不建议随意改。 |
| 安全 | 是 | `.env` 不提交；`.env.example` 只放占位值；真实密码、Token、Cookie 不进入仓库。 |

## §10 容器化兼容检查

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 是 | `project-info/quick-start-all-services.md` 等文档中的本机路径改为 `$PROJECT_ROOT`、`PROJECT_WORKSPACE`、`ALLURE_REPORTS_ROOT` 占位。 |
| 宿主机固定端口 | 是 | 前后端、Playwright、Docker 端口均通过 `.env.example` 变量说明；文档区分宿主机开发端口和 Compose 内部服务名。 |
| 真实凭据 | 风险存在 | `.env.example` 使用 `change-me-*` 或 `<...>` 占位；不得提交真实 `.env`。 |
| 不可迁移业务常量 | 是 | `api-test` 示例 `https://api.gbif.org` 本轮不改执行协议，记录为后续独立需求候选；Jenkins 相关默认路径和公开地址本轮环境变量化。 |
| 手工 Jenkins 配置依赖 | 否 | 本轮不引入新的 Jenkins 手工配置。 |

## §11 非功能要求

- **安全**：真实 `.env` 不提交；脱敏模板不包含真实账号、密码、token、cookie、生产 URL。
- **可迁移性**：服务地址、端口、数据路径、报告路径通过 `.env.example`、Compose 服务名、volume 或相对路径表达。
- **可维护性**：启动后不建议修改的变量集中备注，避免后续误改造成数据卷或历史报告断链。
- **可验证性**：配置读取、MySQL 迁移、后端测试、前端构建/E2E、静态扫描都有证据文件。

## §12 验收口径汇总

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| AC1.1 | Django 正式 settings 使用 MySQL 且库名与 `MYSQL_DATABASE` 一致 | F1 |
| AC1.2 | Docker MySQL 可用后 Django migration 成功 | F1 |
| AC1.3 | `init_admin` 从 `.env` 幂等初始化管理员且不泄露密码 | F1 |
| AC1.4 | pytest 测试环境仍使用内存 SQLite | F1 |
| AC2.1 | Vite dev host/port 从根 `.env` 加载 | F2 |
| AC2.2 | Vite `/api` 代理目标从 env 派生 | F2 |
| AC2.3 | Playwright baseURL/webServer/origin 使用同一派生配置 | F2 |
| AC2.4 | Axios 未配置时默认 `/api/v1` 相对路径 | F2 |
| AC3.1 | `.env.example` 可作为完整脱敏启动模板 | F3 |
| AC3.2 | 静态测试确认 `.env.example` 无真实敏感值且变量齐全 | F3 |
| AC3.3 | `AGENTS.md` 记录 `.env` 标准配置入口 | F3 |
| AC3.4 | 快速启动/部署资料无真实绝对路径、真实密码或生产地址 | F3 |

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-07-04 | 0.1 | 创建澄清中需求说明书 | 初始版本最终验收前 MySQL 与 `.env` 收尾 |

## §14 冻结确认（主人签字门禁）

冻结前逐项核对：

- [x] §0 待澄清清单全部闭环（无“待确认”状态）
- [x] §9 架构影响评估已完成
- [x] §7 API 契约完整、可冻结（本轮不改变业务 API）
- [x] §10 容器化兼容检查已列出整改方案
- [x] §4 每个功能点都有可测的 Given-When-Then 验收标准

**冻结人（主人）**：`已通过对话裁决冻结`　　**冻结日期**：`2026-07-04`
