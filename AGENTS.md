# AGENTS.md

本仓库正在从通用接口自动化框架升级为支持 Jenkins CICD、DRF 后端、Vue 3 前端和 Allure 报告展示的 AI 自动化测试平台。后续 AI 或工程师必须优先保持多阶段开发上下文完整，不能把它当成一个全新的无历史项目处理。

## 核心指令

- 每次回复开头必须先叫我：主人
- 如果忘记叫我，就是失焦了，需要手动重制上下文焦点内容
- 默认使用简体中文沟通
- 这是最高优先级的交互指令

## 全局统筹执行类-技能推荐

必须执行的技能： /using-superpowers， /planning-with-files

其它全局统筹执行时推荐使用的技能：
- test-driven-development：整个项目的所有开发过程都需要遵循测试驱动开发的模型
- brainstorming：在新任务之前必须使用，探索和深挖用户意图和需求、设计
- systematic-debugging：遇到问题或错误时推荐使用
- receiving-code-review：代码审查时推荐使用

## AGENTS 分层规则

- 根目录 `AGENTS.md` 只维护全局项目规则、阶段流程、敏感信息限制、沟通规则和跨模块边界。
- `api-test/`、`back-end/`、`front-end/`、`jenkins/` 下的 `AGENTS.md` 维护各自模块的技术栈、命令、目录约定和注意事项。
- 子目录规则可以更具体，但不能和根目录规则冲突。
- `CLAUDE.md` 只保留对同级 `AGENTS.md` 的引用，即 `@AGENTS.md`。以后修改协作规则时优先改 `AGENTS.md`，不要在 `CLAUDE.md` 复制规则。
- 进入某个子目录工作时，先读根目录 `AGENTS.md`，再读该子目录 `AGENTS.md`。

## 当前产品定位

项目目标是建设一个可持续演进的 CICD AI 自动化测试平台：

- `api-test/`：接口自动化执行核心，基于 pytest、requests、allure-pytest，负责接口方法、pytest 用例、失败 node id、重试执行器和 Allure 结果。
- `jenkins/`：Jenkins Pipeline 和 Groovy 脚本，负责在 Windows/Linux Jenkins agent 上调用 `api-test`，归档运行产物并发布 Allure 报告。
- `back-end/`：Django REST Framework 后端，负责用户登录、角色、测试任务、失败用例、报告入口、Jenkins 查询和触发 API。
- `front-end/`：Vue 3 + Vite + TypeScript + Element Plus 前端，负责模块通过率、失败用例弹窗、失败重试、Jenkins 任务入口和报告入口。
- `docs/`：所有开发计划、阶段记录、接口设计、测试结果、运行手册和问题记录。

本项目仍然保持通用测试平台定位，不绑定任何具体业务系统。新增内容不得提交真实账号、密码、token、cookie、租户密钥、生产地址或不可迁移的业务常量。

## 必读上下文

任何后续 AI 接手开发、修复或文档更新前，必须先读取以下文件：

1. `docs/superpowers/plans/2026-06-22-cicd-test-platform.md`
2. `task_plan.md`
3. `findings.md`
4. `progress.md`
5. `README.md`

其中 `docs/superpowers/plans/2026-06-22-cicd-test-platform.md` 是主开发计划和阶段进度来源。不要另起一个全新的计划文件来替代它，除非用户明确要求。

## 多阶段开发规则

本项目按 10 个阶段推进，每个阶段必须独立完成需求分析、测试、开发、验证、文档、提交和推送：

1. 需求冻结与计划确认
2. `api-test/` 迁移与充分测试
3. pytest node id 与失败重试执行器
4. Jenkins Groovy Pipeline
5. DRF 后端基础工程与用户角色
6. 测试任务与失败用例 API
7. Jenkins 查询与触发 API
8. Vue 3 前端基础与登录
9. 模块通过率与失败用例页面
10. 报告展示、联调、文档和交付

每个阶段必须遵守 TDD：

1. 明确本阶段范围、输入、输出、验收标准和不做事项。
2. 先写自动化测试。
3. 运行精确测试命令，确认 RED。
4. 编写最小实现。
5. 运行测试确认 GREEN。
6. 必要时重构，并再次运行测试。
7. 更新 `docs/`、`task_plan.md`、`findings.md`、`progress.md` 和主计划文件。
8. 阶段完成后单独执行 `git commit`。
9. 提交后执行 `git push`，失败则记录原因。

禁止跨阶段混合大批量实现。发现当前工作区已有未提交改动时，先用 `git status --short` 确认范围，不能回滚用户或其他 AI 已做的改动。

## 模块边界

- `api-test/` 只负责接口自动化执行能力、pytest node id、失败重试执行器和 Allure 原始结果。
- `jenkins/` 只负责 Jenkins Pipeline 参数、stage 编排、Windows/Linux 兼容和产物归档。
- `back-end/` 只负责 DRF API、用户角色、任务数据、失败用例数据、Jenkins 查询/触发和报告入口。
- `front-end/` 只负责 Vue 3 测试平台界面、登录态、模块通过率、失败用例操作和报告入口。
- 跨模块逻辑必须优先沉淀到最合适的单一模块，避免 Jenkins、后端和前端重复实现同一规则。

## 全局安全规则

- 不提交真实账号、密码、token、cookie、租户密钥、Jenkins API Token、生产 URL 或敏感地址。
- 示例配置使用占位符、环境变量或本地私有配置。
- 报告、日志、抓包、运行时产物不要作为业务代码提交。
- Jenkins、DRF、Vue 和 pytest 中都保持平台字段通用，不引入具体公司业务模块常量。

## Docker 快速部署规则

AI 需要执行或说明 Docker 部署时，按需读取 `docker/DEPLOYMENT.md`，并以该文件为准。

## 文档与记录

- 开发和测试中产生的文档统一放入 `docs/`。
- 每次阶段性动作后更新主计划文件的阶段进度记录。
- 重要发现写入 `findings.md`。
- 执行动作、测试命令和结果写入 `progress.md`。
- 阶段文档必须包含：范围、实现内容、测试命令、测试结果、已知问题、后续建议。
- 项目架构说明书参考: `/project-info/项目架构说明书.md`

## Git 规则

- 每个阶段完成后必须单独 `git commit` 和 `git push`。

## 减少常见 LLM 编码错误的行为准则
可根据项目特定需求合并使用： @andrej-karpathy-skills.md

