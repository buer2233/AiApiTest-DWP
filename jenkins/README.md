# jenkins

`jenkins` 是 AiApiTest-DWP 的 Jenkins Pipeline 和 Groovy 脚本目录，负责在 Windows/Linux Jenkins agent 上调用 `api-test`，执行接口自动化测试、失败重试、Allure 报告生成和产物归档。

当前已将原单一参数化 pipeline 重新设计为**三个相互独立的 pipeline**（每日全量 / 模块重试 / 失败重试），各自驱动 `api-test/tools/ci_runner.py` 对应模式；公共 stage 抽取到 `scripts/lib/pipeline-common.groovy` 复用，避免重复。

## 目录结构

```text
jenkins/
├── Jenkinsfile.daily-full        # job: api-test-daily-full 入口
├── Jenkinsfile.module-rerun      # job: api-test-module-rerun 入口
├── Jenkinsfile.failed-rerun      # job: api-test-failed-rerun 入口
├── README.md
├── scripts/
│   ├── daily-full-pipeline.groovy
│   ├── module-rerun-pipeline.groovy
│   ├── failed-rerun-pipeline.groovy
│   └── lib/
│       └── pipeline-common.groovy    # 公共 runCommand / runStages
└── tests/
    ├── test_pipeline_static.py        # 三个 pipeline 静态结构测试
    └── test_docker_deployment_static.py
```

## 三个独立 Pipeline

| Job | 入口 Jenkinsfile | 模式 | 触发 | 关键参数 |
| --- | --- | --- | --- | --- |
| `api-test-daily-full` | `Jenkinsfile.daily-full` | `RETRY_MODE=none`（全量） | 定时 `cron`（每日凌晨） | 无（固定 `CASE_PATH=test_case`） |
| `api-test-module-rerun` | `Jenkinsfile.module-rerun` | `RETRY_MODE=module` | 手动 | `CASE_PATH`、`RETRY_COUNT` |
| `api-test-failed-rerun` | `Jenkinsfile.failed-rerun` | `selected` / `all-failed` | 手动 | `RETRY_MODE`、`PYTEST_NODE_IDS`、`CASE_PATH`、`RETRY_COUNT` |

三个 pipeline 通过 `withEnv` 注入模式相关环境变量，统一以 `--from-jenkins-env` 调用 `ci_runner.py`；
Groovy **不复制** pytest 执行、失败重试、node id 收集与 Allure 解析逻辑（这些只在 `api-test/tools/ci_runner.py` 实现）。

## 公共 stage（scripts/lib/pipeline-common.groovy）

```text
Checkout → Prepare Python → Install API Test Requirements
→ Run API Tests → Generate Allure Report
→ Archive Runtime Artifacts → Publish Allure
```

- `runCommand(unix, windows)`：`isUnix()` 分支兼容 Linux `sh` 与 Windows `bat`。
- 使用 Jenkins workspace 相对路径（`api-test/...`），不写死本机绝对路径。

## ci_runner 参数契约（环境变量）

| 环境变量 | 说明 |
| --- | --- |
| `RETRY_MODE` | `none` / `selected` / `all-failed` / `module` |
| `CASE_PATH` | pytest 模块/用例路径（相对 `api-test`） |
| `PYTEST_NODE_IDS` | 多个 pytest node id，换行或英文逗号分隔 |
| `RETRY_COUNT` | pytest-rerunfailures 重试次数 |
| `CLEAN_ALLURE` / `OPEN_REPORT` | 清理 / 打开报告开关 |
| `RUN_ID` / `CI_RUNNER_ENV` | run id 与 Jenkins 环境标识 |

## 静态验证

```bash
python -m pytest jenkins/tests
```

## 边界说明

- 本阶段仅交付脚本与静态测试（不联动前端触发、后端 Jenkins API 调用、任务入库）。
- 并发上限与同模块互斥锁属平台编排层，留后续「执行链路」需求。

## 安全原则

- 不提交真实 Jenkins URL、用户名或 API token。
- 不写死本机绝对路径，使用 workspace 相对路径。
- 真实凭据通过 Jenkins Credentials 或环境变量管理。
