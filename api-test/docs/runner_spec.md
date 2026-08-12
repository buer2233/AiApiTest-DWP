# api-test/docs/runner_spec.md

本文件是 E9 接口自动化测试框架的**执行参考手册**，包含所有运行命令、CI 执行器用法、失败重试机制和执行产物说明。
当需要执行测试、配置 CI 或排查运行问题时读取本文件。

## 执行协议

- 使用 pytest、requests、allure-pytest、pytest-rerunfailures。
- 失败重试以 pytest node id 为核心数据结构，不能改写 pytest 原始 node id 字符串。
- `tools/ci_runner.py` 必须使用相对 `api-test/` 的路径，不写死本机绝对路径。
- Allure 原始结果写入 `report/allure-results/` 或 `runtime/ci-runs/<run_id>/allure-results/`。
- Allure HTML 报告写入 `report/allure-report/` 或 `runtime/ci-runs/<run_id>/allure-report/`。
- Jenkins 和 DRF 依赖的执行摘要必须稳定输出到 `runtime/ci-runs/<run_id>/`，至少包含模块、总数、通过数、失败数、错误数、跳过数、失败 node id、报告路径和执行状态。

## 本地运行

运行全部接口用例：

```powershell
python runpytest.py
```

执行指定模块：

```powershell
python runpytest.py --case-path test_case/test_login_case --clean
```

按 marker 运行：

```powershell
python runpytest.py -m smoke
```

E9 真实登录验收优先从 Jenkins Credentials 或进程环境变量读取私有凭据：
`E9_LOGINID` 与 `E9_USERPASSWORD` 必须同时配置。仅在本地调试且明确使用抓包账号时，
才回退读取 `page_api/login_api/account.json`；该文件已被 Git 忽略，不能提交真实值。

```powershell
$env:E9_LOGINID = "<E9_LOGINID>"
$env:E9_USERPASSWORD = "<E9_USERPASSWORD>"
python -m pytest -p no:base_url test_case/test_login_case --base-url http://<E9_HOST>:<E9_PORT>
```

生成后打开 Allure 报告：

```powershell
python runpytest.py --case-path test_case/test_login_case --open-report
```

默认报告位置：

```text
api-test/report/allure-results/
api-test/report/allure-report/<timestamp>/
```

## CI 执行器

```powershell
python -m tools.ci_runner --case-path test_case/test_login_case --retry-mode module --run-id local-demo --clean
```

常用参数：

| 参数 | 说明 |
|------|------|
| `--case-path` | pytest 用例目录、文件或模块路径 |
| `--node-id` | pytest node id，可重复传入 |
| `--retry-mode` | `none`、`module`、`selected`、`all-failed` |
| `--retry-count` | pytest-rerunfailures 重试次数，必须大于等于 0 |
| `--run-id` | 本次运行 ID，用于生成 `runtime/ci-runs/<run_id>/` |
| `--clean` / `--no-clean` | 是否传递 `--clean-alluredir` |
| `--open-report` | Allure CLI 可用时打开 HTML 报告 |

执行产物：

```text
api-test/runtime/ci-runs/<run_id>/
├── console.log
├── failed_nodeids.json
├── summary.json
├── case_results.json
├── allure-results/
└── allure-report/
```

`summary.json` 还包含 `case_results`，按 pytest 最终 node id 输出 `passed`、`failed`、`skipped`、`error` 状态。Jenkins 执行时 pytest 使用 `-vv`，逐用例过程输出会脱敏后实时进入 Jenkins console，同时写入当前 run 的 `console.log`；pytest cache 位于当前 `runtime/ci-runs/<run_id>/.pytest_cache`，避免并发任务共享根缓存。`RUN_ID` 仅允许字母、数字、点、下划线和短横线，且已存在的 run 目录不会被覆盖。

Jenkins 环境变量模式默认读取 `CI_RUN_RETENTION_DAYS`，未配置时保留 30 天。
每次 CI 执行只会删除 `runtime/ci-runs/` 下超过保留期的历史 run 目录，
不会删除本次运行目录，也不会清理 30 天内的报告。

`summary.json` 包含：

- `status`
- `return_code`
- `failed_nodeids`
- `allure_results_dir`
- `allure_report_dir`
- `allure_report_status`
- `allure_report_message`
- `total_count`
- `failed_count`
- `passed_count`
- `skipped_count`
- `duration_seconds`

后续 Jenkins Pipeline 和 DRF 后端都应调用 `tools.ci_runner`，不要在 Groovy 或后端中重复实现 pytest 命令拼接和失败重试逻辑。

## 失败重试

pytest node id 是失败重试的核心数据结构。

选择一个或多个用例重试：

```powershell
python -m tools.ci_runner `
  --retry-mode selected `
  --node-id "test_case/test_login_case/test_login_api.py::TestE9LoginAPI::test_login_and_get_os_info" `
  --run-id retry-selected
```

一键重跑全部失败用例：

```powershell
python -m tools.ci_runner --retry-mode all-failed --run-id retry-all
```

模块重试：

```powershell
python -m tools.ci_runner --retry-mode module --case-path test_case/test_login_case --run-id retry-module
```

## 验证命令

运行 `api-test` 自身测试：

```powershell
python -m pytest tests -v
```

运行执行器测试：

```powershell
python -m pytest tests/test_pytest_nodeids.py tests/test_ci_runner.py -v
```

运行迁移回归测试：

```powershell
python -m pytest tests/test_runpytest_commands.py tests/test_pycharm_migration_config.py -v
```