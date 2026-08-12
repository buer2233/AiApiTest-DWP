# api-test — E9 接口自动化测试框架

`api-test` 是 **E9 系统专用**的接口自动化执行核心，负责封装 E9 接口方法、运行 pytest 用例、生成 Allure 结果、收集失败 pytest node id，并向 Jenkins 和后端提供统一的 CI 执行入口。

本框架不包含 E9 以外的任何业务模块。不要提交真实账号、密码、token、cookie、租户密钥、生产地址或不可迁移的业务常量。

## 目录结构

```text
api-test/
├── config.py                    # 接口自动化通用配置（E9 测试环境）
├── conftest.py                  # pytest 命令行参数和公共 fixture
├── pytest.ini                   # pytest 发现规则
├── requirements.txt             # Python 依赖
├── runpytest.py                 # 本地手动执行入口
├── page_api/                    # 接口方法封装层
│   ├── public/                  # 公共基类（BaseAPI）
│   └── login_api/               # 登录模块接口封装
├── test_case/                   # pytest 接口用例层
│   └── test_login_case/         # 登录模块用例
├── test_data/                   # 测试数据目录，按需添加
├── tests/                       # api-test 自身单元测试
├── tools/                       # CI、node id、失败重试等可复用工具
├── utils/                       # 通用请求增强、日志和辅助能力
├── report/                      # Allure 原始结果和 HTML 报告
└── runtime/                     # 抓包、CI 执行和临时运行产物
```

### 命名规范（与 E10 框架对齐）

| 层级 | 命名规范 | 示例 |
|------|---------|------|
| 接口方法目录 | `page_api/模块名_api/` | `page_api/login_api/` |
| 测试用例目录 | `test_case/test_模块名_case/` | `test_case/test_login_case/` |

新增模块时按上述规范在对应位置创建目录即可。

## 安装依赖

```powershell
cd D:\AI\Hermes\dev\workspace001\AiApiTest-DWP\api-test
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
python runpytest.py --case-path test_case/test_login_case --clean
```

按 marker 运行：

```powershell
python runpytest.py -m smoke
```

E9 真实登录验收优先从 Jenkins Credentials 或进程环境变量读取私有凭据：
`E9_LOGINID` 与 `E9_USERPASSWORD` 必须同时配置。仅在本地调试且明确使用抓包账号时，
才回退读取 `test_data/account.json`。

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

## 开发约定

- 接口方法放在 `page_api/`，命名规范为 `模块名_api/`。
- pytest 用例放在 `test_case/test_模块名_case/`。
- 测试平台通过 `test_case/test_*_case/` 文件夹区分模块。
- 多层取值优先用 `get_value()`，单层取值优先用 `.get()`。
- 新增执行能力优先放在 `tools/`，供 Jenkins 和后端复用。
- 运行产物写入 `runtime/`，报告产物写入 `report/`，不要作为业务代码提交。
- 新功能和缺陷修复必须先写测试，按 RED -> GREEN -> REFACTOR 推进。

## 接口基类设计：Session 复用与 Cookie 自动持久化

`page_api/public/base_api.py` 中的 `BaseAPI` 是所有接口封装类的公共父类，其核心设计依赖 `requests.Session` 的内置 Cookie 持久化机制，实现零手动干预的登录态透传。

### 工作原理

```
LoginAPI 实例化
       │
       ▼
Step 1: get_rsa_info()     ──→  Session 懒创建，服务端可能下发初始 Cookie
       │                         (如 JSESSIONID、路由标识)
       ▼
Step 2: check_login()      ──→  POST 登录，服务端 Set-Cookie 写入登录态
       │                         Session 自动存入内部 cookieJar  ← 关键！
       ▼
Step 3: remind_login()     ──→  自动携带 Step2 的 Cookie ✓
       │
Step 4: is_weak_password() ──→  自动携带 Step2 的 Cookie ✓
       │
Step 5: get_os_info()      ──→  自动携带 Step2 的 Cookie ✓
```

### 关键设计点

1. **懒加载单例 Session**：`BaseAPI.get_base_request()` 只在首次请求时创建 `requests.Session`，同一实例内的所有接口调用复用同一个 Session，Cookie 自然透传。
2. **`requests.Session` 内置 Cookie Jar**：像浏览器一样自动接收 `Set-Cookie` 响应头并存入内部 `cookieJar`，后续同域请求自动携带，整个过程对调用方完全透明。
3. **零手动 Cookie 操作**：接口封装层（如 `LoginAPI`）无需读取 `response.cookies`、无需手动设置 `headers["Cookie"]`，也无需覆写 `__init__`——完全沿用 `BaseAPI` 的 Session 管理。

### 优势

- **代码简洁**：业务接口方法只关注请求参数和路径，不掺杂 Cookie 管理逻辑。
- **不易出错**：避免手动 Cookie 传递中的遗漏、过期、域名不匹配等问题。
- **跨用例复用**：同一 `BaseAPI` 子类实例可在同一测试会话中多次调用不同接口，登录态始终保持。
- **可测试性**：Session 隔离在实例级别，不同测试用例各自持有独立实例，互不干扰。

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