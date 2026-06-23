# back-end

`back-end` 是 AiApiTest-DWP 的 Django REST Framework 后端目录，后续负责用户登录、角色、测试任务、失败用例、报告入口，以及 Jenkins 查询和触发 API。

当前阶段尚未开始后端实现。正式开发会在 Stage 5、Stage 6 和 Stage 7 分阶段完成。

## 目标职责

- 使用 DRF Token 提供登录、退出和当前用户接口。
- 保留 `admin` 和 `member` 两类用户角色。
- 使用本地 MySQL 作为默认数据库。
- 管理测试任务、失败用例、重试任务和报告路径。
- 对接 Jenkins job/build 查询、触发和日志查看。
- 调用 `api-test/tools/ci_runner.py` 或登记 Jenkins 返回结果，避免重复实现 pytest 重试逻辑。

## 计划阶段

| 阶段 | 内容 |
|------|------|
| Stage 5 | DRF 后端基础工程与用户角色 |
| Stage 6 | 测试任务与失败用例 API |
| Stage 7 | Jenkins 查询与触发 API |

## 预期结构

```text
back-end/
├── manage.py
├── requirements.txt
├── pytest.ini
├── config/
│   ├── settings.py
│   └── urls.py
├── apps/
│   ├── accounts/
│   ├── test_runs/
│   └── jenkins_integration/
└── tests/
```

## 后续测试命令

Stage 5 预期：

```powershell
python -m pytest tests/test_accounts_api.py -v
```

Stage 6 预期：

```powershell
python -m pytest tests/test_test_runs_api.py tests/test_allure_results_parser.py -v
```

Stage 7 预期：

```powershell
python -m pytest tests/test_jenkins_client.py tests/test_jenkins_api.py -v
```

## 配置原则

- 数据库连接从环境变量或本地私有配置读取。
- 不提交真实 MySQL 密码、Jenkins Token 或内部服务地址。
- Jenkins client 测试必须使用 fake HTTP 响应，不依赖真实 Jenkins。
