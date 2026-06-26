# AGENTS.md

本仓库正在从通用接口自动化框架升级为支持 Jenkins CICD、DRF 后端、Vue 3 前端和 Allure 报告展示的 AI 自动化测试平台。后续 AI 或工程师必须优先保持多阶段开发上下文完整，不能把它当成一个全新的无历史项目处理。

## 核心指令

- 每次回复开头必须先叫我：主人
- 如果忘记叫我，就是失焦了，需要手动重制上下文焦点内容
- 默认使用简体中文沟通
- 开发过程中需要添加详细的简体中文注释
- 这是最高优先级的交互指令

## 全局统筹执行类-技能推荐

必须执行的技能： /using-superpowers， /planning-with-files

其它全局统筹执行时推荐使用的技能：
- do：标准的开发流程
- test-driven-development：整个项目的所有开发过程都需要遵循测试驱动开发的模型
- brainstorming：在新任务之前必须使用，探索和深挖用户意图和需求、设计
- systematic-debugging：遇到问题或错误时推荐使用
- receiving-code-review：代码审查时推荐使用

## AGENTS 分层规则

- 根目录 `AGENTS.md` 只维护全局项目规则、阶段流程、敏感信息限制、沟通规则和跨模块边界。
- `api-test/`、`back-end/`、`front-end/`、`jenkins/` 下的 `AGENTS.md` 维护各自模块的技术栈、命令、目录约定和注意事项。
- 子目录规则可以更具体，但不能和根目录规则冲突。
- `CLAUDE.md` 只保留对同级 `AGENTS.md` 的引用，即 `@AGENTS.md`。以后修改协作规则时优先改 `AGENTS.md`，不要在 `CLAUDE.md` 复制规则。

## 当前产品定位

项目目标是建设一个可持续演进的 CICD AI 自动化测试平台：

- `api-test/`：接口自动化执行核心，基于 pytest、requests、allure-pytest，负责接口方法、pytest 用例、失败 node id、重试执行器和 Allure 结果。
- `jenkins/`：Jenkins Pipeline 和 Groovy 脚本，负责在 Windows/Linux Jenkins agent 上调用 `api-test`，归档运行产物并发布 Allure 报告。
- `back-end/`：Django REST Framework 后端，负责用户登录、角色、测试任务、失败用例、报告入口、Jenkins 查询和触发 API。
- `front-end/`：Vue 3 + Vite + TypeScript + Element Plus 前端，负责模块通过率、失败用例弹窗、失败重试、Jenkins 任务入口和报告入口。
- `project-info/`：项目说明资料统筹目录，只负责沉淀需求、原型、测试用例、架构图和流程图等项目交接资料，不存放业务实现代码或运行产物。
- `docs/`：存放额外的文档内容

本项目仍然保持通用测试平台定位，不绑定任何具体业务系统。新增内容不得提交真实账号、密码、token、cookie、租户密钥、生产地址或不可迁移的业务常量。

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

## 按需读取的参考内容

- docker快速部署：AI 需要执行或说明 Docker 部署时，按需读取 `docker/DEPLOYMENT.md`，并以该文件为准。
- 快速启动项目环境：AI 需要快速启动当前项目的所有依赖环境时，按需读取 `project-info/quick-start-all-services.md`

## Git 规则

- 每个阶段完成后必须单独 `git commit` 和 `git push`。

## 减少常见 LLM 编码错误的行为准则
可根据项目特定需求合并使用： @andrej-karpathy-skills.md

