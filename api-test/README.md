# api-test

`api-test` 是 AiApiTest-DWP 的接口自动化执行核心，负责封装接口方法、运行 pytest 用例、生成 Allure 结果、收集失败 pytest node id，并向 Jenkins 和后端提供统一的 CI 执行入口。

本目录保持通用接口自动化框架定位，不绑定具体业务系统。不要提交真实账号、密码、token、cookie、租户密钥、生产地址或不可迁移的业务常量。

## 目录结构

```text
api-test/
├── config.py                    # 接口自动化通用配置
├── conftest.py                  # pytest 命令行参数和公共 fixture
├── pytest.ini                   # pytest 发现规则
├── requirements.txt             # Python 依赖
├── runpytest.py                 # 本地手动执行入口
├── page_api/                    # 接口方法封装层
├── test_case/                   # pytest 接口用例层
├── test_data/                   # 测试数据目录，按需添加
├── tests/                       # api-test 自身单元测试
├── tools/                       # CI、node id、失败重试等可复用工具
├── utils/                       # 通用请求增强、日志和辅助能力
├── report/                      # Allure 原始结果和 HTML 报告
└── runtime/                     # 抓包、CI 执行和临时运行产物
```

## 安装依赖

```powershell
cd D:\AI\AiApiTest-DWP\api-test
pip install -r requirements.txt
```

Allure HTML 报告生成依赖 Allure CLI。未安装 Allure CLI 时，pytest 仍会正常执行，只会跳过 HTML 报告生成。

## 本地运行

运行全部接口用例：

```powershell
python runpytest.py
```

运行指定模块：

```powershell
python runpytest.py --case-path test_case/test_gbif_case --clean
```

按 marker 运行：

```powershell
python runpytest.py -m smoke
```

生成后打开 Allure 报告：

```powershell
python runpytest.py --case-path test_case/test_gbif_case --open-report
```

默认报告位置：

```text
api-test/report/allure-results/
api-test/report/allure-report/<timestamp>/
```

## CI 执行器

Stage 3 已提供统一执行器：

```powershell
python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id local-demo --clean
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
├── allure-results/
└── allure-report/
```

`summary.json` 包含：

- `status`
- `return_code`
- `failed_nodeids`
- `allure_results_dir`
- `allure_report_dir`

后续 Jenkins Pipeline 和 DRF 后端都应调用 `tools.ci_runner`，不要在 Groovy 或后端中重复实现 pytest 命令拼接和失败重试逻辑。

## 失败重试

pytest node id 是失败重试的核心数据结构。

选择一个或多个用例重试：

```powershell
python -m tools.ci_runner `
  --retry-mode selected `
  --node-id "test_case/test_gbif_case/test_gbif_api.py::TestGbifAPI::test_species_search_by_keyword" `
  --run-id retry-selected
```

一键重跑全部失败用例：

```powershell
python -m tools.ci_runner --retry-mode all-failed --run-id retry-all
```

模块重试：

```powershell
python -m tools.ci_runner --retry-mode module --case-path test_case/test_gbif_case --run-id retry-module
```

## 开发约定

- 接口方法放在 `page_api/`。
- pytest 用例放在 `test_case/test_*_case/`。
- 测试平台通过 `test_case/test_*_case/` 文件夹区分模块。
- 多层取值优先用 `get_value()`，单层取值优先用 `.get()`。
- 新增执行能力优先放在 `tools/`，供 Jenkins 和后端复用。
- 运行产物写入 `runtime/`，报告产物写入 `report/`，不要作为业务代码提交。
- 新功能和缺陷修复必须先写测试，按 RED -> GREEN -> REFACTOR 推进。

## 验证命令

运行 `api-test` 自身测试：

```powershell
python -m pytest tests -v
```

运行 Stage 3 执行器测试：

```powershell
python -m pytest tests/test_pytest_nodeids.py tests/test_ci_runner.py -v
```

运行迁移回归测试：

```powershell
python -m pytest tests/test_runpytest_commands.py tests/test_pycharm_migration_config.py -v
```
