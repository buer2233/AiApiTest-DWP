# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins报告本地保留与Allure插件接入-功能测试用例

## 1. 测试范围

依据需求简述：

- Jenkins Job 执行后在实际执行仓库 `api-test/runtime/ci-runs/<run_id>/` 生成 Allure 结果和 HTML 报告。
- 本地 runtime 报告默认保留 30 天，仅清理超过保留期的历史 run。
- Jenkins build 和 artifact 默认保留 30 天。
- Jenkins 工具链镜像预装 Allure Jenkins 插件，支持 Jenkins 内报告展示。
- 当前 Jenkins 容器挂载路径必须指向当前仓库。

## 2. 功能测试用例

| 用例编号 | 优先级 | 模块 | 场景 | 前置条件 | 操作步骤 | 预期结果 |
| --- | --- | --- | --- | --- | --- | --- |
| P5-JENKINS-REPORT-001 | P0 | api-test | 默认报告保留天数 | Jenkins env 未配置 `CI_RUN_RETENTION_DAYS` | 调用 `build_run_request_from_jenkins_env()` | `RunRequest.retention_days=30` |
| P5-JENKINS-REPORT-002 | P0 | api-test | 自定义报告保留天数 | Jenkins env 配置 `CI_RUN_RETENTION_DAYS=45` | 调用 `build_run_request_from_jenkins_env()` | `RunRequest.retention_days=45` |
| P5-JENKINS-REPORT-003 | P0 | api-test | 只删除超过保留期的历史 run | `runtime/ci-runs` 下存在 current、old、recent 和普通文件 | 调用 `cleanup_old_ci_runs(retention_days=30)` | old 被删除；current、recent 和普通文件保留 |
| P5-JENKINS-REPORT-004 | P0 | Jenkins Pipeline | Jenkins 构建和 artifact 保留 30 天 | 读取共享 Pipeline | 检查 `properties` | 存在 `buildDiscarder(logRotator(...))`，build 和 artifact 使用同一保留天数 |
| P5-JENKINS-REPORT-005 | P0 | Jenkins Pipeline | Pipeline 向 ci_runner 传保留天数 | 读取共享 Pipeline | 检查 `withEnv` | 包含 `CI_RUN_RETENTION_DAYS=${ciRunRetentionDays}`，默认值为 30 |
| P5-JENKINS-REPORT-006 | P1 | Docker Compose | Jenkins 容器接收保留天数 | 读取 `docker-compose.yml` | 检查 Jenkins environment | 包含 `CI_RUN_RETENTION_DAYS: ${CI_RUN_RETENTION_DAYS:-30}` |
| P5-JENKINS-REPORT-007 | P1 | 环境模板 | `.env.example` 文档化报告保留配置 | 读取 `.env.example` | 检查配置项 | 包含 `CI_RUN_RETENTION_DAYS=30`，无真实凭据 |
| P5-JENKINS-REPORT-008 | P0 | Docker Jenkins | 工具链镜像安装 Allure Jenkins 插件 | 读取 `docker/jenkins/Dockerfile` | 检查构建步骤 | 包含 `jenkins-plugin-cli --plugins allure-jenkins-plugin` |
| P5-JENKINS-REPORT-009 | P0 | Jenkins 本地验证 | 当前 Job 不写入临时目录 | Jenkins 容器挂载当前仓库并配置本地 Job | 手工触发每日全量 Job | `summary.json` 路径位于 `/workspace/AiApiTest-DWP/api-test/runtime/ci-runs/<run_id>/`；宿主机当前仓库同步可见 |
| P5-JENKINS-REPORT-010 | P1 | 子代理审计 | `Subagent log not found` 解释 | 本地生成审计报告 | 检查报告文件 | 报告说明该提示不等同于子代理失败，且报告不提交 git |
| P5-JENKINS-REPORT-011 | P0 | Docker Jenkins | Jenkins 用户可创建 workspace 控制目录 | 读取 `docker/jenkins/Dockerfile` | 检查 `/workspace` 初始化 | 包含 `mkdir -p /workspace` 和 `chown jenkins:jenkins /workspace` |
| P5-JENKINS-REPORT-012 | P0 | Docker Jenkins | Pipeline 的 `python` 命令可用 | 读取 `docker/jenkins/Dockerfile` | 检查 Python 包 | 包含 `python-is-python3` |
| P5-JENKINS-REPORT-013 | P0 | Jenkins Allure | 工具链镜像自动注册 Allure Commandline | 读取 `jenkins/scripts/configure-allure-commandline.groovy` | 检查初始化脚本 | 使用 `AllureCommandlineInstallation` 注册 `Allure Commandline` |
| P5-JENKINS-REPORT-014 | P0 | Jenkins Pipeline | Allure 插件不改写 Jenkins 构建状态 | 读取共享 Pipeline | 检查 `Publish Allure` 阶段 | 包含 `commandline: 'Allure Commandline'` 和 `resultPolicy: 'LEAVE_AS_IS'` |

## 3. 回归测试

- `python -m pytest api-test/tests/test_ci_runner.py`
- `python -m pytest jenkins/tests/test_pipeline_static.py`
- `python -m pytest jenkins/tests/test_docker_deployment_static.py`
- 必要时用当前仓库挂载的 Jenkins 容器触发 `AiApiTest-DWP-Daily-Full-Module`，检查本地 `api-test/runtime/ci-runs/<run_id>/summary.json` 和 Allure 报告目录。
- 必要时使用 `docker compose -f docker-compose.yml -f docker-compose.jenkins-tools.yml build jenkins` 验证工具链镜像可构建；网络较慢时应延长超时。
