# CICD Test Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有接口自动化框架基础上，分阶段建设 Jenkins CICD、DRF 后端、Vue 3 前端测试平台，并支持用例执行、失败用例重试、模块重试、Allure 报告展示和 Jenkins 执行查询。

**Architecture:** 仓库拆分为 `api-test/`、`jenkins/`、`back-end/`、`front-end/` 四个主目录。`api-test/` 保留并增强接口自动化执行能力，`jenkins/` 通过 Groovy Pipeline 调用本地接口自动化，`back-end/` 通过 DRF 管理任务、失败用例、报告和 Jenkins 记录，`front-end/` 使用 Vue 3 展示模块通过率、失败用例、重试入口和报告入口。

**Tech Stack:** Python、pytest、allure-pytest、Allure CLI、Jenkins Pipeline Groovy、Django、Django REST Framework、本地 MySQL 数据库、Vue 3、Vite、TypeScript、Element Plus、Pinia、Vue Router、Axios。

---

## 1. 已确认需求

| 编号 | 需求 | 决策 |
|------|------|------|
| R1 | 前端技术栈 | Vue 3，目录 `front-end/` |
| R2 | 后端技术栈 | Python DRF，目录 `back-end/` |
| R3 | 接口测试框架位置 | 迁移到 `api-test/` |
| R4 | 迁移内容 | `report/`、`test_case/`、`test_data/`、`utils/`、`config.py`、`conftest.py`、`pytest.ini`、`requirements.txt`、`runpytest.py` |
| R5 | 迁移验收 | 迁移后执行 `python runpytest.py --case-path test_case/test_gbif_case --clean`，验证路径和运行能力 |
| R6 | Jenkins 优先级 | 第一阶段先实现 Jenkins，再开发网页端平台 |
| R7 | Jenkins 目录 | `jenkins/` |
| R8 | Jenkins 实现方式 | Groovy Pipeline 调用本地接口自动化测试、失败重试、Allure 报告生成 |
| R9 | 失败重试 | 支持选择一个或多个失败用例重试、一键重跑全部失败用例、模块重试 |
| R10 | 失败重试实现依据 | 通过组合 pytest node id 进行重跑 |
| R11 | 模块定义 | 测试平台通过 `test_case/test_*_case/` 文件夹区分模块 |
| R12 | 报告展示 | 平台展示失败用例简要信息，并支持点击打开 Allure 报告 |
| R13 | 用户权限 | 保留管理员和普通用户角色，当前权限一致，但模型预留差异化权限空间 |
| R14 | UI 参考 | 参考现有公司测试平台截图，但不完整照搬 |
| R15 | 开发方式 | 大型任务分 10 个阶段开发，每个阶段执行完整 TDD 流程，并持续更新本计划文档 |
| R16 | 阶段流程 | 每个阶段单独进行需求分析、编写测试用例、开发、测试 |
| R17 | 版本管理 | 每个阶段开发和测试完成后，单独执行 `git commit` 和 `git push` |
| R18 | 后端认证 | 使用 DRF Token |
| R19 | 后端数据库 | 强制使用本地 MySQL 数据库，连接 `localhost:3306` |
| R20 | 前端组件库 | 使用 Element Plus |
| R21 | Jenkins 脚本管理 | Groovy/Jenkins 脚本源文件存放在 `jenkins/`，通过 git 版本管理 |
| R22 | Jenkins 兼容性 | Jenkins 脚本确认兼容 Windows 和 Linux |
| R23 | Allure 报告展示 | 打开静态 HTML 报告 |
| R24 | 文档归档 | 开发和测试中产生的文档全部记录在 `docs/` |

## 2. 已确认技术选型与流程

| 项目 | 已确认方案 |
|------|------------|
| 开发阶段 | 10 个阶段，每个阶段独立需求分析、测试、开发、验证、提交、推送 |
| TDD 顺序 | 需求分析 -> 编写测试用例 -> 运行测试确认 RED -> 开发 -> 运行测试确认 GREEN -> 重构 -> 回归测试 |
| Git 流程 | 每个阶段完成后单独 `git commit`，随后 `git push` |
| 文档位置 | 所有开发和测试文档统一放在 `docs/` |
| 后端认证 | DRF Token |
| 后端数据库 | 本地 MySQL `localhost:3306` |
| 前端组件库 | Element Plus |
| Jenkins 脚本 | 源文件放在 `jenkins/`，纳入 git 版本管理 |
| Jenkins 兼容 | Windows 和 Linux 双兼容 |
| Allure 展示 | 打开静态 HTML 报告 |

## 3. 目标目录结构

```text
D:/AI/AiApiTest-DWP/
├── api-test/
│   ├── config.py
│   ├── conftest.py
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── runpytest.py
│   ├── report/
│   ├── runtime/
│   ├── test_case/
│   ├── test_data/
│   ├── tests/
│   └── utils/
├── jenkins/
│   ├── Jenkinsfile
│   ├── README.md
│   └── scripts/
│       └── api-test-pipeline.groovy
├── back-end/
│   ├── manage.py
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── config/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── test_runs/
│   │   └── jenkins_integration/
│   └── tests/
├── front-end/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── router/
│   │   ├── stores/
│   │   └── views/
│   └── tests/
├── docs/
│   ├── superpowers/plans/2026-06-22-cicd-test-platform.md
│   ├── api-test-migration.md
│   ├── jenkins-setup.md
│   ├── back-end-setup.md
│   ├── front-end-setup.md
│   └── test-platform-runbook.md
├── task_plan.md
├── findings.md
└── progress.md
```

## 4. 总体阶段顺序

| 阶段 | 名称 | 状态 | 目标 |
|------|------|------|------|
| Stage 1 | 需求冻结与计划确认 | complete | 固化开发流程、阶段顺序、技术选型和文档规则 |
| Stage 2 | `api-test/` 迁移与充分测试 | complete | 将分散的测试框架内容全部转移到 `api-test/` 并充分验证 |
| Stage 3 | pytest node id 与失败重试执行器 | complete | 提供可被 Jenkins 和后端复用的 node id 收集、失败用例重跑能力 |
| Stage 4 | Jenkins Groovy Pipeline | complete | Jenkins 可执行用例、重试用例、生成 Allure 报告、归档结果 |
| Stage 5 | DRF 后端基础工程与用户角色 | complete | 建立 DRF Token 认证、本地 MySQL、管理员/普通用户角色 |
| Stage 6 | 测试任务与失败用例 API | complete | 保存测试任务、失败用例、重试任务、报告路径和执行日志 |
| Stage 7 | Jenkins 查询与触发 API | complete | 后端支持 Jenkins job/build 查询、触发、日志查看，并兼容 Windows/Linux |
| Stage 8 | Vue 3 前端基础与登录 | pending | 建立 Vue 3、Element Plus、登录态、布局、菜单 |
| Stage 9 | 模块通过率与失败用例页面 | pending | 实现参考截图的模块列表、失败用例弹窗、重试入口 |
| Stage 10 | 报告展示、联调、文档和交付 | pending | 打开 Allure 静态 HTML 报告，完成全链路联调和文档交付 |

## 5. 阶段开发规则

每个阶段必须单独完成以下流程，不跨阶段混合提交：

1. 需求分析：明确本阶段范围、输入、输出、验收标准和不做事项。
2. 编写测试用例：生产代码前先写自动化测试。
3. 验证 RED：运行精确测试命令，确认失败原因是目标功能缺失。
4. 开发：只写让当前阶段测试通过的最小实现。
5. 测试：运行本阶段测试和必要回归测试，确认 GREEN。
6. 重构：只在测试通过后清理代码，并再次运行测试。
7. 更新文档：把需求分析、测试命令、测试结果、问题记录到 `docs/`。
8. Git 提交：本阶段开发和测试完成后，单独 `git commit`。
9. Git 推送：提交完成后执行 `git push`。

阶段提交前检查：

- [ ] 本阶段所有测试先经历 RED，再经历 GREEN。
- [ ] 本阶段相关文档已记录到 `docs/`。
- [ ] 未提交真实账号、密码、token、cookie、租户密钥或敏感地址。
- [ ] `git status` 中只包含本阶段相关改动或已明确说明的既有改动。
- [ ] 已完成本阶段 `git commit` 和 `git push`。

## 6. Stage 1: 需求冻结与计划确认

**Files:**
- Create: `docs/superpowers/plans/2026-06-22-cicd-test-platform.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`

- [x] **Step 1: 记录用户架构约束**

已记录 Vue 3、DRF、`api-test/`、`jenkins/`、Jenkins 优先、失败重试、用户角色、参考 UI、分阶段 TDD 等要求。

- [x] **Step 2: 记录截图关键信息**

已记录模块通过率列表、失败用例弹窗、筛选区、重试按钮、Jenkins 任务入口和 Allure 报告入口。

- [x] **Step 3: 用户确认技术选型与流程**

已确认：

```text
DRF 认证：DRF Token
数据库：本地 MySQL
前端组件库：Element Plus
Allure 第一版展示方式：打开静态 HTML
Jenkins 脚本兼容策略：Windows/Linux 双兼容
Jenkins 脚本源文件：jenkins/
开发和测试文档：docs/
每阶段流程：需求分析 -> 编写测试用例 -> 开发 -> 测试 -> git commit -> git push
```

- [x] **Step 4: 更新核心接续文档**

已将 `AGENTS.md` 和 `README.md` 从旧的单体接口自动化框架说明更新为 CICD AI 自动化测试平台说明。

更新重点：
- `AGENTS.md` 明确后续 AI 必须先读取主计划、`task_plan.md`、`findings.md`、`progress.md` 和 `README.md`，避免丢失多阶段上下文。
- `AGENTS.md` 明确 `api-test/`、`jenkins/`、`back-end/`、`front-end/`、`docs/` 的职责边界。
- `AGENTS.md` 保留“每次回复开头必须叫主人”、默认简体中文、敏感信息禁止提交等规则。
- `README.md` 改为平台总览，说明当前目标、目录结构、10 阶段开发计划、`api-test` 快速运行方式和 AI 接手流程。

- [x] **Step 5: 用户确认进入 Stage 2**

确认后开始执行 `api-test/` 迁移。迁移会移动文件并运行测试验证。

## 7. Stage 2: `api-test/` 迁移与充分测试

**Files:**
- Move: `report/` -> `api-test/report/`
- Move: `test_case/` -> `api-test/test_case/`
- Move: `test_data/` -> `api-test/test_data/`
- Move: `utils/` -> `api-test/utils/`
- Move: `config.py` -> `api-test/config.py`
- Move: `conftest.py` -> `api-test/conftest.py`
- Move: `pytest.ini` -> `api-test/pytest.ini`
- Move: `requirements.txt` -> `api-test/requirements.txt`
- Move: `runpytest.py` -> `api-test/runpytest.py`
- Create: `api-test/tests/test_runpytest_commands.py`
- Modify: `api-test/runpytest.py`
- Modify: `api-test/pytest.ini`
- Modify: `README.md`
- Create: `docs/api-test-migration.md`

- [x] **Step 1: 写迁移后路径测试**

测试文件：`api-test/tests/test_runpytest_commands.py`

目标行为：
- `build_pytest_command()` 默认执行 `test_case`。
- 自定义 `case_path` 可以传入模块目录。
- `build_allure_generate_command()` 使用 `api-test/report/allure-results` 和 `api-test/report/allure-report`。
- `ensure_runtime_dirs()` 创建 `report/`、`runtime/`、`logs/`、Allure 结果目录。

运行命令：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_runpytest_commands.py -v
```

预期 RED：测试文件存在后，至少因 `api-test/` 尚未迁移或路径未适配失败。

- [x] **Step 2: 移动接口自动化框架文件**

使用 PowerShell `Move-Item -LiteralPath` 逐项移动，移动前确认目标路径均位于 `D:\AI\AiApiTest-DWP\api-test`。

- [x] **Step 3: 调整 `runpytest.py` 默认入口**

把脚本入口调整为默认 `main()`，通过命令行参数选择模块，避免固定写死 `test_case/test_gbif_case`。

验收命令：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python runpytest.py --case-path test_case/test_gbif_case --clean
```

预期：pytest 正常启动；如果外部公开 API 限流导致个别用例 skip 或 fail，需要记录实际失败原因，优先修复路径类问题。

- [x] **Step 4: 验证 GREEN**

运行：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_runpytest_commands.py -v
python runpytest.py --case-path test_case/test_gbif_case --clean
```

完成标准：
- 单元测试通过。
- `runpytest.py` 可在 `api-test/` 下执行。
- Allure 原始结果写入 `api-test/report/allure-results`。
- Allure HTML 报告写入 `api-test/report/allure-report/<timestamp>`，如果本机未安装 Allure CLI，脚本明确提示并保持 pytest 退出码。
- `docs/api-test-migration.md` 记录迁移内容、测试命令、测试结果、发现的问题和解决方案。
- 完成单独 `git commit` 和 `git push`。

## 8. Stage 3: pytest node id 与失败重试执行器

**Files:**
- Create: `api-test/tools/__init__.py`
- Create: `api-test/tools/pytest_nodeids.py`
- Create: `api-test/tools/ci_runner.py`
- Create: `api-test/tests/test_pytest_nodeids.py`
- Create: `api-test/tests/test_ci_runner.py`
- Modify: `api-test/requirements.txt`
- Create: `docs/pytest-nodeid-retry-runner.md`

- [x] **Step 1: 写 node id 读取失败测试**

测试目标：
- 从 `.pytest_cache/v/cache/lastfailed` 读取失败 node id。
- 支持返回列表格式，保持 pytest 原始 node id 字符串。
- cache 文件不存在时返回空列表。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_pytest_nodeids.py -v
```

预期 RED：`tools.pytest_nodeids` 尚不存在。

- [x] **Step 2: 实现 `pytest_nodeids.py`**

功能：
- `load_lastfailed(cache_dir: Path) -> list[str]`
- `write_nodeids(nodeids: list[str], output_path: Path) -> None`
- `normalize_nodeids(raw_values: list[str]) -> list[str]`

完成标准：
- 不依赖真实业务用例。
- cache JSON 损坏时返回清晰异常，调用方可记录错误。

- [x] **Step 3: 写 CI runner 命令构造测试**

测试目标：
- 模块运行：`python -m pytest test_case/test_gbif_case --alluredir=<run_dir>/allure-results`
- 选择 node id 运行：`python -m pytest nodeid1 nodeid2 --alluredir=<run_dir>/allure-results`
- 一键失败重试：读取 lastfailed 后组合 node id 重跑。
- 输出 `summary.json`，包含 `status`、`return_code`、`failed_nodeids`、`allure_results_dir`、`allure_report_dir`。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_ci_runner.py -v
```

预期 RED：`tools.ci_runner` 尚不存在。

- [x] **Step 4: 实现 `ci_runner.py`**

命令行参数：

```text
--case-path test_case/test_gbif_case
--node-id <pytest node id>              可重复传入
--retry-mode none|selected|all-failed|module
--retry-count 0..N
--run-id <external id>
--clean
--open-report
```

输出目录：

```text
api-test/runtime/ci-runs/<run_id>/
├── console.log
├── failed_nodeids.json
├── summary.json
├── allure-results/
└── allure-report/
```

完成标准：
- Jenkins 和 DRF 后续都调用同一个执行器。
- 重试能力不写在 Groovy 和 DRF 两处，避免逻辑分叉。
- `docs/pytest-nodeid-retry-runner.md` 记录 node id 来源、重试模式、测试命令和测试结果。
- 完成单独 `git commit` 和 `git push`。

执行结果：

```text
RED:
- tests/test_pytest_nodeids.py: ModuleNotFoundError: No module named 'tools'
- tests/test_ci_runner.py: ModuleNotFoundError: No module named 'tools'
- stale lastfailed 补强测试: 1 failed, 6 passed
- retry_count 负数边界测试: 1 failed

GREEN:
- python -m pytest tests/test_pytest_nodeids.py tests/test_ci_runner.py -v -> 13 passed
- python -m pytest tests -v -> 20 passed
- python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id stage3-smoke --clean -> exit code 0
```

## 9. Stage 4: Jenkins Groovy Pipeline

**Files:**
- Create: `jenkins/Jenkinsfile`
- Create: `jenkins/scripts/api-test-pipeline.groovy`
- Create: `jenkins/README.md`
- Modify: `api-test/tools/ci_runner.py`
- Modify: `api-test/tests/test_ci_runner.py`
- Create: `docs/jenkins-pipeline.md`

- [x] **Step 1: 写 CI runner 的 Jenkins 参数兼容测试**

测试目标：
- 支持 Jenkins 传入 `CASE_PATH`。
- 支持 Jenkins 传入多个 node id，分隔符使用换行或英文逗号。
- 支持 Jenkins 传入 `RETRY_MODE=all-failed` 和 `RETRY_COUNT=1`。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_ci_runner.py -v
```

- [x] **Step 2: 实现 Groovy Pipeline 参数**

Jenkins 参数：

```text
CASE_PATH              默认 test_case/test_gbif_case
PYTEST_NODE_IDS        多个 pytest node id，换行分隔
RETRY_MODE             none / selected / all-failed / module
RETRY_COUNT            默认 0
CLEAN_ALLURE           默认 true
OPEN_REPORT            默认 false
```

- [x] **Step 3: 实现 Jenkins stages**

Pipeline 阶段：

```text
Checkout
Prepare Python
Install API Test Requirements
Run API Tests
Generate Allure Report
Archive Runtime Artifacts
Publish Allure
```

实现原则：
- Groovy 负责参数、环境变量和 Jenkins stage。
- 实际 pytest 执行、失败 node id 收集、summary 输出由 `api-test/tools/ci_runner.py` 完成。
- 使用 `isUnix()` 分支兼容 `sh` 和 `bat`。

- [x] **Step 4: Jenkins 本地验收**

在 Jenkins job 中配置仓库根目录后运行。

完成标准：
- Jenkins 可触发 `api-test` 测试。
- 构建页可看到控制台日志。
- 构建产物包含 `runtime/ci-runs/<run_id>/summary.json`、`failed_nodeids.json`、Allure 原始结果。
- Allure 插件可展示报告；如果环境没有插件，仍归档 HTML 报告目录。
- Groovy/Jenkins 脚本源文件均位于 `jenkins/` 并纳入 git 管理。
- Jenkins Pipeline 兼容 Windows `bat` 和 Linux `sh`。
- `docs/jenkins-pipeline.md` 记录 Jenkins 参数、脚本说明、测试命令和验证结果。
- 完成单独 `git commit` 和 `git push`。

执行结果：

```text
RED:
- api-test/tests/test_ci_runner.py: 2 failed, 8 passed，缺少 Jenkins node id 解析和 env -> RunRequest 适配函数
- jenkins/tests/test_pipeline_static.py: 3 failed，缺少 Jenkinsfile 和 Groovy Pipeline 脚本
- jenkins/tests/test_pipeline_static.py::test_pipeline_preserves_artifacts_when_pytest_fails: 1 failed，失败后不会继续归档产物

GREEN:
- cd api-test; python -m pytest tests/test_ci_runner.py -v -> 10 passed
- cd jenkins; python -m pytest tests/test_pipeline_static.py -v -> 4 passed
- cd api-test; python -m pytest tests -v -> 22 passed
- cd jenkins; python -m pytest tests -v -> 4 passed
- cd api-test; python -m tools.ci_runner --from-jenkins-env -> exit code 0，Allure HTML 生成成功
```

## 10. Stage 5: DRF 后端基础工程与用户角色

**Files:**
- Create: `back-end/manage.py`
- Create: `back-end/requirements.txt`
- Create: `back-end/pytest.ini`
- Create: `back-end/config/settings.py`
- Create: `back-end/config/urls.py`
- Create: `back-end/apps/accounts/models.py`
- Create: `back-end/apps/accounts/serializers.py`
- Create: `back-end/apps/accounts/views.py`
- Create: `back-end/apps/accounts/permissions.py`
- Create: `back-end/tests/test_accounts_api.py`
- Create: `docs/back-end-accounts.md`

- [x] **Step 1: 写登录和角色测试**

测试目标：
- 用户可登录并获得 token。
- `admin` 和 `member` 两种角色可保存。
- 当前两个角色访问平台 API 权限一致。
- 权限类中保留管理员独有权限判断入口。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\back-end
python -m pytest tests/test_accounts_api.py -v
```

预期 RED：Django 工程和 accounts app 尚不存在。

- [x] **Step 2: 创建 Django/DRF 工程**

默认配置：
- 本地 MySQL 数据库，连接地址固定为 `localhost:3306`。
- `AUTH_USER_MODEL = "accounts.User"`。
- DRF Token 认证。
- CORS 允许本地前端开发地址。

- [x] **Step 3: 实现 accounts**

模型：

```text
User.username
User.role = admin | member
```

API：

```text
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

完成标准：
- 账户测试通过。
- 可创建管理员和普通用户。
- `docs/back-end-accounts.md` 记录本地 MySQL 配置、迁移命令、测试命令和测试结果。
- 完成单独 `git commit` 和 `git push`。

执行结果：

```text
RED:
- back-end/tests/test_accounts_api.py: ImproperlyConfigured: Requested setting AUTH_USER_MODEL, but settings are not configured.
- create_superuser 补强测试: 1 failed，默认 role 为 member，不符合管理员创建验收。

GREEN:
- cd back-end; python -m pytest tests/test_accounts_api.py -v -> 6 passed
- cd back-end; python manage.py check -> System check identified no issues
```

## 11. Stage 6: 测试任务与失败用例 API

**Files:**
- Create: `back-end/apps/test_runs/models.py`
- Create: `back-end/apps/test_runs/serializers.py`
- Create: `back-end/apps/test_runs/services/api_test_runner.py`
- Create: `back-end/apps/test_runs/services/allure_results_parser.py`
- Create: `back-end/apps/test_runs/views.py`
- Create: `back-end/apps/test_runs/urls.py`
- Create: `back-end/tests/test_test_runs_api.py`
- Create: `back-end/tests/test_allure_results_parser.py`
- Create: `docs/test-runs-api.md`

- [x] **Step 1: 写模型和 API 测试**

测试目标：
- 创建测试任务。
- 查询测试任务列表。
- 查询测试任务详情。
- 查询失败用例列表。
- 选择失败用例重试。
- 一键重试全部失败用例。
- 按模块路径重试。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\back-end
python -m pytest tests/test_test_runs_api.py -v
```

- [x] **Step 2: 实现数据模型**

核心模型：

```text
TestRun
- id
- run_id
- case_path
- node_ids
- retry_mode
- retry_count
- status
- triggered_by
- trigger_source
- report_path
- allure_results_path
- console_log_path
- started_at
- finished_at
- summary

FailureCase
- id
- test_run
- node_id
- case_name
- module_path
- description
- error_type
- assertion_message
- status
- retry_status
- last_retry_run
```

- [x] **Step 3: 实现 Allure 结果解析**

解析来源：

```text
api-test/runtime/ci-runs/<run_id>/allure-results/*.json
```

输出：
- 失败用例 node id。
- 用例名。
- 用例描述。
- 错误类型。
- 断言/错误信息。
- 执行状态。

- [x] **Step 4: 实现 API**

API：

```text
GET  /api/test-runs/
POST /api/test-runs/
GET  /api/test-runs/{id}/
GET  /api/test-runs/{id}/failures/
POST /api/test-runs/{id}/retry-selected/
POST /api/test-runs/{id}/retry-all-failed/
POST /api/test-runs/{id}/retry-module/
GET  /api/test-runs/{id}/report/
```

完成标准：
- API 测试通过。
- 后端可调用 `api-test/tools/ci_runner.py` 或登记 Jenkins 返回的执行结果。
- `docs/test-runs-api.md` 记录模型、接口、请求响应示例、测试命令和测试结果。
- 完成单独 `git commit` 和 `git push`。

执行结果：

```text
RED:
- tests/test_allure_results_parser.py: ModuleNotFoundError: No module named 'apps.test_runs'
- tests/test_test_runs_api.py: ModuleNotFoundError: No module named 'apps.test_runs'

GREEN:
- cd back-end; python -m pytest tests/test_allure_results_parser.py tests/test_test_runs_api.py -v -> 9 passed
- cd back-end; python manage.py check -> System check identified no issues
- cd back-end; python -m pytest -v -> 19 passed
```

## 12. Stage 7: Jenkins 查询与触发 API

**Files:**
- Create: `back-end/apps/jenkins_integration/models.py`
- Create: `back-end/apps/jenkins_integration/client.py`
- Create: `back-end/apps/jenkins_integration/serializers.py`
- Create: `back-end/apps/jenkins_integration/views.py`
- Create: `back-end/apps/jenkins_integration/urls.py`
- Create: `back-end/tests/test_jenkins_client.py`
- Create: `back-end/tests/test_jenkins_api.py`
- Create: `docs/jenkins-api.md`

- [x] **Step 1: 写 Jenkins client 测试**

测试目标：
- 查询 job 列表。
- 查询 build 列表。
- 查询 build 状态。
- 查询 build console log。
- 触发参数化 build。
- Jenkins 凭据从环境变量或 Django settings 读取，不写死。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\back-end
python -m pytest tests/test_jenkins_client.py tests/test_jenkins_api.py -v
```

- [x] **Step 2: 实现 Jenkins client**

配置项：

```text
JENKINS_BASE_URL
JENKINS_USERNAME
JENKINS_API_TOKEN
JENKINS_DEFAULT_JOB
```

API：

```text
GET  /api/jenkins/jobs/
GET  /api/jenkins/jobs/{job_name}/builds/
GET  /api/jenkins/jobs/{job_name}/builds/{build_number}/
GET  /api/jenkins/jobs/{job_name}/builds/{build_number}/console/
POST /api/jenkins/jobs/{job_name}/build/
```

完成标准：
- 测试中使用 fake Jenkins HTTP 响应，不依赖真实 Jenkins。
- 真实 Jenkins 参数不提交到仓库。
- 后端 Jenkins API 与 `jenkins/` 中的 Pipeline 参数保持一致。
- `docs/jenkins-api.md` 记录 Jenkins 配置、Windows/Linux 兼容注意事项、测试命令和测试结果。
- 完成单独 `git commit` 和 `git push`。

执行结果：

```text
RED:
- tests/test_jenkins_client.py: ModuleNotFoundError: No module named 'apps.jenkins_integration'
- tests/test_jenkins_api.py: ModuleNotFoundError: No module named 'apps.jenkins_integration'

GREEN:
- cd back-end; python -m pytest tests/test_jenkins_client.py tests/test_jenkins_api.py -v -> 12 passed
- cd back-end; python manage.py check -> System check identified no issues
- cd back-end; python manage.py makemigrations --check --dry-run -> No changes detected
- cd back-end; python -m pytest -v -> 31 passed
```

## 13. Stage 8: Vue 3 前端基础与登录

**Files:**
- Create: `front-end/package.json`
- Create: `front-end/vite.config.ts`
- Create: `front-end/src/main.ts`
- Create: `front-end/src/router/index.ts`
- Create: `front-end/src/stores/auth.ts`
- Create: `front-end/src/api/http.ts`
- Create: `front-end/src/api/auth.ts`
- Create: `front-end/src/views/LoginView.vue`
- Create: `front-end/src/layouts/AppLayout.vue`
- Create: `front-end/tests/auth.spec.ts`
- Create: `docs/front-end-login.md`

- [ ] **Step 1: 写前端登录测试**

测试目标：
- 未登录访问平台页跳转到登录页。
- 登录成功保存 token 和用户信息。
- `admin`、`member` 都能进入平台。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\front-end
npm test -- auth.spec.ts
```

- [ ] **Step 2: 创建 Vue 3 工程**

默认依赖：
- Vue 3
- Vite
- TypeScript
- Vue Router
- Pinia
- Axios
- Element Plus
- Vitest
- Vue Test Utils

- [ ] **Step 3: 实现基础布局**

页面结构参考截图：
- 顶部导航。
- 左侧菜单。
- 主内容区域。
- 用户信息和退出入口。

完成标准：
- 登录测试通过。
- 本地前端可启动。
- `docs/front-end-login.md` 记录前端启动命令、登录流程、测试命令和测试结果。
- 完成单独 `git commit` 和 `git push`。

## 14. Stage 9: 模块通过率与失败用例页面

**Files:**
- Create: `front-end/src/api/testRuns.ts`
- Create: `front-end/src/views/ModulePassRateView.vue`
- Create: `front-end/src/components/FailureCasesDialog.vue`
- Create: `front-end/src/components/ModuleRunTable.vue`
- Create: `front-end/src/components/RunFilters.vue`
- Create: `front-end/tests/module-pass-rate.spec.ts`
- Create: `front-end/tests/failure-cases-dialog.spec.ts`
- Create: `docs/module-pass-rate-and-failures.md`

- [ ] **Step 1: 写模块列表测试**

测试目标：
- 展示日期、用例包名、模块名、负责人、自动化负责人、通过率、运行时间、操作。
- 通过率低于 100% 时显示失败重试入口。
- 点击模块重试调用后端 `retry-module` API。
- 点击更多菜单可看到 Jenkins 任务和报告入口。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\front-end
npm test -- module-pass-rate.spec.ts
```

- [ ] **Step 2: 写失败用例弹窗测试**

测试目标：
- 弹窗展示失败用例列表。
- 支持筛选用例名、错误类型、执行状态。
- 支持选择一个或多个失败用例。
- 点击失败重试调用 `retry-selected` API。
- 点击一键失败重试调用 `retry-all-failed` API。
- 点击 Allure 报告入口打开报告 URL。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\front-end
npm test -- failure-cases-dialog.spec.ts
```

- [ ] **Step 3: 实现页面**

设计约束：
- 不做营销页，默认进入可操作测试平台。
- 表格、筛选、弹窗和按钮风格贴近参考截图。
- 保持通用平台字段，不引入公司业务模块常量。

完成标准：
- 前端测试通过。
- 页面可完成模块查看、失败用例查看、选择重试、打开报告。
- `docs/module-pass-rate-and-failures.md` 记录页面功能、接口依赖、测试命令和测试结果。
- 完成单独 `git commit` 和 `git push`。

## 15. Stage 10: 报告展示、联调、文档和交付

**Files:**
- Modify: `back-end/apps/test_runs/views.py`
- Modify: `back-end/config/urls.py`
- Modify: `front-end/src/api/testRuns.ts`
- Modify: `front-end/src/views/ModulePassRateView.vue`
- Create: `front-end/src/views/ReportRedirectView.vue`
- Create: `docs/test-platform-runbook.md`
- Create: `docs/final-integration-report.md`
- Modify: `README.md`

- [ ] **Step 1: 写报告 URL API 测试**

测试目标：
- 测试任务有报告路径时，返回可访问报告 URL。
- 报告不存在时返回明确错误。
- 不暴露服务器任意文件路径。

运行：

```powershell
cd D:\AI\AiApiTest-DWP\back-end
python -m pytest tests/test_test_runs_api.py -v
```

- [ ] **Step 2: 实现报告访问**

第一版能力：
- 后端返回报告入口 URL。
- 前端点击后新窗口打开 Allure HTML。
- Jenkins build 也记录报告入口。

- [ ] **Step 3: 全链路验收**

命令：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python runpytest.py --case-path test_case/test_gbif_case --clean

cd D:\AI\AiApiTest-DWP\back-end
python -m pytest

cd D:\AI\AiApiTest-DWP\front-end
npm test
```

Jenkins 验收：
- Jenkins job 触发测试。
- 失败用例写入 summary。
- Allure 报告可打开。
- 后端可查询 Jenkins build。
- 前端可展示任务和失败用例。

- [ ] **Step 1: 补齐运行文档**

文档内容：
- 如何运行 `api-test`。
- 如何配置 Jenkins。
- 如何启动 DRF 后端。
- 如何启动 Vue 前端。
- 如何查看 Allure 报告。
- 如何执行失败重试。

- [ ] **Step 4: 最终验证**

运行：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests -v

cd D:\AI\AiApiTest-DWP\back-end
python -m pytest

cd D:\AI\AiApiTest-DWP\front-end
npm test
```

- [ ] **Step 5: 更新计划最终状态**

本文件记录：
- 每个阶段完成时间。
- 测试命令。
- 测试结果。
- 遗留问题。
- 下一阶段建议。
- 完成单独 `git commit` 和 `git push`。

## 16. 阶段进度记录

| 日期 | 阶段 | 状态 | 执行内容 | 测试结果 | Git 状态 | 备注 |
|------|------|------|----------|----------|----------|------|
| 2026-06-22 | Stage 1 | in_progress | 创建开发计划，记录用户架构、技术选型、10 阶段流程、TDD 和提交推送要求 | 未运行测试，当前为需求/计划阶段 | 未提交 | 等待用户确认进入 Stage 2 |
| 2026-06-22 | Stage 1 | in_progress | 更新 `AGENTS.md` 和 `README.md`，将旧接口自动化框架说明对齐为 CICD AI 自动化测试平台说明，并补充后续 AI 接手规则 | 文档更新，未运行自动化测试 | 未提交 | 本次只更新核心文档和上下文记录，不进入新阶段实现 |
| 2026-06-22 | Stage 2 | complete | 迁移接口测试框架到 `api-test/`，新增迁移路径测试，修复 `runpytest.py` 默认入口和忽略规则 | RED: 5 failed；GREEN: 5 passed；回归: 14 passed, 1 skipped，Allure 报告生成成功 | committed and pushed: `60a0711` | Stage 2 完成 |
| 2026-06-23 | Stage 2 bugfix | complete | 修复 PyCharm 手动运行单测仍引用旧 `test_case` 工作目录的问题，并适配 `api-test/page_api` 结构 | RED: 2 failed；GREEN: 2 passed；迁移测试: 5 passed；等效单测: 1 passed | committed and pushed: `be60899` | 用户已确认 PyCharm 手动测试无问题 |
| 2026-06-23 | Stage 3 | complete | 新增 pytest node id 读取工具和 CI 重试执行器，支持模块运行、选择 node id、一键失败重试、summary 和运行产物输出 | RED: `tools` 不存在、旧 lastfailed 污染、负数 retry_count；GREEN: 13 passed；回归: 20 passed；烟测: exit code 0 | committed and pushed | Stage 3 完成，具体提交记录见 git 历史 |
| 2026-06-23 | Stage 4 | complete | 新增 Jenkins 参数兼容适配、Jenkinsfile、Groovy Pipeline、静态验证测试和 Jenkins 文档 | RED: 2 failed/3 failed/1 failed；GREEN: ci_runner 10 passed，Jenkins 静态 4 passed，api-test 回归 22 passed，Jenkins env 烟测 exit code 0 | committed and pushed: `e38e415` | 本地未连接真实 Jenkins，已记录验证限制 |
| 2026-06-23 | Stage 5 | complete | 新增 DRF 后端基础工程、Token 登录/登出/me API、自定义用户角色和权限入口；补强数据库配置为强制 MySQL `localhost:3306` | RED: settings 未配置；补强 RED: createsuperuser 默认 member；数据库配置 RED: pytest 下仍为 SQLite；GREEN: database settings 1 passed，accounts 6 passed，Django check 通过 | committed and pushed: `05ad778` | 首次 `git push` 曾失败，后续已重新推送成功 |
| 2026-06-23 | Stage 6 | complete | 新增 `test_runs` app、测试任务/失败用例模型、Allure 失败解析、runner 适配和测试任务/失败重试/报告入口 API | RED: `apps.test_runs` 不存在；GREEN: Stage 6 9 passed，Django check 通过，后端回归 19 passed | committed and pushed: `37eba96` | MySQL 长 node id 唯一索引过长，已移除该约束 |
| 2026-06-23 | Stage 7 | complete | 新增 Jenkins client、Jenkins 查询/触发 API、Pipeline 参数转换和触发记录模型 | RED: `apps.jenkins_integration` 不存在；GREEN: Stage 7 12 passed，Django check 通过，迁移检查通过，后端回归 31 passed | committed and pushed: `8d9c9e4` | 测试使用 fake HTTP/monkeypatch，不依赖真实 Jenkins |

## 17. 风险与处理策略

| 风险 | 影响 | 处理策略 |
|------|------|----------|
| 现有 `runpytest.py` 入口固定执行 demo 模块 | 迁移后默认行为不符合平台调用 | Stage 2 先写测试，再调整为 `main()` 默认入口 |
| Allure CLI 可能未安装 | 报告 HTML 无法生成 | 保留 pytest 执行结果，明确提示；Jenkins 文档写安装要求 |
| Jenkins 环境路径和本机路径不同 | Groovy 调用失败 | Groovy 使用 Jenkins workspace 相对路径，不写死 `D:\AI\...` |
| 失败用例 node id 解析不稳定 | 重试无法精确选择用例 | 使用 pytest cache 和 Allure result 双来源校验 |
| 前后端一次性范围过大 | 交付周期长 | 先 Jenkins，再后端 API，再前端页面，每阶段独立验收 |
| 用户权限当前一致但后续要区分 | 返工权限模型 | 第一版就建立角色字段和权限类入口 |
| 本地 MySQL 环境未准备 | 后端阶段测试无法连接数据库 | Stage 5 前确认数据库名、用户、密码通过环境变量配置，不写入仓库；主机端口固定为 `localhost:3306` |
| 每阶段必须 push | 远程仓库或凭据异常会阻塞阶段完成 | 阶段末单独记录 push 命令和结果，失败时记录原因并等待处理 |

## 18. 当前不纳入第一版的能力

| 能力 | 原因 |
|------|------|
| 多项目/多租户 | 当前需求强调通用框架，但未要求项目空间 |
| 复杂角色权限矩阵 | 当前仅要求管理员和普通用户预留空间 |
| Allure 趋势深度解析 | 第一版先能打开报告和展示失败用例 |
| 测试账号替换的真实业务逻辑 | 项目不能绑定具体业务账号和 token |
| 环境比对、作废、近 7 天/近 30 天统计 | 属于参考截图扩展功能，第一版先实现核心闭环 |
