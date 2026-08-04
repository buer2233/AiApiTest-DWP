# AiApiTest-DWP

`AiApiTest-DWP` 是一个面向 AI 协作的企业级自动化测试平台，采用单仓库管理接口自动化、Jenkins 流水线、DRF 后端、Vue 3 前端、Docker 基础设施和项目交接资料。

平台执行主干固定为 Jenkins：所有测试执行、模块重试、失败重试和报告生成都通过 Jenkins 调用 `api-test` 完成；DRF 负责平台数据、权限、任务编排和状态同步；Vue 3 前端负责测试管理界面。

本项目保持通用测试平台定位，不提交真实账号、密码、token、cookie、Jenkins API Token、生产地址或不可迁移的业务常量。

## 平台环境启动

平台应用服务、依赖检查/安装、镜像重建、冒烟和全量环境验收统一由 Jenkins 环境 Job `AiApiTest-DWP-Platform-Bootstrap` 完成。快速路径是：主人/平台运维准备私有 `.env` 并启动 MySQL/Jenkins bootstrap 容器；Jenkins 启动时幂等创建或修复该固定环境 Job，随后在 Jenkins 页面点击 Build 或使用 helper，最后查看 Jenkins Build Summary、归档 Allure 与 `.env` 配置的公开地址。

首次配置必须先复制 `.env.example`，再按 [Docker 部署说明](docker/DEPLOYMENT.md) 人工补齐仅存在于本地 `.env` 的 16 项私有配置，之后才能运行基础服务 bootstrap。模板只保留平台绑定主机、公开主机/协议、五个宿主机端口以及 workspace、Docker GID、报告保留天数、Playwright 镜像共 12 项公共配置；服务 URL 统一由这些基础量派生。Job 名、内部服务地址、API 路径、超时、Cookie 策略和其他固定运行参数均由代码维护。

Windows helper 是 `scripts/trigger-platform-bootstrap.ps1`；Linux/macOS/Git Bash helper 是 `scripts/trigger-platform-bootstrap.sh`。AI 只能使用这两个 helper，不能直接执行应用服务 Docker/依赖安装/`runserver`/Vite/worker 命令。MySQL 与 Jenkins 仅由主人/平台运维启动；失败时依据 Jenkins 结构化诊断修复后重新构建。完整的 bootstrap、Job 参数、Socket 安全边界和故障排查见 `docker/DEPLOYMENT.md` 与 `jenkins/README.md`。

## Jenkins 结果自动同步（仅隔离本地开发调试）

下列命令仅用于隔离本地开发调试，不属于平台环境准备、生产运行或验收 worker 的启动入口。AI 不得执行这些命令；平台环境中的 worker 由 Compose `jenkins-sync-worker` 服务承载，并只能通过 Jenkins 环境 Job 管理。

```powershell
cd back-end
python manage.py sync_jenkins_results --once
python manage.py sync_jenkins_results --watch
python manage.py sync_jenkins_results --watch --interval 10
```

`--watch` 未显式传入 `--interval` 时使用代码内固定的 10 秒轮询间隔。该进程复用后端数据库与 Jenkins 私有配置，不使用浏览器 Cookie，不直接执行 pytest；隔离调试时建议只启动一个实例，重复实例仍通过数据库唯一约束和事务保持落库幂等。
