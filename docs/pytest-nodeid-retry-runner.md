# Stage 3: pytest node id 与失败重试执行器

## 阶段范围

本阶段只在 `api-test/` 内实现可复用的 pytest node id 读取能力和 CI 执行器。Jenkins Groovy、DRF API、前端页面不在本阶段实现。

## 输入

- pytest 的 `.pytest_cache/v/cache/lastfailed` 文件。
- 模块路径，例如 `test_case/test_gbif_case`。
- 一个或多个 pytest node id，例如 `test_case/test_gbif_case/test_gbif_api.py::TestGbifAPI::test_species_search_by_keyword`。
- 运行参数：`retry-mode`、`retry-count`、`run-id`、`clean`、`open-report`。

## 输出

每次 CI 执行输出到：

```text
api-test/runtime/ci-runs/<run_id>/
├── console.log
├── failed_nodeids.json
├── summary.json
├── allure-results/
└── allure-report/
```

`summary.json` 至少包含：

- `status`
- `return_code`
- `failed_nodeids`
- `allure_results_dir`
- `allure_report_dir`

## 重试模式

| 模式 | 行为 |
|------|------|
| `none` | 按 `case-path` 执行模块或目录 |
| `module` | 按 `case-path` 重跑当前模块目录 |
| `selected` | 按传入的一个或多个 `node-id` 精确重跑 |
| `all-failed` | 读取 `.pytest_cache/v/cache/lastfailed` 中全部失败 node id 后重跑 |

## 验收标准

- 能从 pytest cache 读取失败 node id，并保持 pytest 原始 node id 字符串。
- cache 不存在时返回空列表。
- cache JSON 损坏时抛出清晰异常，便于调用方记录。
- 能写出 node id JSON，供 Jenkins 和后端读取。
- 能构造模块运行命令、选中 node id 运行命令、一键失败重试命令。
- 能输出 `summary.json`、`failed_nodeids.json` 和 `console.log`。
- 本阶段测试先 RED 后 GREEN。

## 测试命令

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_pytest_nodeids.py -v
python -m pytest tests/test_ci_runner.py -v
```

## 当前结果

已完成。

## 实现内容

- 新增 `api-test/tools/pytest_nodeids.py`：
  - `load_lastfailed(cache_dir)` 从 `.pytest_cache/v/cache/lastfailed` 读取失败 node id。
  - `normalize_nodeids(raw_values)` 去除空值和重复值，保留 pytest 原始 node id 字符串。
  - `write_nodeids(nodeids, output_path)` 写出 JSON 列表，供 Jenkins 和后端复用。
- 新增 `api-test/tools/ci_runner.py`：
  - `RunRequest` 描述一次 CI 执行请求。
  - `resolve_pytest_targets()` 支持 `none`、`module`、`selected`、`all-failed` 四种目标解析。
  - `build_pytest_command()` 构造 pytest 命令，并支持 `--reruns` 和 `--clean-alluredir`。
  - `run_ci_tests()` 执行 pytest，写出 `console.log`、`failed_nodeids.json` 和 `summary.json`。
  - 执行前清理旧的 pytest `lastfailed` cache，避免历史失败污染本次 summary。

## TDD 记录

### RED

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_pytest_nodeids.py -v
python -m pytest tests/test_ci_runner.py -v
```

结果：

- `tests/test_pytest_nodeids.py`：1 error，原因是 `tools` 包不存在。
- `tests/test_ci_runner.py`：1 error，原因是 `tools` 包不存在。

补强测试：

```powershell
python -m pytest tests/test_ci_runner.py -v
```

结果：

- 1 failed, 6 passed。失败原因是旧的 `.pytest_cache/v/cache/lastfailed` 会污染当前运行产物。

负数重试次数边界：

```powershell
python -m pytest tests/test_ci_runner.py::test_build_pytest_command_rejects_negative_rerun_count -v
```

结果：

- 1 failed。失败原因是 `retry_count=-1` 未被拒绝。

### GREEN

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_pytest_nodeids.py tests/test_ci_runner.py -v
```

结果：

```text
13 passed
```

回归：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests -v
```

结果：

```text
20 passed
```

真实执行器烟测：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id stage3-smoke --clean
```

结果：

```text
Exit code: 0
Allure report: api-test/runtime/ci-runs/stage3-smoke/allure-report
summary.json status: passed
failed_nodeids.json: []
```

## 已知问题

- `runtime/ci-runs/` 属于运行产物，已通过 `.gitignore` 排除，不提交。
- Allure CLI 不是 Python 依赖；本机可用时会生成 HTML 报告，不可用时执行器仍会保留 pytest 结果与 summary。
