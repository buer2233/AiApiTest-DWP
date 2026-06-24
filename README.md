# AiApiTest-DWP

`AiApiTest-DWP` 是一个面向 AI 协作的 CICD 自动化测试平台项目。当前仓库正在从通用接口自动化框架升级为包含接口自动化执行、Jenkins Pipeline、DRF 后端、Vue 3 前端、失败用例重试和 Allure 报告展示的一体化测试平台。

本项目不绑定具体业务系统。所有接口测试、平台接口、Jenkins 配置和前端页面都应保持可迁移、可复用，不能提交真实账号、密码、token、cookie、租户密钥或生产环境地址。

## 当前目标

平台第一版目标是打通以下闭环：

- 在 `api-test/` 中运行 pytest 接口自动化用例并生成 Allure 结果。
- 通过 pytest node id 支持选择失败用例重试、一键失败重试和模块重试。
- 通过 `jenkins/` 中的 Groovy Pipeline 在 Jenkins 上触发本地接口自动化执行。
- 通过 `back-end/` 中的 DRF 服务管理用户、测试任务、失败用例、报告路径和 Jenkins 记录。
- 通过 `front-end/` 中的 Vue 3 页面展示模块通过率、失败用例、重试入口、Jenkins 任务入口和 Allure 报告入口。
- 通过 `back-end/` 受控服务 `/reports/<run_id>/` 打开 Allure 静态 HTML 报告。
- 所有阶段的需求、测试、实现和验证记录统一沉淀到 `docs/`。
- 项目架构说明书参考: `/project-info/项目架构说明书.md`

## 仓库结构

```text
AiApiTest-DWP/
├── api-test/                         # pytest 接口自动化执行核心
│   ├── config.py
│   ├── conftest.py
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── runpytest.py
│   ├── report/                       # Allure 原始结果和 HTML 报告
│   ├── runtime/                      # 抓包、CI 执行和临时运行产物
│   ├── test_case/                    # 接口方法和 pytest 用例
│   ├── test_data/
│   ├── tests/                        # api-test 自身单元测试
│   └── utils/
├── jenkins/                          # Jenkinsfile 和 Groovy Pipeline 脚本
├── back-end/                         # Django REST Framework 后端
├── front-end/                        # Vue 3 + Element Plus 前端
├── docs/
│   └── superpowers/plans/
│       └── 2026-06-22-cicd-test-platform.md
├── task_plan.md                      # 当前任务阶段计划
├── findings.md                       # 重要发现和决策
├── progress.md                       # 执行日志、测试命令和结果
└── AGENTS.md                         # 后续 AI 接手时必须遵守的协作规则
```

## 开发主计划

后续开发必须优先读取：

```text
docs/superpowers/plans/2026-06-22-cicd-test-platform.md
```

该文件记录了完整 10 阶段开发计划、验收命令、风险、进度和阶段要求。不要在不了解该文件的情况下继续开发，也不要另起无上下文的新计划替代它。

当前阶段顺序：

1. 需求冻结与计划确认
2. `api-test/` 迁移与充分测试
3. pytest node id 与失败重试执行器
4. Jenkins Groovy Pipeline
5. DRF 后端基础工程与用户角色
6. 测试任务与失败用例 API
7. Jenkins 查询与触发 API
8. Vue 3 前端基础与登录
9. 模块通过率与失败用例页面
10. 报告展示、联调、文档和交付

每个阶段都必须单独完成需求分析、测试用例、RED、开发、GREEN、重构、文档、`git commit` 和 `git push`。

## 快速运行 `api-test`

安装接口自动化依赖：

```bash
cd api-test
pip install -r requirements.txt
```

运行全部接口用例：

```bash
python runpytest.py
```

运行指定模块：

```bash
python runpytest.py --case-path test_case/test_gbif_case --clean
```

按 marker 运行：

```bash
python runpytest.py -m smoke
```

生成后打开 Allure 报告：

```bash
python runpytest.py --case-path test_case/test_gbif_case --open-report
```

Allure HTML 报告默认输出到：

```text
api-test/report/allure-report/<timestamp>/
```

如果本机未安装 Allure CLI，pytest 仍应正常返回测试退出码，脚本只跳过 HTML 报告生成。

## Docker 快速部署 MySQL 和 Jenkins

本项目支持通过 Docker 快速部署本地 MySQL 和 Jenkins。详细部署说明见 [docker/DEPLOYMENT.md](docker/DEPLOYMENT.md)。

## 平台运行手册

第一版平台运行、报告访问、失败重试和验证命令见 [docs/test-platform-runbook.md](docs/test-platform-runbook.md)。

最终联调记录见 [docs/final-integration-report.md](docs/final-integration-report.md)。

## 平台开发约定

### `api-test/`

- 接口方法放在 `api-test/test_case/page_api/`。
- pytest 用例放在 `api-test/test_case/test_*_case/`。
- 后续 Jenkins 和 DRF 都应调用 `api-test` 中的统一执行器，不重复实现 pytest 重试逻辑。
- 失败重试以 pytest node id 为核心数据结构。
- 运行产物写入 `api-test/runtime/`，报告写入 `api-test/report/`。

### `jenkins/`

- Jenkins 脚本必须通过 git 管理。
- Pipeline 使用 workspace 相对路径，不写死本机绝对路径。
- 必须兼容 Windows `bat` 和 Linux `sh`。
- Jenkins 参数、失败重试模式和 `api-test` 执行器参数必须保持一致。

### `back-end/`

- 使用 Django REST Framework。
- 认证使用 DRF Token。
- 默认数据库使用本地 MySQL，通过环境变量或本地私有配置提供连接信息。
- 预留管理员和普通用户角色，第一版权限可一致。
- Jenkins 相关测试使用 fake 响应，不依赖真实 Jenkins 服务。

### `front-end/`

- 使用 Vue 3、Vite、TypeScript、Vue Router、Pinia、Axios 和 Element Plus。
- 首页应是可操作测试平台，不做营销页。
- 核心页面包括模块通过率、失败用例弹窗、失败重试入口、Jenkins 任务入口和 Allure 报告入口。

## AI 接手要求

新的 AI 或工程师接手时，先按以下顺序恢复上下文：

1. 读取 `AGENTS.md`。
2. 读取 `docs/superpowers/plans/2026-06-22-cicd-test-platform.md`。
3. 读取 `task_plan.md`、`findings.md`、`progress.md`。
4. 执行 `git status --short`，确认已有改动。
5. 根据主计划进入当前未完成阶段，不要跳阶段开发。

阶段开发完成后，必须把测试命令、测试结果、问题和提交状态写回文档，确保后续无上下文 AI 也能继续工作。
