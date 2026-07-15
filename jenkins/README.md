# jenkins

`jenkins` 是 AiApiTest-DWP 的 Jenkins Pipeline 和 Groovy 脚本目录，负责在 Windows/Linux Jenkins agent 上校验并启动隔离的 `api-runner`，执行接口自动化测试、失败重试、Allure 报告生成和产物归档。

Stage 5 P4 已在通用 Pipeline 基础上拆出三条业务流水线：每日全量模块执行、失败重试、模块重试。当前阶段供主人直接在 Jenkins 上配置和验收；平台 DRF/Vue 触发与结果同步在下一阶段接入。

## Stage13 平台环境 Job

平台应用环境准备只使用一个固定 Pipeline Job。推荐名称为 `AiApiTest-DWP-Platform-Bootstrap`，并与私有 `.env` 中的 `JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME` 一致。本地 Compose Jenkins 启动时幂等创建或修复该 Job，固定加载 `jenkins/Jenkinsfile.platform-bootstrap` 并注入 `LOCAL_WORKSPACE_REPO=true`；用户可以在 Jenkins 页面手工点击同一个 Job，也可以使用 helper 触发，两条路径都进入相同的 Jenkinsfile、参数、阶段和结果契约。

| 配置项 | 固定值或要求 |
| --- | --- |
| Job 类型 | Pipeline |
| Pipeline script path | `jenkins/Jenkinsfile.platform-bootstrap` |
| 并发 | Pipeline 固定 `disableConcurrentBuilds`，不得在 Job 覆盖为并发执行 |
| 参数一 | Boolean `build_all`，默认 `build_all=true` |
| 参数二 | Boolean `run_full_tests`，默认 `run_full_tests=false` |
| 本地挂载模式 | `LOCAL_WORKSPACE_REPO=true`，使用 `AIAPITEST_LOCAL_WORKSPACE`；不能把本地源码 Job 改为远端 checkout |
| SCM 模式 | `LOCAL_WORKSPACE_REPO=false`，由 Jenkins 配置的 SCM 执行 `checkout scm` |
| controller | 使用 Jenkins 工具链镜像，必须具有 Docker CLI/Compose、Docker Socket 挂载和 `.env` 的 `DOCKER_GID` supplemental group |

环境 Job 有固定七阶段：Checkout/Workspace、Bootstrap Preflight、Dependency Assurance、Deploy、Health、Tests、Archive & Summary。`build_all=true` 会重建镜像并重启全部应用服务；`build_all=false` 仅在服务缺失或构建输入变化时增量重建。默认冒烟，`run_full_tests=true` 才执行平台全量。三域依赖独立检查，安装失败时每个域只尝试一次安装、输出完整日志并汇总失败；任何依赖失败均在部署前终止。环境 Job 不执行 migration、初始化管理员、`collectstatic`，不执行 rollback，不删除 volume；失败时保留服务与诊断证据。

用户启动 MySQL/Jenkins bootstrap 后，Jenkins 启动时幂等创建或修复该 Job：Windows 使用 `scripts/trigger-platform-bootstrap.ps1`，Linux/macOS/Git Bash 使用 `scripts/trigger-platform-bootstrap.sh`，或在 Jenkins 页面点击 Build。AI 必须只使用这两个 helper，禁止直接 Docker、pip、npm、`runserver`、Vite 或 worker 启动命令。

### 信任与故障边界

Docker Socket 赋予 Jenkins controller 主机级 Docker 控制能力，因此仅允许受信任的本地开发/验收 controller 使用，绝不允许不受信任 SCM/PR Job 使用。`DOCKER_GID` 只解决 Socket 访问权限，禁止使用 `chmod 666 /var/run/docker.sock`。详情和 MySQL/Jenkins bootstrap 命令见 `docker/DEPLOYMENT.md`，这些命令只供主人/平台运维执行。

失败时优先查看 Jenkins Build Summary 和结构化诊断：`.env` 缺失、Docker CLI/Compose/Socket、MySQL 未运行或不健康、依赖 build、应用 health、helper 认证/Job/timeout 都会给出修复方向。主人/平台运维修复根因后重新构建；AI 不得以宿主机命令旁路失败。Allure 是 Jenkins Allure 插件/Build 级归档入口，不新增常驻服务。

## 目标职责

- 提供通用 Jenkinsfile、三条业务 Jenkinsfile 和可复用 Groovy 脚本。
- 暴露 Jenkins 参数：模块路径、模块展示名、node id、重试次数、清理开关和报告兼容开关。
- 通过 `jenkins/scripts/api_runner_cli.py execute` 启动固定镜像 `aiapitest-api-runner:local`，由镜像内源码中的 `api-test/tools/ci_runner.py` 执行 pytest 和失败重试。
- 归档 `api-test/runtime/ci-runs/<run_id>/` 下的运行产物。
- 发布或归档 Allure 报告。
- 兼容 Windows `bat` 和 Linux `sh`。

## 计划结构

```text
jenkins/
├── Jenkinsfile
├── Jenkinsfile.daily-full-module
├── Jenkinsfile.failed-rerun
├── Jenkinsfile.module-rerun
├── README.md
├── tests/
│   └── test_pipeline_static.py
└── scripts/
    ├── api-test-pipeline.groovy
    ├── api_runner_cli.py
    ├── api_runner_lifecycle.py
    ├── daily-full-module-pipeline.groovy
    ├── failed-rerun-pipeline.groovy
    └── module-rerun-pipeline.groovy
```

## 三条业务流水线

| Job 类型 | Jenkinsfile | Pipeline 脚本 | 触发方式 | 固定执行模式 | 后续是否更新模块日期/执行时间 |
| --- | --- | --- | --- | --- | --- |
| 每日全量模块执行 | `jenkins/Jenkinsfile.daily-full-module` | `jenkins/scripts/daily-full-module-pipeline.groovy` | `0 2 * * *`，也可手工触发 | `RETRY_MODE=none` | 是 |
| 失败重试 | `jenkins/Jenkinsfile.failed-rerun` | `jenkins/scripts/failed-rerun-pipeline.groovy` | 手工触发；后续由 DRF 触发 | `RETRY_MODE=selected` | 否 |
| 模块重试 | `jenkins/Jenkinsfile.module-rerun` | `jenkins/scripts/module-rerun-pipeline.groovy` | 手工触发；后续由 DRF 触发 | `RETRY_MODE=module` | 是 |

每日全量按“一个模块一个 Jenkins Job”配置。每个模块创建一个独立 Pipeline Job，使用同一个 `Jenkinsfile.daily-full-module`，并在该 Job 的环境变量中设置 `JENKINS_MODULE_CASE_PATH` 作为本模块的 `CASE_PATH` 默认值。初始化脚本会直接配置 `0 2 * * *` 定时触发，初始化完成后即生效；手工 Build 仅用于验收执行链路，不是 cron 生效条件。未配置 `JENKINS_MODULE_CASE_PATH` 且未手工填写 `CASE_PATH` 时，构建会明确失败，避免 cron 跑到示例模块。

失败重试只有一条执行链路。平台下一阶段的“勾选失败用例后失败重试”和“一键失败重试”都应把目标失败用例 node id 列表传给 `PYTEST_NODE_IDS`；一键失败重试只是快速选择当前模块全部失败用例，不使用 `all-failed` 模式。

## 参数说明

### 每日全量模块执行

| 参数 | 说明 |
|------|------|
| `CASE_PATH` | pytest 模块路径，默认来自当前 Job 的 `JENKINS_MODULE_CASE_PATH` |
| `MODULE_NAME` | Jenkins 展示用模块名，不影响 pytest 选择 |
| `RETRY_COUNT` | pytest-rerunfailures 重试次数 |
| `CLEAN_ALLURE` | 是否清理 Allure 结果 |
| `OPEN_REPORT` | 兼容参数；Jenkins 非交互环境强制按 false 执行，避免启动 Allure Web server 卡住构建 |

### 失败重试

| 参数 | 说明 |
|------|------|
| `CASE_PATH` | 当前模块 pytest 路径，用于上下文和报告命名 |
| `PYTEST_NODE_IDS` | 必填，多个 pytest node id 支持换行或英文逗号分隔 |
| `RETRY_COUNT` | pytest-rerunfailures 重试次数 |
| `CLEAN_ALLURE` | 是否清理 Allure 结果 |
| `OPEN_REPORT` | 兼容参数；Jenkins 非交互环境强制按 false 执行，避免启动 Allure Web server 卡住构建 |

`PYTEST_NODE_IDS` 为空时构建会明确失败，避免误跑整个模块。

### 模块重试

| 参数 | 说明 |
|------|------|
| `CASE_PATH` | pytest 模块路径，默认 `test_case/test_gbif_case` |
| `MODULE_NAME` | Jenkins 展示用模块名，不影响 pytest 选择 |
| `RETRY_COUNT` | pytest-rerunfailures 重试次数 |
| `CLEAN_ALLURE` | 是否清理 Allure 结果 |
| `OPEN_REPORT` | 兼容参数；Jenkins 非交互环境强制按 false 执行，避免启动 Allure Web server 卡住构建 |

## 通用 Pipeline 兼容入口

`jenkins/Jenkinsfile` 仍保留通用入口，加载 `jenkins/scripts/api-test-pipeline.groovy`。通用入口继续暴露 `RETRY_MODE` 参数，支持 `none`、`selected`、`all-failed`、`module`，主要用于兼容已有本地验证或临时排查。P4 验收优先使用上面的三条业务 Jenkinsfile。

## Pipeline 阶段

```text
Checkout
Run API Tests
Archive Runtime Artifacts
Publish Allure
```

`Run API Tests` 阶段由 Jenkins `timeout(time: 60, unit: 'MINUTES')` 包裹，并通过固定的 `api_runner_cli.py execute` 命令委托 controller 标准库 helper。helper 先复用平台环境 Job 的同源 hash 算法校验 `aiapitest-api-runner:local` labels，再以 `docker create/start/wait/logs` 启动唯一 runner；容器不挂载 Jenkins workspace 源码、不读取根 `.env`，pytest、重试、summary 和 Allure 生成仍只由镜像内源码的 `ci_runner` 负责。

Compose Jenkins 默认通过 `JENKINS_EXECUTORS=40` 提供 40 个 controller executors，使四个现有平台 Job 均具备至少 10 个并发任务的容量。`configure-executors.groovy` 会在启动时移除这些 Job 的禁止并发属性；并发隔离由包含 Job/build/run 标识的唯一 runner 容器和 `RUN_ID` 共同保证，controller 不创建业务 Python 环境或安装测试依赖。

## 运行产物

每次构建都先从 runner 内的固定 run 目录把五项必需产物复制到 workspace staging，完整性校验通过后再原子落位到 `api-test/runtime/ci-runs/<run_id>/`。该目录至少应包含：

- `summary.json`
- `failed_nodeids.json`
- `console.log`
- `allure-results/`
- `allure-report/`

runner 门禁、容器名称/ID、脱敏日志和导出诊断写入 `api-test/runtime/runner-lifecycle/<run_id>/` 并与标准 run 一起归档。导出成功后只删除本次 runner；导出失败时不创建虚假标准 run、不删除 runner，并在 lifecycle 证据中给出人工 `docker cp` 指引。

如果 Jenkins 安装了 Allure 插件，流水线会发布 `allure-results`。如果插件不存在，构建不会因为缺少插件中断，用户仍可通过归档产物查看报告。若 `summary.json` 标记 Allure HTML 未生成，helper 会在产物成功回传和 runner 清理后明确失败。

Jenkins 构建中不要使用 `allure open`。即使手工构建时勾选 `OPEN_REPORT`，共享 Pipeline 也会强制传入 `OPEN_REPORT=false`，报告查看统一通过 Jenkins Allure 插件入口或归档的 `allure-report/index.html`。

Jenkins 构建和 artifact 默认保留 30 天，共享 Pipeline 同时把 `CI_RUN_RETENTION_DAYS` 传给 runner 内的 `ci_runner`。隔离 runner 看不到 workspace 的历史 run，因此本阶段不会自动删除宿主历史目录；长期运行时应结合 Jenkins workspace 运维策略观察容量。需要调整 Jenkins 保留天数时，在本地 `.env` 或 Jenkins 私有环境变量中覆盖 `CI_RUN_RETENTION_DAYS`。

Jenkins 内展示 Allure 报告依赖 Allure Jenkins 插件。默认官方 Jenkins 镜像不包含该插件；本地需要 Jenkins 内报告页时，应使用 `docker-compose.jenkins-tools.yml` 构建工具链镜像，该镜像同时安装 Allure CLI 和 `allure-jenkins-plugin`。已有 Jenkins 容器如果仍显示 `Allure Jenkins plugin is not installed`，需要用工具链镜像重建 Jenkins 容器，但不要删除 `aiapitest-jenkins-home` 数据卷。

工具链镜像会把 Allure CLI 注册为 Jenkins 全局工具 `Allure Commandline`，Pipeline 的 `Publish Allure` 阶段显式使用该工具，并设置 `resultPolicy: 'LEAVE_AS_IS'`。因此 pytest 失败用例只体现在 `summary.json` 和 Allure 报告中，不会把 Jenkins 基础设施构建改写为失败或不稳定。

## 人工验收步骤

本地 Docker Compose Jenkins 已将 `PROJECT_WORKSPACE` 指向的仓库挂载到 `AIAPITEST_LOCAL_WORKSPACE`，默认容器内路径为 `/workspace/AiApiTest-DWP`。`PROJECT_WORKSPACE` 必须是当前正在开发和验收的仓库根目录；如果它指向旧工作区，Jenkins 会加载旧代码，即使当前仓库已经提交和推送也不会生效。

若 Jenkins 控制台里的 `summary.json` 显示报告路径位于 `/tmp/...`、`/var/jenkins_home/workspace/...` 或旧工作区，而当前宿主机仓库 `api-test/runtime/ci-runs/` 没有报告，说明 Job 没有在当前挂载仓库执行。主人/平台运维应修正 `.env` 的 `PROJECT_WORKSPACE` 指向当前仓库根目录，按 `docker/DEPLOYMENT.md` 的 bootstrap 流程刷新 Jenkins 挂载，再运行 `configure-local-mounted-jobs.groovy` 修正本地 Job；AI 只报告诊断并等待重新构建。

### 本地 Compose Jenkins

本地验收不要使用远端 Git checkout 作为 Job 的第一步。应运行 `jenkins/scripts/configure-local-mounted-jobs.groovy` 配置本地挂载 Job，或在 Job 内联脚本中直接 `dir('/workspace/AiApiTest-DWP')` 后加载业务脚本。不要使用 `ws('/workspace/AiApiTest-DWP')` 作为本地挂载入口，否则多个 Job 同时运行时 Jenkins 可能分配到未挂载源码的 `@2` 目录。

`configure-local-mounted-jobs.groovy` 只有在显式 `LOCAL_WORKSPACE_REPO=true` 时才会执行；脚本会创建本地 Job，或修复早期“先 GitHub checkout、再设置 LOCAL_WORKSPACE_REPO”的旧本地 Job。已有非本地 Job 默认不会被覆盖，如确需强制替换，可在 Jenkins 环境中显式设置 `AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS=true` 后再执行脚本。

Stage8 起，本地脚本会读取挂载仓库内的 `api-test/utils/package_module.yaml`，按 `JENKINS_DAILY_FULL_JOB_PREFIX-<package_name>` 创建每个模块的 Daily Job，并为每个 Job 注入 `JENKINS_MODULE_CASE_PATH=test_case/<package_name>`。该命名规则必须与后端 `sync_jenkins_job_bindings` 管理命令保持一致；否则 Daily discovery 会扫描到不存在的 Job。

默认 `docker-compose.yml` 已把 `configure-local-mounted-jobs.groovy` 只读挂载到 Jenkins `init.groovy.d`。Jenkins 启动时会幂等创建或修复 `AiApiTest-DWP-Platform-Bootstrap` 环境 Job，以及分模块 Daily Job；环境 Job 无 cron、固定加载 `jenkins/Jenkinsfile.platform-bootstrap` 并由该 Jenkinsfile 管理 `disableConcurrentBuilds`，分模块 Daily Job 各自配置唯一的 `0 2 * * *` 定时器。初始化仍会移除遗留共享 Daily Job 的定时器但保留历史构建。修改模块 YAML 或 Job 前缀后，需要重启 Jenkins 并再次运行后端 `sync_jenkins_job_bindings`，确保 Jenkins Job 与数据库 binding 同名。

### 远端 Jenkins

远端 Jenkins 可以继续使用 SCM / Pipeline script path 加载 `jenkins/Jenkinsfile.*`，但远端网络、凭据和仓库地址必须由 Jenkins 自身配置维护，不写入本仓库。远端环境不要执行本地挂载 Job 配置脚本，除非同时配置了可用的 `AIAPITEST_LOCAL_WORKSPACE`。

1. 本地 Compose Jenkins 启动时会运行 `jenkins/scripts/configure-local-mounted-jobs.groovy`，生成或修正环境、每日全量、失败重试、模块重试本地 Job；无需手工创建环境 Job。
2. 如需手工创建本地内联 Pipeline，必须直接使用 `/workspace/AiApiTest-DWP`，不得先访问远端 Git。
3. 在该 Job 环境变量中设置 `JENKINS_MODULE_CASE_PATH=<当前模块 pytest 路径>`，重载初始化脚本后确认参数和 `0 2 * * *` 定时器已写入 Job 配置；可再手工 Build 验证实际执行链路。
4. 检查 console log、artifact 和 Allure 报告入口。
5. 创建失败重试 Job，Pipeline script path 使用 `jenkins/Jenkinsfile.failed-rerun`。
6. 空提交 `PYTEST_NODE_IDS`，确认构建明确失败。
7. 传入一条或多条 node id，确认只运行目标用例并生成完整产物。
8. 创建模块重试 Job，Pipeline script path 使用 `jenkins/Jenkinsfile.module-rerun`。
9. 设置 `CASE_PATH` 后手工 Build，确认运行当前模块全部用例并生成完整产物。

## 安全原则

- 不提交真实 Jenkins URL、用户名或 API token。
- 不写死本机绝对路径。
- 使用 Jenkins workspace 相对路径。
- 真实凭据通过 Jenkins Credentials 或环境变量管理。
