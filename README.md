# AiApiTest-DWP

`AiApiTest-DWP` 是一个面向 AI 协作的企业级自动化测试平台，采用单仓库管理接口自动化、Jenkins 流水线、DRF 后端、Vue 3 前端、Docker 基础设施和项目交接资料。

平台执行主干固定为 Jenkins：所有测试执行、模块重试、失败重试和报告生成都通过 Jenkins 调用 `api-test` 完成；DRF 负责平台数据、权限、任务编排和状态同步；Vue 3 前端负责测试管理界面。

本项目保持通用测试平台定位，不提交真实账号、密码、token、cookie、Jenkins API Token、生产地址或不可迁移的业务常量。

## Jenkins 结果自动同步

DRF 后端提供独立轻量同步进程，用于自动同步运行中任务并发现各模块的每日全量构建：

```powershell
cd back-end
python manage.py sync_jenkins_results --once
python manage.py sync_jenkins_results --watch
python manage.py sync_jenkins_results --watch --interval 10
```

`--watch` 默认读取根目录 `.env` 中的 `JENKINS_BUILD_POLL_INTERVAL_SECONDS`。该进程复用后端数据库与 Jenkins 私有配置，不使用浏览器 Cookie，不直接执行 pytest；本地开发建议只启动一个实例，重复实例仍通过数据库唯一约束和事务保持落库幂等。
