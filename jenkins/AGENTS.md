# jenkins/AGENTS.md

本目录是 Jenkins Pipeline、Groovy 脚本和 Job 模板目录。进入 `jenkins/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- Jenkins 是平台严格执行主干，所有测试执行、模块重试、失败重试和报告生成都必须通过 Jenkins。
- Jenkins 同时维护两条明确分离的执行链路：Platform Bootstrap 负责应用环境准备，业务 API Pipeline 负责接口用例执行、重试与 Allure 报告。
- Platform Bootstrap 固定加载 `jenkins/Jenkinsfile.platform-bootstrap`，通过 `jenkins/scripts/platform_bootstrap_cli.py` 执行环境预检、依赖保障、Compose 部署、健康检查、测试和证据归档；它不是 `ci_runner.py` 的包装层。
- 业务 API Pipeline 才调用 `api-test/tools/ci_runner.py`，负责 pytest、失败 node id 收集、重试和业务测试 summary。
- Jenkins 不负责 DRF 数据入库逻辑、Vue 页面逻辑或 pytest 重试规则实现。

## 固定 loop 中的位置

- `jenkins/` 属于非循环基础设施阶段，不要求每个需求重复产出。
- 当需求影响执行链路、Job 参数、归档策略、并发策略或报告发布方式时，必须先有需求说明、测试用例和架构影响说明，再修改 Jenkins 脚本。
- 修改 Pipeline 前必须先补充或更新脚本测试、契约断言和样例参数，实际运行确认失败测试由目标行为缺失导致，再做最小实现、目标测试 GREEN、重构和回归，遵循 `RED -> GREEN -> REFACTOR`。

## 模块职责

- Jenkins 参数定义和 Job 模板维护。
- Windows/Linux agent 兼容。
- Platform Bootstrap 只管理 `backend`、`frontend`、`jenkins-sync-worker` 三项应用服务；MySQL/Jenkins 由主人或平台运维 bootstrap，`api-runner` 仅按需作为测试镜像运行。
- 业务 API Pipeline 调用 `api-test/tools/ci_runner.py` 执行 daily full suite、module rerun、failed rerun 等模式，并归档 `api-test/runtime/ci-runs/<run_id>/` 产物。
- Platform Bootstrap 归档 `runtime/platform-bootstrap/<build-id>/` 证据、Build Summary 和可用 Allure 结果。
- 发布或归档 Allure 报告。
- 保留 Jenkins job/build 链接、任务状态和 console log，供 DRF 同步。

## 技术约定

- Groovy 只负责 Jenkins 参数、环境变量和 stage 编排。
- 业务 API Pipeline 的 pytest 执行、失败 node id 收集、重试和 summary 输出必须由 `api-test/tools/ci_runner.py` 完成；不得把这些逻辑复制进 Jenkinsfile 或 Groovy。
- Platform Bootstrap 的依赖域校验、镜像构建、健康检查与全量回归由 `platform_bootstrap` 模块按既定协议执行，Jenkinsfile 不得内联 Docker、pip 或 npm 命令。
- Pipeline 必须使用 `isUnix()` 分支兼容 Linux `sh` 和 Windows `bat`。
- 脚本使用 Jenkins workspace 相对路径，不写死本机绝对路径。
- Jenkins 脚本源文件必须放在 `jenkins/` 并纳入 git 管理。
- 凭据必须通过 Jenkins Credentials 或环境变量注入，不写入 Groovy、README 或示例参数。

## 测试和验证

- Jenkins 脚本变更应至少覆盖参数校验、执行模式选择、Windows/Linux 命令分支和归档路径。
- 能用本地脚本测试的逻辑应放到可测试文件中，避免把复杂逻辑全部塞进 Jenkinsfile。
- 修改归档契约时，必须同步更新 `api-test/` 执行器契约和 `back-end/` 同步逻辑说明。
- Platform Bootstrap 变更还必须覆盖固定 Job 名、`build_all` / `run_full_tests` 参数、八阶段顺序、三域至多一次构建、一次性 schema 初始化服务边界和结构化证据路径。

## 禁止事项

- 不在 Jenkinsfile 或 Groovy 脚本中提交真实账号、密码、token、cookie、Jenkins API Token、生产 URL 或敏感地址。
- 不在 Jenkins 中复制 pytest node id 收集、失败重试或 Allure summary 解析核心逻辑。
- 不把运行产物、console log、Allure HTML 或临时 workspace 文件提交到 git。

## 平台环境唯一入口（强制）

- 平台应用环境重启、依赖检查/安装、`backend`/`frontend`/`jenkins-sync-worker` 启动、停止或重建，以及平台冒烟/全量环境验收，AI 必须且只能触发固定 Jenkins 环境 Job。
- 固定环境 Job 名为私有 `.env` 的 `JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME`，默认 `AiApiTest-DWP-Platform-Bootstrap`；它由本地 Compose Jenkins 启动时通过版本化 init Groovy 幂等创建或修复，固定加载 `jenkins/Jenkinsfile.platform-bootstrap`，不得手工创建另一条旁路 Job。
- 该 Job 固定经过 `Checkout/Workspace`、`Bootstrap Preflight`、`Dependency Assurance`、`Schema & Initial Data`、`Deploy`、`Health`、`Tests`、`Archive & Summary` 八阶段；schema 阶段仅通过 profile `bootstrap` 的一次性 `backend-bootstrap` 服务依序执行 `migrate --noinput`、`seed_environment`、`init_admin --bootstrap-only`，成功后才允许 Deploy。`build_all=true` 默认全量重建应用镜像并重建三项应用容器，`run_full_tests=false` 默认仅冒烟。
- Windows 唯一入口为 `scripts/trigger-platform-bootstrap.ps1`；Linux/macOS/Git Bash 唯一入口为 `scripts/trigger-platform-bootstrap.sh`。用户在 Jenkins 页面手工点击同一 Job 也使用相同 Pipeline、参数、阶段和结果契约。
- AI 禁止直接执行应用服务 `docker compose up/restart/stop/down`、`docker build`、宿主机或运行容器的 `pip install`、`npm install/npm ci`，也禁止直接启动 Django `runserver`、Vite 或同步 worker 替代环境 Job。
- MySQL 与 Jenkins 仅由主人/平台运维按 `docker/DEPLOYMENT.md` 完成 bootstrap；环境 Job/helper 永不管理这两个基础服务。AI 只能检查并反馈，不能代替主人/平台运维启动。
- 除固定 Job 的 `Schema & Initial Data` 一次性 `backend-bootstrap` 服务外，AI、宿主机、常驻服务、readiness、其他 Jenkins Job 均禁止执行 migration 或初始化管理员。禁止 `down -v`、volume 删除、`chmod 666 /var/run/docker.sock`、`collectstatic`、自动 rollback 或输出真实凭据。环境失败必须阅读 Jenkins 结构化诊断，引导主人修复后重新构建，不能旁路处理。
