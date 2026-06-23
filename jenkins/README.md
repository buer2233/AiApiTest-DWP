# jenkins

`jenkins` 是 AiApiTest-DWP 的 Jenkins Pipeline 和 Groovy 脚本目录，后续负责在 Windows/Linux Jenkins agent 上调用 `api-test`，执行接口自动化测试、失败重试、Allure 报告生成和产物归档。

当前阶段即将进入 Stage 4，实现 Jenkins Groovy Pipeline。

## 目标职责

- 提供 Jenkinsfile 和可复用 Groovy 脚本。
- 暴露 Jenkins 参数：模块路径、node id、重试模式、重试次数、清理开关和报告开关。
- 调用 `api-test/tools/ci_runner.py` 执行 pytest 和失败重试。
- 归档 `api-test/runtime/ci-runs/<run_id>/` 下的运行产物。
- 发布或归档 Allure 报告。
- 兼容 Windows `bat` 和 Linux `sh`。

## 计划结构

```text
jenkins/
├── Jenkinsfile
├── README.md
└── scripts/
    └── api-test-pipeline.groovy
```

## 计划参数

| 参数 | 说明 |
|------|------|
| `CASE_PATH` | pytest 模块路径，默认 `test_case/test_gbif_case` |
| `PYTEST_NODE_IDS` | 多个 pytest node id，换行或英文逗号分隔 |
| `RETRY_MODE` | `none`、`selected`、`all-failed`、`module` |
| `RETRY_COUNT` | pytest-rerunfailures 重试次数 |
| `CLEAN_ALLURE` | 是否清理 Allure 结果 |
| `OPEN_REPORT` | 是否打开报告，CI 中默认 false |

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

## 安全原则

- 不提交真实 Jenkins URL、用户名或 API token。
- 不写死本机绝对路径。
- 使用 Jenkins workspace 相对路径。
- 真实凭据通过 Jenkins Credentials 或环境变量管理。
