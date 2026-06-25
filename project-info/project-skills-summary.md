# 当前项目 SKILL 使用说明

更新时间：2026-06-25

本文档用于说明 `AiApiTest-DWP` 项目当前推荐使用的 Codex SKILL、适用场景、组合方式和不建议默认启用的技能。后续 AI 或工程师接手项目时，应先阅读根目录 `AGENTS.md`，再按当前工作目录读取对应子目录 `AGENTS.md`。

## 1. 使用原则

- 项目级规则优先级高于单个 SKILL 的默认建议。
- 开发任务默认遵守根目录的多阶段 TDD 流程。
- 跨模块开发时优先使用全局统筹类技能，再叠加对应模块技能。
- 遇到测试失败、构建失败、接口异常或联调问题时，先使用系统化调试技能定位根因。
- 前端任务必须优先遵守 Vue 3、Vite、TypeScript、Vue Router、Pinia、Element Plus 的既有技术栈。
- 项目说明、架构图和流程图只沉淀到 `project-info/`，不要放运行产物、数据库导出或敏感配置。

## 2. 全局统筹执行类

| SKILL | 项目定位 | 使用场景 | 备注 |
| --- | --- | --- | --- |
| `using-superpowers` | 会话入口技能 | 每次开始任务时用于识别是否有适用技能 | 根目录标记为必须执行 |
| `planning-with-files` | 文件化计划与进度管理 | 复杂任务、多步骤开发、需要维护 `task_plan.md`、`findings.md`、`progress.md` 时 | 根目录标记为必须执行 |
| `test-driven-development` | 全项目 TDD 流程 | 新功能、Bugfix、阶段开发 | 与 10 阶段开发规则一致 |
| `brainstorming` | 需求和方案澄清 | 新阶段、大改动、跨模块设计、需求不明确时 | 不建议用于很小的修复任务 |
| `systematic-debugging` | 根因定位 | 测试失败、构建失败、Jenkins/DRF/Vue 联调异常 | 修复前先定位根因 |
| `receiving-code-review` | 处理评审意见 | 用户给出代码审查意见、需要判断建议是否合理时 | 避免盲目按评审文字修改 |
| `subagent-driven-development` | 独立任务并行执行 | 大型实现计划中存在可拆分并行任务时 | 当前项目可选，不作为默认技能 |

推荐组合：

| 场景 | 推荐组合 |
| --- | --- |
| 普通阶段开发 | `using-superpowers` + `planning-with-files` + `test-driven-development` |
| 新阶段方案设计 | `using-superpowers` + `planning-with-files` + `brainstorming` |
| 问题排查 | `systematic-debugging` + 对应模块技能 |
| 处理评审反馈 | `receiving-code-review` + 对应模块技能 |

## 3. 后端开发类

后端目录：`back-end/`

| SKILL | 项目定位 | 使用场景 | 备注 |
| --- | --- | --- | --- |
| `django-tdd` | Django/DRF 后端主技能 | 账户、权限、测试任务、失败用例、Jenkins API 开发 | 与 pytest-django、DRF 测试匹配 |
| `api-design` | REST API 设计 | URL、状态码、分页、过滤、错误响应、版本边界设计 | 适合 Stage 5-7 后端 API |
| `python-patterns` | Python 代码质量 | 服务层、工具函数、类型标注、异常处理、可维护性优化 | 用于实现和重构 |
| `python-testing` | pytest 测试策略 | fixture、mock、参数化、fake HTTP 响应、覆盖率补强 | 后端测试和 `api-test` 测试都可使用 |
| `systematic-debugging` | 后端问题排查 | Django 配置、MySQL、迁移、DRF 认证、Jenkins fake client 异常 | 建议补充到后端场景使用 |

推荐组合：

| 场景 | 推荐组合 |
| --- | --- |
| 新增 DRF API | `django-tdd` + `api-design` + `python-testing` |
| 后端实现和重构 | `django-tdd` + `python-patterns` |
| Jenkins 集成 API | `api-design` + `python-testing` + `systematic-debugging` |
| MySQL、迁移或测试失败 | `systematic-debugging` + `django-tdd` |

## 4. 前端开发类

前端目录：`front-end/`

当前项目使用 Vue 3、Vite、TypeScript、Vue Router、Pinia、Axios、Element Plus、Vitest 和 Vue Test Utils。前端任务应优先使用 Vue 官方相关技能。

| SKILL | 项目定位 | 使用场景 | 备注 |
| --- | --- | --- | --- |
| `vue-best-practices` | Vue 3 主技能 | 任意 `.vue`、Vue Router、Pinia、Vite with Vue 工作 | 前端目录标记为必须执行 |
| `frontend-design` | 前端界面设计与实现 | 页面、组件、布局、交互和视觉质量优化 | 前端目录标记为必须执行 |
| `vue-pinia-best-practices` | Pinia 状态管理 | 登录态、筛选条件、失败用例选择、任务状态 | 适合 `src/stores/` 和复杂页面状态 |
| `vue-router-best-practices` | Vue Router 4 | 登录守卫、平台路由、报告跳转、参数路由 | 适合 `src/router/` 和页面生命周期问题 |
| `vue-testing-best-practices` | Vue 测试 | Vitest、Vue Test Utils、组件测试、mock、异步渲染 | 适合 `front-end/tests/` |
| `vue-debug-guides` | Vue 调试 | 响应式、computed、watch、template、Teleport、异步问题 | 遇到前端异常时使用 |
| `create-adaptable-composable` | 可复用组合式函数 | 创建 `useXxx` composable，且入参需要支持普通值、ref、getter 时 | 按场景使用，不作为默认技能 |
| `ui-ux-pro-max` | UI/UX 质量检查 | 可访问性、表格、弹窗、表单、响应式、数据展示体验评审 | 可选，用于界面质量提升 |
| `ckm:design-system` | 设计系统和令牌 | CSS 变量、组件状态、设计令牌、组件规格整理 | 可选，用于统一主题和组件规范 |

推荐组合：

| 场景 | 推荐组合 |
| --- | --- |
| 新页面或新组件 | `vue-best-practices` + `frontend-design` |
| 登录态和状态管理 | `vue-best-practices` + `vue-pinia-best-practices` |
| 路由守卫和页面跳转 | `vue-best-practices` + `vue-router-best-practices` |
| 前端测试 | `test-driven-development` + `vue-testing-best-practices` |
| 前端异常排查 | `systematic-debugging` + `vue-debug-guides` |
| 抽取复用 composable | `vue-best-practices` + `create-adaptable-composable` |
| UI 体验优化 | `frontend-design` + `ui-ux-pro-max` |

不建议默认使用：

| SKILL | 原因 |
| --- | --- |
| `vue-options-api-best-practices` | 当前项目应使用 Composition API 和 `<script setup lang="ts">` |
| `vue-jsx-best-practices` | 当前项目以 Vue SFC 和 Element Plus 为主，不以 JSX 为默认写法 |

## 5. 项目信息、架构和图形类

目录：`project-info/`

| SKILL | 项目定位 | 使用场景 | 备注 |
| --- | --- | --- | --- |
| `drawio-skill` | 架构图和流程图主技能 | 架构图、执行流程图、ER 图、时序图、泳道图、可导出的正式图 | `project-info/AGENTS.md` 推荐使用 |
| `imagegen` | 位图生成辅助技能 | 展示型图片、概念图、封面图、视觉化说明图 | 适合生成 PNG，不适合作为架构真源 |
| `planning-with-files` | 分析整理支撑技能 | 项目总结、阶段复盘、交接材料、复杂说明文档整理 | 适合先梳理内容，再交给图形技能出图 |
| `brainstorming` | 架构方案澄清 | 架构重构、流程改造、图形表达方案不明确时 | 用于复杂设计前置澄清 |

推荐组合：

| 场景 | 推荐组合 |
| --- | --- |
| 项目架构说明书 | `planning-with-files` |
| 正式架构图或流程图 | `planning-with-files` + `drawio-skill` |
| 展示型图片 | `imagegen` |
| 架构调整方案 | `brainstorming` + `planning-with-files` |

## 6. SKILL 管理类

| SKILL | 项目定位 | 使用场景 | 备注 |
| --- | --- | --- | --- |
| `find-skills` | 查找新技能 | 用户明确要求查找、比较、安装外部技能时 | 日常开发不默认使用 |
| `skill-installer` | 安装技能 | 用户确认需要安装某个技能时 | 需要用户意图明确 |
| `skill-creator` | 创建或优化技能 | 编写项目专用技能、调整技能触发描述、优化技能内容时 | 当前环境存在系统版和用户版同名技能 |
| `plugin-creator` | 创建 Codex 插件 | 需要开发 Codex 插件时 | 当前项目日常开发不使用 |

## 7. 当前可用但非项目默认技能

| SKILL | 建议 |
| --- | --- |
| `openai-docs` | 仅在查询 OpenAI/Codex/API 官方文档时使用 |
| `find-skills` | 仅在用户明确要求搜索新技能时使用 |
| `skill-installer` | 仅在用户确认安装技能时使用 |
| `skill-creator` | 仅在创建或维护技能时使用 |
| `plugin-creator` | 当前项目不默认使用 |
| `ui-ux-pro-max` | 前端体验评审和优化时可用，不替代 `vue-best-practices` |
| `ckm:design-system` | 设计令牌和组件规范时可用，不替代 Element Plus 既有组件体系 |
| `create-adaptable-composable` | 只在创建可复用 Vue composable 时使用 |

## 8. 冲突和注意事项

| 情况 | 风险 | 建议 |
| --- | --- | --- |
| `brainstorming` 对所有任务强制使用 | 小修复会被过度流程化 | 只在复杂新需求、新阶段或跨模块设计时启用 |
| 同时加载过多前端设计技能 | 容易产生设计方向不一致 | Vue 任务以 `vue-best-practices` 为主，视觉质量再叠加 `frontend-design` |
| `imagegen` 用于架构源文件 | 位图不利于后续维护 | 正式架构图优先 `drawio-skill`，位图仅作展示输出 |
| `vue-options-api-best-practices` 用于当前前端默认开发 | 会偏离 Composition API 标准 | 仅维护 Options API 遗留代码时使用 |
| `vue-jsx-best-practices` 用于普通 SFC 页面 | 与当前 SFC 写法不匹配 | 仅在明确使用 Vue JSX 时使用 |
| `skill-creator` 同名重复 | 触发来源可能不清晰 | 使用时确认实际加载的技能内容 |

## 9. 快速选择表

| 我要做什么 | 先用哪些 SKILL |
| --- | --- |
| 开始一个复杂阶段任务 | `using-superpowers` + `planning-with-files` |
| 写新功能或修 Bug | `test-driven-development` + 对应模块技能 |
| 修复失败测试 | `systematic-debugging` + 对应测试技能 |
| 写 DRF API | `django-tdd` + `api-design` + `python-testing` |
| 写 Vue 页面 | `vue-best-practices` + `frontend-design` |
| 写 Pinia store | `vue-best-practices` + `vue-pinia-best-practices` |
| 写路由守卫 | `vue-best-practices` + `vue-router-best-practices` |
| 写前端测试 | `vue-testing-best-practices` + `test-driven-development` |
| 画架构图或流程图 | `planning-with-files` + `drawio-skill` |
| 生成展示图片 | `imagegen` |
| 处理评审意见 | `receiving-code-review` |

