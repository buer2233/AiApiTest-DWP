# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins每日全量卡死修复-功能测试用例

## 1. 测试范围

依据需求简述：

- Jenkins Pipeline 在 CI 环境中禁止打开 Allure Web server。
- `api-test/tools/ci_runner.py` Jenkins env 模式忽略 `OPEN_REPORT=true`。
- Jenkins `Run API Tests`、pytest 子进程和 Allure HTML 生成具备超时保护。
- 本地 CLI 模式继续保留 `--open-report` 行为。
- Jenkins 构建仍生成 Allure HTML 和运行摘要，并可归档 runtime 产物。

## 2. 功能测试用例

| 用例编号 | 优先级 | 模块 | 场景 | 前置条件 | 操作步骤 | 预期结果 |
| --- | --- | --- | --- | --- | --- | --- |
| P5-JENKINS-HANG-001 | P0 | Jenkins Pipeline | 手工构建误勾选 `OPEN_REPORT` 不应卡死 | Jenkins Job 使用 `jenkins/scripts/api-test-pipeline.groovy` | 触发 `AiApiTest-DWP-Daily-Full-Module`，参数 `OPEN_REPORT=true` | Pipeline 传给 `ci_runner` 的 `OPEN_REPORT` 固定为 `false`；`Run API Tests` 阶段不出现 `Press <Ctrl+C> to exit` |
| P5-JENKINS-HANG-002 | P0 | api-test | Jenkins env 模式忽略打开报告 | 环境变量包含 `CI_RUNNER_ENV=jenkins`、`OPEN_REPORT=true` | 调用 `build_run_request_from_jenkins_env()` | 返回的 `RunRequest.open_report` 为 `False` |
| P5-JENKINS-HANG-003 | P1 | api-test | 本地 CLI 模式保留打开报告能力 | 本地命令行显式传 `--open-report` | 调用 `parse_args(["--open-report"])` 或 CLI 入口 | 解析结果仍为 `open_report=True`，不影响开发者本地查看 |
| P5-JENKINS-HANG-004 | P1 | Jenkins Pipeline | 运行产物仍按 P5 契约归档 | Jenkins Job 正常执行 | 等待构建完成并检查 runtime 目录 | `summary.json`、`console.log`、`allure-results`、`allure-report` 路径不变 |
| P5-JENKINS-HANG-005 | P0 | Jenkins Pipeline | `Run API Tests` 有 Jenkins stage 超时 | 读取共享 Pipeline | 检查 `Run API Tests` stage | stage 内包含 `timeout(time: 60, unit: 'MINUTES')`，且包住 `tools.ci_runner --from-jenkins-env` |
| P5-JENKINS-HANG-006 | P0 | Jenkins/api-test | 外层超时给内层诊断留缓冲 | 读取共享 Pipeline 和 `ci_runner.py` | 检查超时常量 | Jenkins stage 为 60 分钟，pytest 为 45 分钟，Allure 为 10 分钟 |
| P5-JENKINS-HANG-007 | P0 | api-test | pytest 子进程超时后仍写诊断产物 | fake `subprocess.run` 抛 `TimeoutExpired` | 调用 `run_ci_tests()` | 生成 `console.log`、`failed_nodeids.json`、`summary.json`；summary 为 failed，return_code 为 124 |
| P5-JENKINS-HANG-008 | P1 | api-test | Allure HTML 生成超时不阻塞 | pytest fake 成功，Allure fake 超时 | 调用 `run_ci_tests()` | summary 中 `allure_report_status=failed`，message 和 `console.log` 含 timeout，流程返回不挂起 |
| P5-JENKINS-HANG-009 | P2 | 容器化兼容 | 修复不引入本机路径或凭据 | 修改已完成 | 扫描新增 diff | 不包含 `.env`、真实账号密码、token、Cookie、本机绝对路径或宿主机固定端口 |

## 3. 回归测试

- `python -m pytest jenkins/tests/test_pipeline_static.py`
- `python -m pytest api-test/tests/test_ci_runner.py`
- 必要时触发 Jenkins `AiApiTest-DWP-Daily-Full-Module` 手工构建，确认 `Run API Tests` 不再卡在 Allure open。
