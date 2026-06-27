# front-end/AGENTS.md

本目录是 Vue 3 前端。进入 `front-end/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- `front-end/` 是企业级管理后台，负责模块通过率、失败用例、Jenkins 任务、Allure 报告入口和平台操作体验。
- 前端只调用 DRF API，不直接调用 Jenkins、pytest、Allure 命令或本地脚本。
- 前端不保存敏感凭据，不实现后端权限判定，只做用户体验和必要的前端状态保护。

## 固定 loop 中的位置

- 前端开发属于固定 loop 第 5 阶段。
- 开发前必须存在同一需求命名的需求说明书、功能测试用例、UI 原型图和已确认的后端 API 契约。
- 开发顺序必须是：先编写 Playwright 自然语言 UI 自动化测试用例，再开发页面和组件，再回归测试。
- 组件内部逻辑复杂时，应补充 Vitest + Vue Test Utils 单元测试。

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
- 前端默认视觉风格参考 `https://getdesign.md/claude/design-md` 对 Claude 的公开设计分析：暖陶土色强调、干净编辑式布局、温和理性的 AI 产品气质。
- 视觉落地必须以可维护的主题变量实现，优先沉淀为 Element Plus 主题变量、全局 CSS 变量和局部组件 token，不允许在页面内散落不可追踪的硬编码颜色。
- 推荐基线：温暖中性色页面背景、炭黑/深灰正文、暖陶土色主按钮和关键操作强调、浅色边框、克制阴影、8px 以内圆角、清晰字号层级和稳定留白。
- 数据密集页面仍优先效率和可扫描性：筛选区、表格、分页、批量操作和详情抽屉需要紧凑但清楚，不做大面积宣传式 hero、装饰渐变、浮夸卡片或无业务含义的插画。
- 成功、失败、警告、禁用、加载和权限态必须保持清晰语义；暖陶土色只作为品牌/主操作强调，不替代错误红、成功绿、警告黄等状态表达。
- 新增页面或组件必须先对齐 `project-info/UI/` 中同名 UI 原型的 Claude 风格说明；如果实现阶段调整视觉规范，应先回写 UI 原型和交互说明。
- 表格、筛选、分页、批量操作、加载态、空状态、错误态和权限态必须完整。
- 失败用例界面只展示状态为 `失败` 和 `跳过` 的记录。
- 手动状态修改只支持在 `失败` 和 `跳过` 之间切换，并明确提示通过率影响。
- 重试操作必须有确认、提交中、成功、失败和可恢复反馈。

## 禁止事项

- 不提交真实账号、密码、token、cookie、生产 URL 或敏感地址。
- 不在前端写死 Jenkins 地址、租户信息或业务模块常量。
- 不绕过 DRF 后端直接访问 Jenkins 或静态运行产物。
