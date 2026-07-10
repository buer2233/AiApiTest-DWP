# jenkins

`jenkins` 是 AiApiTest-DWP 的 Jenkins Pipeline 和 Groovy 脚本目录，后续负责在 Windows/Linux Jenkins agent 上调用 `api-test`，执行接口自动化测试、失败重试、Allure 报告生成和产物归档。

Stage 5 P4 已在通用 Pipeline 基础上拆出三条业务流水线：每日全量模块执行、失败重试、模块重试。当前阶段供主人直接在 Jenkins 上配置和验收；平台 DRF/Vue 触发与结果同步在下一阶段接入。

## 目标职责

- 提供通用 Jenkinsfile、三条业务 Jenkinsfile 和可复用 Groovy 脚本。
- 暴露 Jenkins 参数：模块路径、模块展示名、node id、重试次数、清理开关和报告兼容开关。
- 调用 `api-test/tools/ci_runner.py` 执行 pytest 和失败重试。
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

每日全量按“一个模块一个 Jenkins Job”配置。每个模块创建一个独立 Pipeline Job，使用同一个 `Jenkinsfile.daily-full-module`，并在该 Job 的环境变量中设置 `JENKINS_MODULE_CASE_PATH` 作为本模块的 `CASE_PATH` 默认值。脚本会通过 Jenkins `properties` 配置 `0 2 * * *` 定时触发；首次创建 Job 后建议先手工 Build 一次，使参数和定时配置生效。未配置 `JENKINS_MODULE_CASE_PATH` 且未手工填写 `CASE_PATH` 时，构建会明确失败，避免 cron 跑到示例模块。

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
Prepare Python
Install API Test Requirements
Run API Tests
Generate Allure Report
Archive Runtime Artifacts
Publish Allure
```

`Run API Tests` 阶段由 Jenkins `timeout(time: 60, unit: 'MINUTES')` 包裹，避免 pytest、Allure 或外部依赖异常挂起时长期占用执行器。`ci_runner` 内部也对 pytest 子进程设置 45 分钟超时，对 Allure HTML 生成设置 10 分钟超时，给 summary、failed node ids 和 console 诊断留出落盘缓冲；pytest 或 Allure 超时会写入 `summary.json` 和 `console.log`，便于平台同步诊断。

Compose Jenkins 默认通过 `JENKINS_EXECUTORS=40` 提供 40 个 controller executors，使四个现有平台 Job 均具备至少 10 个并发任务的容量。`configure-executors.groovy` 会在启动时移除这些 Job 的禁止并发属性；共享挂载仓库下，Pipeline 会把 Python 虚拟环境隔离到 `${JENKINS_PYTHON_VENV_DIR}/executor-<EXECUTOR_NUMBER>`，每次运行的 pytest cache 和 Allure 产物继续由 `RUN_ID` 隔离。

## 运行产物

每次构建都会把 `api-test/runtime/ci-runs/<run_id>/` 作为归档根目录。该目录至少应包含：

- `summary.json`
- `failed_nodeids.json`
- `console.log`
- `allure-results/`
- `allure-report/`

如果 Jenkins 安装了 Allure 插件，流水线会发布 `allure-results`。如果插件不存在，构建不会因为缺少插件中断，用户仍可通过归档产物查看报告。若 `summary.json` 标记 Allure HTML 未生成，构建会明确失败。

Jenkins 构建中不要使用 `allure open`。即使手工构建时勾选 `OPEN_REPORT`，共享 Pipeline 也会强制传入 `OPEN_REPORT=false`，报告查看统一通过 Jenkins Allure 插件入口或归档的 `allure-report/index.html`。

本地报告默认保留 30 天。共享 Pipeline 会配置 Jenkins 构建和 artifact 保留 30 天，并把 `CI_RUN_RETENTION_DAYS` 传给 `ci_runner`；`ci_runner` 只会删除 `api-test/runtime/ci-runs/` 下超过保留期的历史 run 目录，当前 run 和 30 天内报告不会被删除。需要调整保留天数时，在本地 `.env` 或 Jenkins 私有环境变量中覆盖 `CI_RUN_RETENTION_DAYS`。

Jenkins 内展示 Allure 报告依赖 Allure Jenkins 插件。默认官方 Jenkins 镜像不包含该插件；本地需要 Jenkins 内报告页时，应使用 `docker-compose.jenkins-tools.yml` 构建工具链镜像，该镜像同时安装 Allure CLI 和 `allure-jenkins-plugin`。已有 Jenkins 容器如果仍显示 `Allure Jenkins plugin is not installed`，需要用工具链镜像重建 Jenkins 容器，但不要删除 `aiapitest-jenkins-home` 数据卷。

工具链镜像会把 Allure CLI 注册为 Jenkins 全局工具 `Allure Commandline`，Pipeline 的 `Publish Allure` 阶段显式使用该工具，并设置 `resultPolicy: 'LEAVE_AS_IS'`。因此 pytest 失败用例只体现在 `summary.json` 和 Allure 报告中，不会把 Jenkins 基础设施构建改写为失败或不稳定。

## 人工验收步骤

本地 Docker Compose Jenkins 已将 `PROJECT_WORKSPACE` 指向的仓库挂载到 `AIAPITEST_LOCAL_WORKSPACE`，默认容器内路径为 `/workspace/AiApiTest-DWP`。`PROJECT_WORKSPACE` 必须是当前正在开发和验收的仓库根目录；如果它指向旧工作区，Jenkins 会加载旧代码，即使当前仓库已经提交和推送也不会生效。

若 Jenkins 控制台里的 `summary.json` 显示报告路径位于 `/tmp/...`、`/var/jenkins_home/workspace/...` 或旧工作区，而当前宿主机仓库 `api-test/runtime/ci-runs/` 没有报告，说明 Job 没有在当前挂载仓库执行。应修正 `.env` 的 `PROJECT_WORKSPACE` 指向当前仓库根目录，重新 `docker compose up -d jenkins` 刷新挂载，再运行 `configure-local-mounted-jobs.groovy` 修正本地 Job。

### 本地 Compose Jenkins

本地验收不要使用远端 Git checkout 作为 Job 的第一步。应运行 `jenkins/scripts/configure-local-mounted-jobs.groovy` 配置本地挂载 Job，或在 Job 内联脚本中直接 `dir('/workspace/AiApiTest-DWP')` 后加载业务脚本。不要使用 `ws('/workspace/AiApiTest-DWP')` 作为本地挂载入口，否则多个 Job 同时运行时 Jenkins 可能分配到未挂载源码的 `@2` 目录。

`configure-local-mounted-jobs.groovy` 只有在显式 `LOCAL_WORKSPACE_REPO=true` 时才会执行；脚本会创建本地 Job，或修复早期“先 GitHub checkout、再设置 LOCAL_WORKSPACE_REPO”的旧本地 Job。已有非本地 Job 默认不会被覆盖，如确需强制替换，可在 Jenkins 环境中显式设置 `AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS=true` 后再执行脚本。

Stage8 起，本地脚本会读取挂载仓库内的 `api-test/utils/package_module.yaml`，按 `JENKINS_DAILY_FULL_JOB_PREFIX-<package_name>` 创建每个模块的 Daily Job，并为每个 Job 注入 `JENKINS_MODULE_CASE_PATH=test_case/<package_name>`。该命名规则必须与后端 `sync_jenkins_job_bindings` 管理命令保持一致；否则 Daily discovery 会扫描到不存在的 Job。

### 远端 Jenkins

远端 Jenkins 可以继续使用 SCM / Pipeline script path 加载 `jenkins/Jenkinsfile.*`，但远端网络、凭据和仓库地址必须由 Jenkins 自身配置维护，不写入本仓库。远端环境不要执行本地挂载 Job 配置脚本，除非同时配置了可用的 `AIAPITEST_LOCAL_WORKSPACE`。

1. 本地 Compose 环境优先运行 `jenkins/scripts/configure-local-mounted-jobs.groovy`，生成或修正每日全量、失败重试、模块重试三条本地 Job。
2. 如需手工创建本地内联 Pipeline，必须直接使用 `/workspace/AiApiTest-DWP`，不得先访问远端 Git。
3. 在该 Job 环境变量中设置 `JENKINS_MODULE_CASE_PATH=<当前模块 pytest 路径>`，先手工 Build 一次，确认参数和 `0 2 * * *` 定时触发生效。
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
