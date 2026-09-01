# E9+AI接口自动化测试框架（api-test）

这是 E9 系统专用的 E9+AI 接口自动化测试框架，底层使用 pytest。框架代码、接口方法、业务用例和 CI 执行器均位于当前 `api-test` 目录，可由平台 Jenkins 统一调度。

## 打开与常用口令

在仓库根目录的 `api-test` 文件夹下执行测试。常用命令如下：

| 目的 | 口令示例 |
| --- | --- |
| 配置环境 | Jenkins 推荐通过 `JENKINS_API_TEST_E9_CREDENTIALS_ID` 绑定 `E9_ACCOUNTS_JSON`；本地可设置 `TARGET_BASE_URL`（或 `E9_BASE_URL`）及角色变量 |
| 执行与报告 | 通过 Jenkins 调用 `python -m tools.ci_runner --from-jenkins-env` |
| 失败重试 | 使用 `--retry-mode selected` 或 `--retry-mode all-failed` |

## 命令速查

在 `api-test` 目录执行：

```powershell
python -m pip install -r requirements.txt
python -m pytest test_case --collect-only
python runpytest.py -m r349084 --clean
python runpytest.py --case-path test_case/test_login_case --clean
allure serve report/allure-results
```

Allure 报告通过 HTTP 服务访问，不建议直接用 `file://` 打开。统一执行参数见 [`docs/runner_spec.md`](docs/runner_spec.md)，接口封装和用例模板见 [`docs/api_test_case_spec.md`](docs/api_test_case_spec.md)。

## 目录与产物

- `page_api/`：接口方法封装；`test_case/`：pytest 用例；`test_data/`：模块测试数据。
- `report/`、`runtime/`、`logs/`：运行产物，不提交。

## 必须遵守

- 不在 `master` 上修改、commit、push 或 merge；push 前必须通过 readiness 检查并得到用户明确确认。
- 账号优先从 Jenkins Secret Text（`E9_ACCOUNTS_JSON`）或角色环境变量读取：管理员使用 `E9_LOGINID` / `E9_USERPASSWORD`，普通成员使用 `E9_EMPLOYEE<n>_LOGINID` / `E9_EMPLOYEE<n>_PASSWORD`；不得把真实凭据写入代码、日志或报告。
- 不提交运行时产物；新增执行能力先在 `tests/` 编写测试。

完整执行参数见 [`docs/runner_spec.md`](docs/runner_spec.md)，接口封装规范见 [`docs/api_test_case_spec.md`](docs/api_test_case_spec.md)。
