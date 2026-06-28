# 当前活动计划：第一个需求-用户登录注册和测试用例展示

## 目标

按仓库固定 loop 完成首个需求：用户注册、用户登录、登录态校验、测试用例展示；先完成需求分级、澄清冻结、架构影响评估、API 契约草案与容器化兼容检查，主人冻结后再自动衔接功能测试用例、UI 原型、后端 TDD、前端 TDD、验收包、提交和推送。

## 当前阶段

Phase 7：完成。

## 阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| Phase 0：恢复上下文与代码盘点 | 完成 | 已读取全局规则、计划文件、架构资料、需求模板、后端/前端规则，并检查当前工作区状态。 |
| Phase 1：需求分级与需求说明书 | 完成 | 本需求涉及用户、邀请码、权限、测试用例数据表、DRF API、Vue 页面，按 M 档完整 loop，不裁剪阶段。 |
| Phase 2：需求澄清冻结 | 完成 | 主人已确认 Q1-Q7，并于 2026-06-28 明确“冻结”。 |
| Phase 3：功能测试用例与 RTM | 完成 | 已在 `project-info/test_case/` 输出同名测试用例和可追溯矩阵。 |
| Phase 4：UI 原型与覆盖校准 | 完成 | 已在 `project-info/UI/` 输出登录、注册、邀请码管理和测试用例列表原型，并依据测试用例完成覆盖校准。 |
| Phase 5：后端 TDD 实现 | 完成 | 已验证 RED：缺少 `config.settings.test` 和 `manage.py`；已实现 DRF 代码并跑通 GREEN：18 passed，覆盖率 94%。 |
| Phase 6：前端 TDD 实现 | 完成 | 已验证前端 RED/GREEN，核心 E2E 后扩展到全量 Playwright `10 passed` 并刷新关键页面截图。 |
| Phase 7：独立审查、验收包、提交推送 | 完成 | 已完成后端和前端独立对抗审查及复审并修复发现项；已聚合验收包，进入本需求单次提交和推送收尾。 |

## 关键问题

1. 功能测试用例和 RTM 是否覆盖全部 AC，是否存在需求漂移？
2. UI 原型是否覆盖测试用例中的正常、异常、边界、权限和状态反馈？

## 已确认决策

| 决策 | 理由 |
| --- | --- |
| 本需求按 M 档推进完整 loop | 涉及前后端、新增或重建数据模型、权限和 API 契约，不能按 S/XS 裁剪。 |
| 需求冻结前不编写业务代码 | 项目规则和 brainstorming 技能均要求先澄清、设计并获得主人确认。 |
| 当前不能依赖 `.pyc` 缓存作为源码 | 后端目录只残留 Python 缓存，没有可维护 `.py` 源码；必须重建可追踪源文件。 |
| 注册后用户默认 `active` | 主人选择 Q1=A，首期不做审批流程。 |
| 登录认证使用 DRF Token | 主人选择 Q2=A，首期使用简单稳定的 Token 认证。 |
| 测试用例通过后端扫描 `api-test/test_case/` 同步入库 | 主人选择 Q3=A，列表 API 从数据库读取。 |
| 注册入口需要邀请码 | 主人选择 Q4=C，需要补充邀请码配置方式。 |
| 测试用例展示字段使用完整首期字段集 | 主人选择 Q5=A，表格展示包名、模块、路径、类名、函数名、标题/描述、node id、更新时间。 |
| 首期权限采用 admin 同步、member 只读 | 主人选择 Q6=B，权限差异进入测试和前端展示。 |
| 邀请码采用数据库表和后台管理能力 | 主人选择 Q7=B，首期支持 admin 创建、查看、禁用邀请码，注册成功后累计使用次数。 |
| 需求已冻结 | 主人已回复“冻结 然后进行之后的步骤”，允许进入下游自动衔接阶段。 |

## 错误记录

| 错误 | 处理 |
| --- | --- |
| `using-superpowers` 技能说明要求通过平台技能加载，但当前环境仅暴露文件路径 | 按开发者技能规则读取 `SKILL.md` 完整内容并继续执行。 |
| `back-end/apps` 等目录在状态里显示为 ignored，初看像已有源码 | 进一步递归检查确认仅有 `__pycache__` 和 `.pyc`，没有 `.py` 源码。 |
| 后端 RED：`ImportError: No module named 'config.settings.test'` 且无 `manage.py` | 按 TDD 预期确认源码缺失导致失败，随后补齐可维护 DRF 工程源码。 |
| 后端首轮 GREEN 失败：重复邀请码返回 400 而契约要求 409 | 根因是 DRF `ModelSerializer` 自动唯一校验先于业务校验触发；关闭 `code` 字段默认唯一校验，由业务错误码返回 `duplicate_invite_code`。 |
| 前端审查 RED：member 直达 `/invite-codes` 未拦截、邀请码禁用按钮缺失 | 补充 Playwright 测试后修复路由守卫、禁用确认和状态刷新。 |
| 前端首轮修复后测试失败：Vite 解析 `src/**/*.js` 旧 sidecar 文件 | 删除 28 个生成 sidecar 文件并在 `.gitignore` 忽略 `front-end/src/**/*.js` 与 `*.js.map`。 |
| 后端审查 RED：唯一冲突、过期邀请码、非法枚举等 7 条契约用例失败 | 补充异常映射、事务处理、数据库约束、枚举校验和扫描器解析修复，后端全量 `25 passed`。 |
| 后端/前端复审均无阻塞问题，但提出非阻塞测试缺口 | 已补充数据库约束、Allure story 和邀请码创建字段错误测试；最终后端 `26 passed`，前端 Playwright `10 passed`。 |

---

# 开发流程与项目架构重构计划

## 目标

与用户一起重新梳理 `AiApiTest-DWP` 的企业级开发流程、AI 协作模式和整体项目架构，并在方案确认后更新根目录 `AGENTS.md` 与 `README.md`，让它们保持简约、清晰、可持续迭代。

## 约束

- 每次对用户回复必须以“主人”开头，并默认使用简体中文。
- 不把本项目当成空白项目处理，必须继承现有多阶段上下文。
- 先做需求深挖和方案确认，再修改正式项目文档。
- 根目录 `AGENTS.md` 与 `README.md` 最终只保留项目总目标、目录介绍、全局技能推荐和必要全局规则。
- 后端固定使用 Python DRF；前端技术栈可重新评估。
- 项目仍保持通用 AI 自动化测试平台定位，不绑定具体业务系统或敏感配置。

## 阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 恢复上下文与读取技能 | 完成 | 已读取 `using-superpowers`、`planning-with-files`、`brainstorming`、`product-requirements` |
| 调研当前项目结构和文档 | 完成 | 已读取根目录与模块 AGENTS、README、近期提交 |
| 深挖需求与澄清目标 | 完成 | 已确认严格 Jenkins 执行主干；详细功能需求先沉淀为草稿，主线回到架构设计 |
| 提出流程与架构方案 | 完成 | 已确认 monorepo、严格 Jenkins 主干、DRF 后端、Vue 3 前端和固定开发 loop |
| 方案确认 | 完成 | 用户已确认按该架构更新文档 |
| 更新 AGENTS.md 与 README.md | 完成 | 已使用简约结构重写根目录文档 |
| 验证与收尾 | 完成 | 已校验 draw.io XML，安装 draw.io desktop CLI，并导出 PNG |

## 已解决问题

- 单仓库内继续保留 `api-test`、`back-end`、`front-end`、`jenkins`、`docker`、`project-info`。
- Jenkins 是严格执行主干，不作为可选转发层。
- DRF 后端是平台编排和数据中心，不直接执行 pytest。
- 前端继续使用 Vue 3 + Vite + TypeScript + Element Plus。
- 每个需求按固定 loop 产出需求说明、功能测试用例、UI 原型、后端测试与实现、前端测试与实现。

## 已确认决策

- 平台执行主干采用严格 Jenkins 模式：平台侧所有测试执行、重试和报告生成都必须通过 Jenkins。
- 项目继续采用 monorepo 单仓库结构，不拆分为多个仓库。
- DRF 后端不直接执行 pytest，不直接替代 Jenkins；后端负责任务建模、权限、审计、Jenkins 触发/同步、失败用例和报告数据管理。
- `api-test` 是测试执行逻辑的唯一实现位置；涉及失败重试、报告生成、pytest 参数和 Allure 产物协议的变更，应优先在 `api-test` 内完成。
- 架构讨论中出现的详细功能和数据表内容先记录到 `project-info/demand/需求草稿-测试平台架构阶段.md`，当前不继续展开完整需求分析。
- 子目录 `AGENTS.md` 需要围绕固定 loop 明确各自入口、产物、依赖和禁止事项，避免后续开发绕过需求、用例、UI 原型或 TDD 阶段。

## 错误记录

| 错误 | 处理 |
| --- | --- |
| `using-superpowers` 初始系统路径不存在 | 使用实际路径 `C:\Users\admin\.codex\skills\using-superpowers\SKILL.md` 成功读取 |
| 首次补充 `findings.md` 时发现文件仍保留旧任务内容 | 改用单文件删除重建补丁，恢复为当前架构重构发现记录 |
| 首次启动可视化服务时将 Windows 路径直接传给 `bash` 导致路径转义失败 | 改用 Git Bash 风格 `/c/Users/...` 路径重试 |
| 第二次启动可视化服务仍失败，当前 `bash` 实际是 Windows WSL 启动器 | 改为直接使用技能目录下的 `server.cjs` 通过 Node 启动 |
| 本机最初未安装 draw.io desktop CLI，无法导出新 PNG 架构图 | 已安装 draw.io desktop CLI 30.2.4，并导出 `project-architecture.png` 与 `project-architecture.drawio.png` |
| `git commit` 失败：当前环境未配置 `user.name` 和 `user.email` | 需要用户提供 Git 身份，或确认使用仓库本地占位身份后再提交 |
| draw.io CLI 使用相对路径导出时报 `input file/directory not found` | 改用绝对路径执行导出 |
| 重新检查时发现架构资料目录已从 `project-info/project_picture/` 变为 `project-info/project_detail/` | 使用当前实际路径 `project-info/project_detail/project-architecture.drawio` 导出 PNG，不回退目录变更 |
| 尝试用临时 Python 生成 draw.io XML 时参数传递错误，未写出文件 | 改用 `apply_patch` 直接替换 `.drawio` 源文件 |

## 2026-06-27 整体 Docker 化架构增强

## 目标

将“后期整个平台可通过 Docker Compose 整体打包部署”的要求写入全局规则、Docker 目录规则和架构资料，并更新架构说明书与架构图。

## 阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 读取技能与当前文档 | 完成 | 已读取 using-superpowers、planning-with-files、brainstorming、drawio-skill 和现有架构资料 |
| 更新 Docker 与全局规则 | 完成 | 已更新 `docker/AGENTS.md`、新增 `docker/CLAUDE.md`，并补充全局 Docker 化要求 |
| 更新架构说明书与架构图 | 完成 | 已更新 `project-architecture.md` 与 `project-architecture.drawio` |
| 导出与校验 | 完成 | 已校验 draw.io XML，导出普通 PNG 与可编辑 PNG |
| 流程规范评价 | 进行中 | 完成后输出当前开发流程优化建议 |

## 本轮约束

- 不把整个平台做成单一巨型镜像，目标是一个 Compose 项目编排多个职责明确的容器。
- Jenkins 仍是严格执行主干，容器化不能绕过 Jenkins 执行测试。
- DRF、Vue、Jenkins、api-test runner 的设计必须支持容器网络、环境变量和可迁移路径。

## 2026-06-27 开发流程检查点与 subagent 并行评估

## 目标

在固定开发 loop 中补充架构影响评估、API 契约冻结、容器化兼容检查三个检查点，并分析是否允许在需求分析后通过 subagent 并行推进测试用例设计和 UI 原型设计。

## 阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 读取流程规则和 subagent 技能 | 完成 | 已读取根规则、阶段规则和 `subagent-driven-development` |
| 补充流程检查点 | 完成 | 已更新根规则和各阶段 AGENTS |
| 更新架构说明 | 完成 | 已说明串并行关系、汇合点和 subagent 适用范围 |
| 输出流程评价 | 进行中 | 分析哪些任务适合 subagent，哪些必须串行 |

## 初步判断

- 用户提出的“需求分析后并行测试用例和 UI 设计”总体合理，但前提是需求说明书中必须已经冻结角色、页面目标、核心字段、状态流转、权限边界、数据表草案和主要验收口径。
- UI 原型可以先参考需求说明书输出第一版，不必等待完整详细测试用例；但前端开发前必须同时对齐 UI 原型、后端 API 契约和功能测试用例。
- 后端开发不能只等 UI 原型，必须等待功能测试用例和 API 契约冻结。

## 2026-06-27 新版架构图与完整开发流程图

## 目标

根据当前最新架构方案，在 `project-info/project_detail/` 下重绘架构图，并新增一张覆盖完整项目开发过程的详细流程图。

## 产物

- 更新 `project-info/project_detail/project-architecture.drawio`
- 更新 `project-info/project_detail/project-architecture.png`
- 更新 `project-info/project_detail/project-architecture.drawio.png`
- 新增 `project-info/project_detail/execution-flow.drawio`
- 新增 `project-info/project_detail/execution-flow.png`
- 新增 `project-info/project_detail/execution-flow.drawio.png`

## 阶段

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 读取绘图规则和架构上下文 | 完成 | 已读取 drawio-skill、diagram-types、项目架构说明和目录规则 |
| 重绘新版架构图 | 完成 | 已体现 Compose 整体部署、Jenkins 主干、api-runner、DRF/Vue 边界和报告入口 |
| 新增完整开发流程图 | 完成 | 已体现需求、检查点、subagent 并行、TDD、联调验收和提交推送 |
| 校验与导出 | 完成 | 已校验 XML，导出普通 PNG 和可编辑 PNG |

## 错误记录补充

| 错误 | 处理 |
| --- | --- |
| 生成 draw.io XML 脚本首次执行时报 `NameError: name 'yellow' is not defined`，未写出文件 | 补充流程图样式变量后重新生成 |
| draw.io 批量导出曾返回退出码 1 但文件已生成且无错误文本 | 拆分检查文件、单条导出验证，确认最终 PNG 均可读；后续重新导出成功 |
| 流程图初版反馈线存在穿越警告 | 改为局部虚线提示节点，最终 `execution-flow.drawio` 校验 0 error、0 warning |
