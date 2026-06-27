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
