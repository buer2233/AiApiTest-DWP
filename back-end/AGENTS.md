# back-end/AGENTS.md

本目录是 Django REST Framework 后端。进入 `back-end/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 后端开发-技能推荐

进行后端开发时推荐使用下面的技能：
- django-tdd：进行django后端开发时需要使用的TDD开发流程
- api-design：REST API 设计、状态码、分页、错误模型
- python-patterns：Python 风格、类型、健壮性和可维护性
- python-testing： pytest 策略、fixture、mock、参数化
- systematic-debugging：遇到问题或错误时推荐使用

## 模块职责

- 用户登录、登出、当前用户信息。
- `admin` 和 `member` 两类角色模型与权限入口。
- 测试任务、失败用例、重试任务、报告路径和执行日志数据。
- Jenkins job/build 查询、触发和 console log 查询 API。
- 对接 `api-test/tools/ci_runner.py` 或 Jenkins 产物，不重复实现 pytest 命令拼接和重试规则。

## 技术约定

- 使用 Django + Django REST Framework。
- 认证使用 DRF Token。
- 默认数据库为本地 MySQL。
- 配置从环境变量或本地私有配置读取，不提交真实凭据。
- 权限第一版可让 `admin` 和 `member` 权限一致，但代码结构要保留管理员专属权限入口。
- Jenkins client 测试必须使用 fake HTTP 响应，不依赖真实 Jenkins 服务。

## 目录约定

- `config/` 放 Django settings、urls 和全局配置。
- `apps/accounts/` 放用户、角色、认证和权限。
- `apps/test_runs/` 放测试任务、失败用例、报告和 Allure 解析。
- `apps/jenkins_integration/` 放 Jenkins client、模型和 API。
- `tests/` 放后端 pytest 测试。

## TDD 要求

- Stage 5 先写账户和角色测试，再创建 Django 工程和 accounts app。
- Stage 6 先写测试任务、失败用例和 Allure 解析测试，再实现模型和 API。
- Stage 7 先写 Jenkins client/API 测试，使用 fake HTTP 响应，再实现 Jenkins 集成。

## 禁止事项

- 不提交真实数据库密码、Jenkins URL、Jenkins 用户名、API token。
- 不在后端复制 `api-test` 的失败重试实现。
- 不把运行产物、报告 HTML 或 console log 当作业务代码提交。
