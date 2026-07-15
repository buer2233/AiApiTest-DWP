# front-end/AGENTS.md

本目录是 Vue 3 前端。进入 `front-end/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- `front-end/` 是企业级管理后台，负责模块通过率、失败用例、Jenkins 任务、Allure 报告入口和平台操作体验。
- 前端只调用 DRF API，不直接调用 Jenkins、pytest、Allure 命令或本地脚本。
- 前端不保存敏感凭据，不实现后端权限判定，只做用户体验和必要的前端状态保护。

## 固定 loop 中的位置

- 前端开发属于固定 loop 第 5 阶段。
- 开发前必须存在同一需求命名的需求说明书、功能测试用例、UI 原型图和已确认的后端 API 契约。
- 如果 UI 原型是与测试用例并行产出的，开发前必须确认 UI 原型已依据完整功能测试用例完成覆盖校准。
- 如果 UI 原型或主人标注图是复合图，开发前必须确认 `project-info/UI/` 已输出区域语义拆解表和前端实现映射表，明确哪些区域是当前页面、点击后路由、弹窗、登录后页面、设计说明层或不实现内容。
- 开发前必须确认容器化兼容检查已完成，前端 API 地址、报告入口、静态资源路径和环境变量不能绑定个人本机配置。
- 开发顺序必须是：先编写 Playwright 自然语言 UI 自动化测试用例，再开发页面和组件，再回归测试。
- 组件内部逻辑复杂时，应补充 Vitest + Vue Test Utils 单元测试。
- 阶段完成必须留存 Playwright 运行结果与关键页面截图证据，并补全 `需求名-可追溯矩阵.md` 的前端实现列。
- 页面实现完成后必须经过独立对抗审查（review subagent，可用 `receiving-code-review`），并由 agent 聚合 `需求名-验收包.md` 交主人终审。自主流水线整体执行方式见 `docs/自主开发流水线.md`。

## 技能推荐

- 必须优先使用：`vue-best-practices`、`frontend-design`。
- 推荐使用：`ui-ux-pro-max`、`vue-router-best-practices`、`vue-pinia-best-practices`、`vue-testing-best-practices`、`vue-debug-guides`、`ckm:design-system`。

## 技术栈

- Vue 3 + Vite + TypeScript。
- Element Plus 作为组件库。
- Vue Router 管理路由。
- Pinia 管理全局状态。
- Axios 封装 HTTP 请求。
- TanStack Query for Vue 管理服务端状态、缓存和刷新。
- Vitest + Vue Test Utils 做组件和组合式函数测试。
- Playwright 做端到端 UI 自动化测试。

## 模块职责

- 登录页、登录态、当前用户信息和权限感知导航。
- 平台基础布局、顶部导航、侧边菜单和页面容器。
- 模块通过率列表，展示模块快照、通过率、通过数、失败数、错误数、运行时间和报告入口。
- 失败用例页面或弹窗，支持筛选、查看详情、状态切换、选择失败用例和触发重试。
- Jenkins 任务列表、任务状态、job/build 链接、console log 入口和 Allure 报告入口。

## UI 和交互规则

- 管理后台应保持安静、清晰、可扫描，不做营销式落地页。
- 前端实现必须严格遵守仓库根目录 `DESIGN-claude.md` 中定义的前端设计风格和前端样式风格；该文件是视觉实现的强制基线，而不是可选参考。
- 视觉落地必须以可维护的主题变量实现，优先沉淀为 Element Plus 主题变量、全局 CSS 变量和局部组件 token，不允许在页面内散落不可追踪的硬编码颜色。
- 推荐基线必须从 `DESIGN-claude.md` 映射到代码：warm cream canvas、coral primary、dark product surface、warm ink text、hairline border、8px 内主控件圆角、清晰字号层级和稳定留白。
- 新增或修改页面时，必须先核对同名 UI 原型中的 Figma 导出图或 Codex `imagegen` 原型图片；没有高保真视觉产物时，不得直接进入前端页面实现。
- 高保真图片是视觉参考和交互输入，不等于“整张图一比一写成一个页面”。实现前必须把 UI 原型中的区域拆成路由、页面、组件、弹窗和状态；只有映射到当前 route / 当前状态的区域才能在当前页面渲染。
- 图片中的说明文字、红框、箭头、对比批注、区域标签和“这里不显示”这类设计标注，必须视为设计标注层，不得写入产品 UI DOM，也不得作为最终页面截图的一部分。
- 如果同一张图同时包含登录页、注册页、登录后页面、详情页或权限态，必须按用户路径拆分实现：登录页只显示登录所需内容；注册页或弹窗只在点击注册链接后出现；登录后页面只在鉴权成功后进入受保护路由；错误/权限态只在对应状态触发后展示。
- 实现阶段必须在代码审查或验收包中记录 `DESIGN-claude.md` 对齐结果，包括色彩 token、字体层级、间距、圆角、状态色、响应式和 Do/Don't 禁止项。
- 数据密集页面仍优先效率和可扫描性：筛选区、表格、分页、批量操作和详情抽屉需要紧凑但清楚，不做大面积宣传式 hero、装饰渐变、浮夸卡片或无业务含义的插画。
- 成功、失败、警告、禁用、加载和权限态必须保持清晰语义；暖陶土色只作为品牌/主操作强调，不替代错误红、成功绿、警告黄等状态表达。
- 新增页面或组件必须先对齐 `project-info/UI/` 中同名 UI 原型的 Claude 风格说明；如果实现阶段调整视觉规范，应先回写 UI 原型和交互说明，并说明是否影响 `DESIGN-claude.md` 基线。
- 表格、筛选、分页、批量操作、加载态、空状态、错误态和权限态必须完整。
- 失败用例界面只展示状态为 `失败` 和 `跳过` 的记录。
- 手动状态修改只支持在 `失败` 和 `跳过` 之间切换，并明确提示通过率影响。
- 重试操作必须有确认、提交中、成功、失败和可恢复反馈。

## 原型到前端的落地映射门禁

进入编码前，前端阶段必须基于 UI 原型补齐一份简短映射，可写入前端实现说明、RTM 或验收包：

| 字段 | 要求 |
| --- | --- |
| UI 区域编号 | 沿用 UI 原型中的 `R1`、`R2` 等编号 |
| 用户路径 | 例如登录初始页、点击注册、登录成功后、无权限访问 |
| Vue route | 明确路由，如 `/login`、`/register`、`/cases/:id` |
| 组件落点 | 明确 Vue 组件或弹窗组件 |
| 初始是否可见 | 当前页面初始渲染时是否出现 |
| Playwright 断言 | 至少覆盖“应该出现”和“不应该同屏出现”的关键断言 |

使用复合登录图时，必须按以下方式拆分：

- 左上登录区域：只作为 `/login` 初始可见登录界面。
- 中间说明区域：如果 UI 原型标为设计说明，则不进入前端。
- 右上注册区域：作为点击“使用邀请码注册”后的 `/register` 页面或注册弹窗。
- 底部登录后区域：作为登录成功后的受保护业务页面，例如用例详情页，不得出现在登录页。

## 禁止事项

- 不提交真实账号、密码、token、cookie、生产 URL 或敏感地址。
- 不在前端写死 Jenkins 地址、租户信息或业务模块常量。
- 不绕过 DRF 后端直接访问 Jenkins 或静态运行产物。
- 不写死宿主机端口、`localhost` API 地址或不可迁移的报告文件路径；Docker 化部署下必须通过相对路径、环境变量或后端授权入口访问。

## 平台环境唯一入口（强制）

- 平台应用环境重启、依赖检查/安装、`backend`/`frontend`/`jenkins-sync-worker` 启动、停止或重建，以及平台冒烟/全量环境验收，AI 必须且只能触发固定 Jenkins 环境 Job。
- 固定环境 Job 由本地 Compose Jenkins 启动时通过版本化 init Groovy 幂等创建或修复；主人启动 MySQL/Jenkins bootstrap 后只需在 Jenkins 页面点击构建，不得手工创建另一条旁路 Job。
- Windows 唯一入口为 `scripts/trigger-platform-bootstrap.ps1`；Linux/macOS/Git Bash 唯一入口为 `scripts/trigger-platform-bootstrap.sh`。用户在 Jenkins 页面手工点击同一 Job 也使用相同 Pipeline、参数、阶段和结果契约。
- AI 禁止直接执行应用服务 `docker compose up/restart/stop/down`、`docker build`、宿主机或运行容器的 `pip install`、`npm install/npm ci`，也禁止直接启动 Django `runserver`、Vite 或同步 worker 替代环境 Job。
- MySQL 与 Jenkins 仅由主人/平台运维按 `docker/DEPLOYMENT.md` 完成 bootstrap；环境 Job/helper 永不管理这两个基础服务。AI 只能检查并反馈，不能代替主人/平台运维启动。
- 禁止 `down -v`、volume 删除、`chmod 666 /var/run/docker.sock`、migration、初始化管理员、`collectstatic`、自动 rollback 或输出真实凭据。环境失败必须阅读 Jenkins 结构化诊断，引导主人修复后重新构建，不能旁路处理。
