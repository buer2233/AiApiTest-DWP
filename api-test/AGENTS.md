# api-test/AGENTS.md

本目录是接口自动化执行核心。进入 `api-test/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 模块职责

- 封装通用接口请求方法和接口方法。
- 编写 pytest 接口自动化用例。
- 生成 Allure 原始结果和 HTML 报告。
- 收集 pytest node id，并支持失败用例重试。
- 向 Jenkins 和 DRF 后端提供统一 CI 执行器。

本目录不负责 Jenkins Groovy 编排、DRF API、Vue 页面或数据库模型。

## 目录约定

- 接口方法放在 `page_api/`。
- pytest 用例放在 `test_case/test_*_case/`。
- 测试平台通过 `test_case/test_*_case/` 文件夹区分模块。
- `tools/` 放可复用执行工具，例如 `pytest_nodeids.py` 和 `ci_runner.py`。
- `tests/` 放 `api-test` 自身单元测试。
- `runtime/`、`report/`、`logs/` 是运行产物目录，不作为业务代码提交。
- `test_data/` 初始可为空，只在需要时添加通用测试数据。

## 技术约定

- 使用 pytest、requests、allure-pytest、pytest-rerunfailures。
- Allure 原始结果写入 `report/allure-results/`。
- Allure HTML 报告写入 `report/allure-report/` 或 `runtime/ci-runs/<run_id>/allure-report/`。
- 多层取值优先用 `get_value()`，单层取值优先用 `.get()`。
- `runpytest.py` 和 `tools/ci_runner.py` 必须使用相对 `api-test/` 的路径，不写死本机绝对路径。
- 失败重试以 pytest node id 为核心数据结构，不能改写 pytest 原始 node id 字符串。

## 执行入口

本地手动执行：

```powershell
python runpytest.py --case-path test_case/test_gbif_case --clean
```

CI 执行器：

```powershell
python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id local-demo --clean
```

选择失败用例重试：

```powershell
python -m tools.ci_runner --retry-mode selected --node-id "<pytest node id>" --run-id retry-selected
```

一键失败重试：

```powershell
python -m tools.ci_runner --retry-mode all-failed --run-id retry-all
```

## 测试要求

- 新增或修改执行能力必须先写 `tests/` 下的 pytest 测试。
- Stage 3 相关回归命令：

```powershell
python -m pytest tests/test_pytest_nodeids.py tests/test_ci_runner.py -v
```

- `api-test` 自身回归命令：

```powershell
python -m pytest tests -v
```

## 禁止事项

- 不在用例或配置中提交真实账号、密码、token、cookie、生产地址。
- 不把重试逻辑复制到 Jenkins Groovy 或后端；Jenkins 和后端必须调用 `tools.ci_runner`。
- 不提交 `runtime/`、`report/allure-results/`、`report/allure-report/`、`logs/` 产物。
