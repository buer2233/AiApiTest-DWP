# AGENTS.md

本仓库正在从通用接口自动化框架升级为支持 Jenkins CICD、DRF 后端、Vue 3 前端和 Allure 报告展示的 AI 自动化测试平台。后续 AI 或工程师必须优先保持多阶段开发上下文完整，不能把它当成一个全新的无历史项目处理。

## 核心指令

- 每次回复开头必须先叫我：主人
- 如果忘记叫我，就是失焦了，需要手动重制上下文焦点内容
- 默认使用简体中文沟通
- 这是最高优先级的交互指令

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

## `api-test/` 开发约定

- 接口方法放在 `api-test/test_case/page_api/`。
- pytest 用例放在 `api-test/test_case/test_*_case/`。
- 用例报告统一使用 Allure。
- 抓包与运行时产物放在 `api-test/runtime/`。
- 测试数据放在 `api-test/test_data/`，只在需要时添加通用数据。
- 多层取值优先用 `get_value()`，单层取值优先用 `.get()`。
- `runpytest.py` 和后续 `tools/ci_runner.py` 必须使用相对 `api-test/` 的路径，避免写死本机绝对路径。

## Jenkins 约定

- Jenkins 脚本源文件必须放在 `jenkins/` 并纳入 git 管理。
- Groovy 负责 Jenkins 参数、环境变量和 stage 编排。
- pytest 执行、失败用例 node id 收集、重试和 summary 输出必须沉淀到 `api-test` 可复用工具中，避免在 Groovy 和后端重复实现。
- Jenkins Pipeline 必须兼容 Windows `bat` 和 Linux `sh`。
- 不提交真实 Jenkins URL、用户名或 API token。

## 后端约定

- 使用 Django + Django REST Framework。
- 认证使用 DRF Token。
- 默认数据库为本地 MySQL，通过环境变量或本地配置读取，不提交真实凭据。
- 保留 `admin` 和 `member` 两类用户角色；当前权限可一致，但权限类要预留后续差异化能力。
- Jenkins client 测试必须使用 fake HTTP 响应，不依赖真实 Jenkins。

## 前端约定

- 使用 Vue 3、Vite、TypeScript、Vue Router、Pinia、Axios、Element Plus。
- 默认展示可操作测试平台，不做营销落地页。
- 页面围绕模块通过率、失败用例、重试入口、Jenkins 任务和 Allure 报告入口设计。
- 保持平台字段通用，不引入具体公司业务模块常量。

## 文档与记录

- 开发和测试中产生的文档统一放入 `docs/`。
- 每次阶段性动作后更新主计划文件的阶段进度记录。
- 重要发现写入 `findings.md`。
- 执行动作、测试命令和结果写入 `progress.md`。
- 阶段文档必须包含：范围、实现内容、测试命令、测试结果、已知问题、后续建议。
