# api-test/AGENTS.md

本目录是 **E9 专用接口自动化测试框架**。进入 `api-test/` 工作前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

> **按需读取文档**（均在 `docs/` 目录下）：
> - 执行命令、CI 参数、失败重试 → `docs/runner_spec.md`
> - 新增用例指南、接口封装规范、编码模板 → `docs/api_test_case_spec.md`

---

## 一、框架定位

- 本框架是 **E9 系统专用**的接口自动化测试框架，不包含 E9 以外的任何业务模块。
- `api-test/` 是 pytest 用例、接口方法、失败 node id、重试执行器和 Allure 原始结果的唯一实现位置。
- Jenkins 只负责调度本目录的统一执行器；DRF 后端只读取 Jenkins 状态和执行产物，不直接拼 pytest 命令。
- 本目录不实现 Jenkins Groovy 编排、DRF API、Vue 页面、数据库模型或平台权限逻辑。

---

## 二、技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| 测试框架 | **pytest 7.4** | 用例发现、执行、断言 |
| HTTP 客户端 | **requests 2.32** + `curl_cffi`（可选） | 发送 HTTP 请求，支持 TLS 指纹模拟 |
| 报告 | **allure-pytest 2.13** | 生成 Allure 原始结果和 HTML 报告 |
| 失败重试 | **pytest-rerunfailures 16** | 用例级失败自动重跑 |
| 配置 | **PyYAML 6.0** | 环境目录和模块目录的 YAML 配置 |
| 报告增强 | **pytest-html 3.1** + **pytest-metadata 2.0** | 辅助报告能力 |

---

## 三、目录约定

```text
api-test/
├── config.py                    # 全局配置（base_url、超时、headers、路径等）
├── conftest.py                  # pytest 命令行参数和 session fixture
├── pytest.ini                   # pytest 发现规则
├── requirements.txt             # Python 依赖
├── runpytest.py                 # 本地执行入口
│
├── docs/                        # 框架文档（按需读取）
│   ├── runner_spec.md            #   执行命令参考手册
│   └── api_test_case_spec.md    #   用例与接口方法编写规范
│
├── page_api/                    # ★ 接口方法封装层
│   ├── public/                  #   公共基类 BaseAPI（不可删改）
│   └── login_api/               #   登录模块接口封装（命名规范: 模块名_api）
│
├── test_case/                   # ★ pytest 接口用例层
│   └── test_login_case/         #   登录模块用例（命名规范: test_模块名_case）
│
├── test_data/                   # 通用脱敏测试数据
│   └── account.json             #   测试账号
├── tests/                       # api-test 框架自身单元测试
├── tools/                       # 可复用工具（ci_runner、nodeids、脱敏等）
├── utils/                       # 通用辅助能力
│   ├── common_function.py       #   全框架通用方法（如 load_account）
│   ├── timeout_http_adapter.py  #   超时适配器
│   ├── package_environment.yaml #   环境目录
│   └── package_module.yaml      #   模块目录
├── report/                      # Allure 产物（不提交）
├── runtime/                     # CI 运行时产物（不提交）
└── logs/                        # 日志（不提交）
```

### 命名规范（对齐 E10 框架）

| 层级 | 规范 | 正确示例 | 错误示例 |
|------|------|---------|---------|
| 接口方法目录 | `page_api/模块名_api/` | `page_api/login_api/` | ~~`page_api/E9/login_api/`~~ |
| 测试用例目录 | `test_case/test_模块名_case/` | `test_case/test_login_case/` | ~~`test_case/test_E9_login_case/`~~ |

> 新增模块时按上述规范创建目录即可，**无需在外层再套 E9 前缀**。框架通过 `config.py` 的 `base_url` 指向 E9 环境，目录结构保持通用。

---

## 四、核心架构

### 4.1 请求链路

```
pytest 用例
    │
    ├── conftest.py → base_url fixture（可从命令行 --base-url 覆盖）
    │
    ▼
LoginAPI(base_url)                ← 继承 BaseAPI
    │
    ├── self.get("/api/...")      ← 调用 BaseAPI.get()
    ├── self.post("/api/...")     ← 调用 BaseAPI.post()
    │
    ▼
BaseAPI.request()
    ├── build_url()               ← 拼接 base_url + 相对路径
    ├── get_base_request()        ← 懒加载 requests.Session（复用 Cookie）
    ├── session.request()         ← 发送 HTTP 请求
    ├── assert status_code        ← 断言 HTTP 状态码
    └── return response.json()    ← 返回 JSON 给用例做业务断言
```

### 4.2 关键设计

1. **Session 复用**：`BaseAPI` 内部维护一个 `requests.Session` 实例（懒加载），同一实例内的所有接口调用共享 Cookie，登录态自动透传，无需手动管理。

2. **配置优先级**：命令行 `--base-url` > `config.py` 的 `base_url`。`BaseAPI.__init__` 的参数 > `config.py` 的全局默认值。

3. **数据取值**：`BaseAPI.get_value(data, list_key)` 支持按路径从嵌套 JSON 中取值，常见 `{"data": {"data": [...]}}` 结构可直接用 `get_value(response)`。

4. **curl_cffi 支持**：`config.use_curl_cffi = True` 时，Session 使用 `curl_cffi` 模拟浏览器 TLS 指纹（绕过 Cloudflare 等 WAF），默认模拟 Chrome。

---

## 五、固定 loop 中的位置

- 当需求涉及测试执行协议、pytest 参数、失败重试、模块重试、Allure 产物、summary 输出或用例组织方式时，必须先确认对应需求文档、功能测试用例和必要的 UI/API 契约已经存在。
- 修改执行器或工具代码时，必须先在 `tests/` 编写并运行 pytest 测试，确认失败由目标行为缺失导致，再做最小实现、目标测试 GREEN、重构和相关回归，遵循 `RED -> GREEN -> REFACTOR`。
- 新增业务自动化用例前，应能追溯到 `project-info/demand/` 的需求和 `project-info/test_case/` 的测试设计，不允许脱离 loop 直接堆用例。

---

## 六、测试要求

- 新增或修改执行能力必须先写 `tests/` 下的 pytest 测试。
- 不得通过弱化断言、跳过用例或只运行避开失败的测试子集获得 GREEN；首次失败若来自路径、依赖或测试自身，应先修复测试环境并重新取得有效 RED。
- 修改失败重试、summary、Allure 归档或 node id 逻辑时，必须覆盖正常执行、失败执行、重试成功、重试仍失败、空失败列表和路径不存在等场景。

---

## 七、安全和禁止事项

- 不在用例或配置中提交真实账号、密码、token、cookie、租户密钥、生产 URL 或敏感地址。
- 不把重试逻辑复制到 Jenkins Groovy、DRF 后端或 Vue 前端。
- 不提交 `runtime/`、`report/allure-results/`、`report/allure-report/`、`logs/`、`.pytest_cache/`、`__pycache__/` 等产物。
- 不在 `page_api/` 和 `test_case/` 中硬编码 IP 地址或域名，统一使用 `config.base_url` 或 `base_url` fixture。