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


