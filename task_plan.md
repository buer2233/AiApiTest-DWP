# Task Plan: CICD and Web Test Platform Design

## Goal
与用户共同设计接口自动化框架的 CICD 和网页端测试平台能力，用户确认需求后再按 TDD 开发。

## Current Phase
Phase 4: TDD Implementation - Stage 7 complete, ready for commit and push

## Phases

### Phase 1: Requirements Brainstorming
- [x] 读取用户项目约束和指定技能
- [x] 确认本阶段只做需求设计，不写业务实现
- [x] 梳理现有框架能力边界
- [x] 输出第一轮需求模型和关键问题
- [x] 根据用户反馈迭代需求
- [x] 创建大型开发计划文档
- [x] 将 `AGENTS.md` 和 `README.md` 从旧接口自动化框架描述更新为 CICD AI 自动化测试平台描述
- [x] 将后续 AI 接手规则、主计划入口和多阶段开发记录要求写入核心文档
- **Status:** in_progress

### Phase 2: Requirement Confirmation
- [x] 固化功能范围、角色、流程、边界条件
- [x] 明确 MVP 与后续增强范围
- [x] 明确技术约束和验收标准
- [x] 获取用户确认
- **Status:** complete

### Phase 3: Technical Design
- [ ] 设计后端服务、任务模型、Jenkins 集成、报告存储
- [ ] 设计网页端页面和交互
- [ ] 设计数据库/文件存储结构
- [ ] 设计 API 合约和错误处理
- **Status:** pending

### Phase 4: TDD Implementation
- [x] Stage 2 先写失败测试
- [x] Stage 2 验证 RED
- [x] Stage 2 迁移接口测试框架并修复入口
- [x] Stage 2 验证 GREEN
- [x] Stage 2 回归运行 demo 用例
- [x] Stage 2 git commit
- [x] Stage 2 git push
- [x] Stage 3 需求分析和验收标准记录
- [x] Stage 3 先写 `pytest_nodeids` 和 `ci_runner` 失败测试
- [x] Stage 3 验证 RED
- [x] Stage 3 实现 node id 读取、失败重试执行器和 summary 输出
- [x] Stage 3 验证 GREEN
- [x] Stage 3 运行真实执行器烟测
- [x] Stage 3 git commit
- [x] Stage 3 git push
- [x] Stage 4 需求分析和验收标准确认
- [x] Stage 4 先写 Jenkins 参数兼容测试和 Pipeline 静态测试
- [x] Stage 4 验证 RED
- [x] Stage 4 实现 `ci_runner` Jenkins env 适配、Jenkinsfile 和 Groovy Pipeline
- [x] Stage 4 验证 GREEN
- [x] Stage 4 编写 `docs/jenkins-pipeline.md`
- [x] Stage 5 需求分析和验收标准确认
- [x] Stage 5 先写登录、角色和权限测试
- [x] Stage 5 验证 RED
- [x] Stage 5 创建 Django/DRF 工程和 accounts app
- [x] Stage 5 验证 GREEN
- [x] Stage 5 编写 `docs/back-end-accounts.md`
- [x] Stage 5 git push 已重新执行成功，`main` 与 `origin/main` 已同步
- [x] Stage 6 需求分析和验收标准确认
- [x] Stage 6 先写测试任务 API 和 Allure 解析失败测试
- [x] Stage 6 验证 RED
- [x] Stage 6 实现 `test_runs` 模型、runner 适配、Allure 解析和 DRF API
- [x] Stage 6 验证 GREEN
- [x] Stage 6 编写 `docs/test-runs-api.md`
- [x] Stage 6 git commit
- [x] Stage 6 git push
- [x] Stage 7 需求分析和验收标准确认
- [x] Stage 7 先写 Jenkins client/API 失败测试
- [x] Stage 7 验证 RED
- [x] Stage 7 实现 Jenkins client、参数转换、查询/触发 API 和触发记录模型
- [x] Stage 7 验证 GREEN
- [x] Stage 7 编写 `docs/jenkins-api.md`
- **Status:** complete

### Phase 5: Verification and Delivery
- [ ] 运行相关自动化测试
- [ ] 验证报告生成和平台流程
- [ ] 总结改动和后续建议
- **Status:** pending

## Key Questions
1. 网页端测试平台是新增在本仓库内，还是对接已有平台？
2. 是否必须对接真实 Jenkins，还是先实现可替换的 Jenkins 客户端与本地模拟？
3. 用例执行的最小闭环是本地 pytest，Jenkins job，还是两者都需要？
4. 错误重试粒度是单个 pytest 用例、一次测试任务、失败接口请求，还是都要支持？
5. Allure 报告是直接展示静态 HTML，还是平台解析并展示聚合数据？
6. 是否需要用户/角色/权限、项目空间、多环境配置？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 先需求共创，后实现 | 用户明确要求确认需求通过后再使用 TDD 开发 |
| 当前阶段不引入具体业务系统常量 | 遵守项目通用接口自动化框架约束 |
| 需求设计要区分 MVP 与扩展能力 | 避免 CICD、平台、Jenkins、报告能力一次性过大导致交付失焦 |
| 按用户要求先实现 Jenkins，再开发网页测试平台 | Jenkins 是用户明确要求的第一步核心能力 |
| 将开发计划写入 `docs/superpowers/plans/2026-06-22-cicd-test-platform.md` | 后续每个阶段都在同一文档更新任务和进度 |
| 每个阶段独立执行需求分析、测试、开发、验证、提交、推送 | 用户明确要求每阶段单独开发并严格执行 TDD、`git commit`、`git push` |
| DRF 使用 Token 认证，本地 MySQL 作为默认数据库 | 用户已确认后端基础工程选型 |
| Vue 3 前端使用 Element Plus | 用户已确认前端组件库 |
| Allure 报告第一版打开静态 HTML | 用户已确认报告展示方式 |
| `AGENTS.md` 和 `README.md` 作为后续 AI 接手入口，必须优先体现 CICD 测试平台定位 | 用户明确要求避免新 AI 丢失开发任务记录和要求 |
| Stage 3 在 `api-test/tools/` 中沉淀统一执行器 | 后续 Jenkins 和 DRF 都复用同一执行入口，避免重试逻辑分叉 |
| 执行器运行前清理旧 pytest `lastfailed` cache | 防止历史失败 node id 污染当前运行 summary |
| Stage 5 所有环境强制使用本地 MySQL `localhost:3306` | 用户明确要求数据库连接不再回退 SQLite 或覆盖到其他主机端口 |
| `create_superuser()` 默认写入 `role=admin` | 满足“可创建管理员”的验收，同时普通用户默认仍为 `member` |
| Stage 6 后端通过 `ApiTestRunner` 适配 `api-test/tools/ci_runner.py` | 避免在 DRF 中复制 pytest 命令和重试规则 |
| Stage 6 报告 API 只返回 `/reports/<run_id>/` 入口，不暴露服务器绝对路径 | 满足报告入口需求，同时把静态 HTML 服务留到 Stage 10 |
| Stage 7 Jenkins client 使用 `requests.Session` 并支持注入 fake session | 真实运行可调用 Jenkins，测试可完全隔离外部服务 |
| Stage 7 后端触发 API 将前端字段转换为 Stage 4 Pipeline 大写参数 | 保持 Jenkins Pipeline、后端和后续前端的参数契约一致 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| None | 1 | N/A |
| Stage 3 初始 RED: `ModuleNotFoundError: No module named 'tools'` | 1 | 创建 `api-test/tools/__init__.py`、`pytest_nodeids.py`、`ci_runner.py` |
| Stage 3 补强 RED: 旧 `lastfailed` 污染当前运行产物 | 1 | 在解析重试目标后、执行 pytest 前清理旧 cache |
| Stage 3 补强 RED: `retry_count=-1` 未被拒绝 | 1 | 在命令构造和 CLI 入口增加非负校验 |
| Stage 4 初始 RED: Jenkins env 适配函数不存在 | 1 | 新增 `parse_jenkins_node_ids()` 和 `build_run_request_from_jenkins_env()` |
| Stage 4 初始 RED: Jenkinsfile/Groovy Pipeline 不存在 | 1 | 创建 `jenkins/Jenkinsfile` 和 `jenkins/scripts/api-test-pipeline.groovy` |
| Stage 4 补强 RED: pytest 失败会中断归档阶段 | 1 | `Run API Tests` 使用 `catchError`，失败后继续归档和发布 Allure |
| Stage 5 初始 RED: Django settings 未配置 | 1 | 创建 `back-end/config`、`manage.py`、`pytest.ini` 和 accounts app |
| Stage 5 环境错误: `--reuse-db` 无法识别 | 1 | 安装 `back-end/requirements.txt` 补齐 `pytest-django` |
| Stage 5 补强 RED: `create_superuser()` 默认 role 为 `member` | 1 | 新增自定义 `UserManager` 和 manager 迁移 |
| Stage 5 MySQL 检查 warning: 默认数据库不存在 | 1 | 文档记录本地 MySQL 建库命令 |
| Stage 5 数据库配置 RED: pytest 下仍回退 SQLite | 1 | 删除 pytest SQLite 分支，强制 `django.db.backends.mysql`、`localhost:3306` |
| Stage 6 初始 RED: `ModuleNotFoundError: No module named 'apps.test_runs'` | 1 | 创建 `apps.test_runs` app、模型、服务、序列化器、视图和 URL |
| Stage 6 MySQL 迁移错误: `Specified key was too long` | 1 | 移除 `(test_run, node_id)` 唯一约束，保留长 pytest node id 存储能力 |
| Stage 6 复用测试库残留: `Table 'test_runs_testrun' already exists` | 1 | 使用 `--create-db` 重建 MySQL 测试库后继续验证 |
| Stage 7 初始 RED: `ModuleNotFoundError: No module named 'apps.jenkins_integration'` | 1 | 创建 `apps.jenkins_integration` app、client、serializers、views、urls 和迁移 |

## Notes
- 默认使用简体中文沟通。
- 开发阶段必须遵守 TDD：生产代码前先写失败测试。
- 不提交真实账号、密码、token、cookie 或敏感地址。
