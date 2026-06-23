# Progress Log

## Session: 2026-06-22

### Phase 1: Requirements Brainstorming
- **Status:** in_progress
- **Started:** 2026-06-22 16:22:04 +08:00
- Actions taken:
  - 读取 `using-superpowers` 技能说明。
  - 读取 `planning-with-files` 技能说明。
  - 读取 `api-design` 技能说明，用于后续平台 API 合约设计。
  - 读取 `test-driven-development` 技能说明，确认实现阶段必须先写失败测试。
  - 确认根目录没有 `.codegraph/`。
  - 查看项目根目录文件列表，初步确认已有接口自动化框架结构。
  - 将规划文件切换到本轮 CICD + 网页端测试平台需求设计任务。
  - 查看用户提供的两张测试平台截图，提炼模块通过率页和失败用例弹窗的关键交互。
  - 收到用户明确架构：`front-end/` 使用 Vue 3，`back-end/` 使用 DRF，`api-test/` 承载迁移后的接口测试框架，`jenkins/` 承载 Groovy/Jenkins 能力。
  - 创建开发计划文档 `docs/superpowers/plans/2026-06-22-cicd-test-platform.md`，记录 10 个阶段、每阶段 TDD 流程、验收命令、风险和当前进度。
  - 根据用户确认的开发流程更新计划：每阶段单独需求分析、编写测试用例、开发、测试、`git commit`、`git push`。
  - 将后端数据库默认方案从 SQLite 调整为本地 MySQL。
  - 确认 DRF Token、Element Plus、Jenkins Windows/Linux 兼容、Allure 静态 HTML 报告、所有开发测试文档归档到 `docs/`。
  - 2026-06-22 17:54:17 +08:00：根据用户要求更新 `AGENTS.md` 和 `README.md`，将旧的 AI 接口自动化框架描述改为 CICD AI 自动化测试平台描述。
  - 2026-06-22 17:54:17 +08:00：在 `AGENTS.md` 中补充后续 AI 必读主计划和上下文文件、四大工程目录职责、阶段 TDD、敏感信息限制和文档记录规则。
  - 2026-06-22 17:54:17 +08:00：在 `README.md` 中补充当前平台目标、仓库结构、10 阶段开发计划、`api-test` 快速运行方式和 AI 接手流程。
  - 2026-06-22 17:54:17 +08:00：检查 `git status --short`，发现 `api-test/` 等迁移改动已存在于工作区但未提交；本次没有回滚或覆盖这些既有改动。
  - 2026-06-22 17:54:19 +08:00：开始 Stage 2，创建 `docs/api-test-migration.md` 和 `api-test/tests/test_runpytest_commands.py`。
  - 2026-06-22 17:54:19 +08:00：运行迁移验证测试确认 RED，结果 5 failed，失败原因是框架文件尚未迁移到 `api-test/`。
  - 2026-06-22 17:54:19 +08:00：将 `report/`、`test_case/`、`test_data/`、`utils/`、`config.py`、`conftest.py`、`pytest.ini`、`requirements.txt`、`runpytest.py` 移动到 `api-test/`。
  - 2026-06-22 17:54:19 +08:00：修复 `api-test/runpytest.py` 默认入口为 `main()`。
  - 2026-06-22 17:54:19 +08:00：更新 `.gitignore`，忽略 `api-test` 下的报告、运行时和日志产物。
  - 2026-06-22 17:54:19 +08:00：运行迁移验证测试确认 GREEN，结果 5 passed。
  - 2026-06-22 17:54:19 +08:00：运行 demo 回归 `python runpytest.py --case-path test_case/test_gbif_case --clean`，结果 14 passed, 1 skipped，并生成 Allure HTML 报告。
  - 2026-06-22 17:54:19 +08:00：完成 Stage 2 提交 `60a0711`，提交信息 `stage2: migrate api test framework`。
  - 2026-06-22 17:54:19 +08:00：执行 `git push origin main` 成功，远程 `main` 更新到 `60a0711`。
  - 2026-06-23 09:14:44 +08:00：处理迁移后 PyCharm 手动运行单测报错，定位到 `.idea/workspace.xml` 仍引用旧工作目录 `$PROJECT_DIR$/test_case/test_gbif_case`。
  - 2026-06-23 09:14:44 +08:00：新增 `api-test/tests/test_pycharm_migration_config.py`，先运行确认 RED：2 failed。
  - 2026-06-23 09:14:44 +08:00：修复 PyCharm 测试配置和 runpytest 配置到 `api-test` 路径，并保留用户已移动的 `api-test/page_api` 结构。
  - 2026-06-23 09:14:44 +08:00：运行 PyCharm 配置测试确认 GREEN：2 passed。
  - 2026-06-23 09:14:44 +08:00：运行迁移路径测试：5 passed。
  - 2026-06-23 09:14:44 +08:00：等效 PyCharm 手动执行单个测试：`cd api-test/test_case/test_gbif_case; python -m pytest test_gbif_api.py::TestGbifAPI::test_species_search_by_keyword -q`，结果 1 passed。
  - 2026-06-23：用户确认 PyCharm 手动执行测试无问题，进入 Stage 3。
  - 2026-06-23：创建 `docs/pytest-nodeid-retry-runner.md`，记录 Stage 3 范围、输入、输出、重试模式和验收标准。
  - 2026-06-23：创建 `api-test/tests/test_pytest_nodeids.py` 和 `api-test/tests/test_ci_runner.py`，先运行确认 RED，失败原因均为 `ModuleNotFoundError: No module named 'tools'`。
  - 2026-06-23：创建 `api-test/tools/__init__.py`、`api-test/tools/pytest_nodeids.py`、`api-test/tools/ci_runner.py`，实现 node id 读取、CI 执行、产物写出和 summary。
  - 2026-06-23：运行 Stage 3 测试确认初始 GREEN：`tests/test_pytest_nodeids.py` 5 passed，`tests/test_ci_runner.py` 6 passed。
  - 2026-06-23：真实执行器烟测：`python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id stage3-smoke --clean`，exit code 0，Allure HTML 报告生成到 `api-test/runtime/ci-runs/stage3-smoke/allure-report`。
  - 2026-06-23：发现旧 `.pytest_cache/v/cache/lastfailed` 可能污染本次运行 summary，补充失败测试后修复为执行前清理旧 cache。
  - 2026-06-23：补充 `retry_count=-1` 边界失败测试，修复为命令构造和 CLI 入口均拒绝负数。
  - 2026-06-23：运行 Stage 3 精确测试：`python -m pytest tests/test_pytest_nodeids.py tests/test_ci_runner.py -v`，结果 13 passed。
  - 2026-06-23：运行 `api-test` 回归测试：`python -m pytest tests -v`，结果 20 passed。
  - 2026-06-23：提交前最终烟测：`python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id stage3-final --clean`，exit code 0，Allure HTML 报告生成成功。
  - 2026-06-23：Stage 3 已完成提交和推送，具体 commit hash 见 git 历史。
  - 2026-06-23：按用户要求整理根目录与四个核心子目录的 Markdown 规则文件：根 `AGENTS.md` 保留全局规则；`api-test/`、`back-end/`、`front-end/`、`jenkins/` 均补齐 `README.md`、`AGENTS.md`、`CLAUDE.md`；所有 `CLAUDE.md` 仅引用同级 `AGENTS.md`。
  - 2026-06-23：文档整理后运行 `cd api-test; python -m pytest tests -v`，结果 20 passed。
  - 2026-06-23：开始 Stage 4，读取根目录和 `api-test/`、`jenkins/` 协作规则，确认根目录没有 `.codegraph/`，工作区初始干净。
  - 2026-06-23：新增 `api-test/tests/test_ci_runner.py` Jenkins 参数兼容测试，覆盖 `CASE_PATH`、换行/逗号分隔的 `PYTEST_NODE_IDS`、`RETRY_MODE=all-failed`、`RETRY_COUNT=1`。
  - 2026-06-23：新增 `jenkins/tests/test_pipeline_static.py`，覆盖 Jenkins 参数、必需 stages、`isUnix()`、`sh`/`bat`、调用 `python -m tools.ci_runner`、归档和 Allure 发布。
  - 2026-06-23：运行 Stage 4 初始 RED：`cd api-test; python -m pytest tests/test_ci_runner.py -v`，结果 2 failed, 8 passed，失败原因是 Jenkins env 适配函数不存在。
  - 2026-06-23：运行 Stage 4 初始 RED：`cd jenkins; python -m pytest tests/test_pipeline_static.py -v`，结果 3 failed，失败原因是 `Jenkinsfile` 不存在。
  - 2026-06-23：实现 `parse_jenkins_node_ids()`、`build_run_request_from_jenkins_env()` 和 `--from-jenkins-env`。
  - 2026-06-23：创建 `jenkins/Jenkinsfile` 和 `jenkins/scripts/api-test-pipeline.groovy`，定义参数、Checkout/Prepare Python/Install/Run/Generate/Archive/Publish stages，并用 `isUnix()` 分支兼容 `sh`/`bat`。
  - 2026-06-23：运行 `cd api-test; python -m pytest tests/test_ci_runner.py -v`，结果 10 passed。
  - 2026-06-23：运行 `cd jenkins; python -m pytest tests/test_pipeline_static.py -v`，结果 3 passed。
  - 2026-06-23：发现 pytest 失败时 Jenkins 会中断后续归档，新增补强 RED：`cd jenkins; python -m pytest tests/test_pipeline_static.py::test_pipeline_preserves_artifacts_when_pytest_fails -v`，结果 1 failed。
  - 2026-06-23：将 `Run API Tests` 包裹在 `catchError(buildResult: 'FAILURE', stageResult: 'FAILURE')` 中，确保失败后继续归档产物和发布 Allure。
  - 2026-06-23：运行 `cd jenkins; python -m pytest tests/test_pipeline_static.py -v`，结果 4 passed。
  - 2026-06-23：创建 `docs/jenkins-pipeline.md`，记录 Jenkins 参数、脚本说明、测试命令、验证结果和本地未接入真实 Jenkins 的限制。
  - 2026-06-23：运行最终回归：`cd api-test; python -m pytest tests -v`，结果 22 passed；`cd jenkins; python -m pytest tests -v`，结果 4 passed。
  - 2026-06-23：运行 Jenkins 环境变量模式烟测：`cd api-test; python -m tools.ci_runner --from-jenkins-env`，环境变量 `CASE_PATH=test_case/test_gbif_case`、`RETRY_MODE=module`、`RUN_ID=stage4-jenkins-env-smoke`，结果 exit code 0，Allure HTML 生成成功。
  - 2026-06-23：开始 Stage 5，读取根目录与 `back-end/AGENTS.md`，确认根目录没有 `.codegraph/`，工作区初始仅有用户侧 `AGENTS.md` 非本阶段改动。
  - 2026-06-23：创建 `back-end/tests/test_accounts_api.py`，覆盖登录 token、登出、当前用户、`admin`/`member` 角色保存、当前平台权限一致和管理员专属权限入口。
  - 2026-06-23：运行 Stage 5 初始 RED：`cd back-end; python -m pytest tests/test_accounts_api.py -v`，结果 1 error，失败原因是 Django settings 未配置。
  - 2026-06-23：创建 DRF 后端基础工程：`manage.py`、`config/`、`apps/accounts/`、`requirements.txt`、`pytest.ini` 和 accounts 迁移。
  - 2026-06-23：运行账户测试时发现 `--reuse-db` 无法识别，原因是当前环境缺少 `pytest-django`；执行 `cd back-end; python -m pip install -r requirements.txt` 成功，pip 提示全局 `django-celery-beat` 依赖旧 Django。
  - 2026-06-23：运行 Stage 5 初始 GREEN：`cd back-end; python -m pytest tests/test_accounts_api.py -v`，结果 5 passed。
  - 2026-06-23：补充 `create_superuser()` 默认管理员角色测试，先运行确认 RED：1 failed，默认 role 为 `member`。
  - 2026-06-23：新增 `UserManager.create_superuser()` 默认 `role=admin`，并补充 `0002_alter_user_managers.py` 迁移。
  - 2026-06-23：运行补强测试确认 GREEN：`cd back-end; python -m pytest tests/test_accounts_api.py::test_create_superuser_defaults_to_admin_role -v`，结果 1 passed。
  - 2026-06-23：运行 Stage 5 精确测试：`cd back-end; python -m pytest tests/test_accounts_api.py -v`，结果 6 passed。
  - 2026-06-23：运行配置检查：`cd back-end; python manage.py check`，结果 System check identified no issues。
  - 2026-06-23：创建 `docs/back-end-accounts.md`，记录本地 MySQL 配置、迁移命令、测试命令、测试结果和已知问题。
  - 2026-06-23：根据用户要求补强 Stage 5 数据库配置，新增 `back-end/tests/test_database_settings.py`，先运行 RED，确认 pytest 下仍回退 SQLite。
  - 2026-06-23：删除 `back-end/config/settings.py` 中的 pytest SQLite 分支，强制所有环境使用 MySQL，连接固定为 `localhost:3306`。
  - 2026-06-23：运行数据库配置测试确认 GREEN：`cd back-end; python -m pytest tests/test_database_settings.py -v`，结果 1 passed。
  - 2026-06-23：在强制 MySQL 配置下运行账户 API 测试：`cd back-end; python -m pytest tests/test_accounts_api.py -v`，结果 6 passed。
  - 2026-06-23：提交 Stage 5 数据库配置补强：`2a00252 stage5: force backend mysql connection`。
  - 2026-06-23：首次执行 `git push` 失败，错误为 `fatal: unable to access 'https://github.com/buer2233/AiApiTest-DWP.git/': Empty reply from server`。
  - 2026-06-23：后续重新推送成功，当前 `main` 已与 `origin/main` 同步，最新远端提交为 `05ad778`。
  - 2026-06-23：开始 Stage 6：测试任务与失败用例 API。按 TDD 先编写 `test_runs` API 和 Allure 解析失败测试。
  - 2026-06-23：新增 `back-end/tests/test_allure_results_parser.py` 和 `back-end/tests/test_test_runs_api.py`。
  - 2026-06-23：运行 Stage 6 初始 RED：`cd back-end; python -m pytest tests/test_allure_results_parser.py -v`，结果 1 error，失败原因是 `apps.test_runs` 不存在。
  - 2026-06-23：运行 Stage 6 初始 RED：`cd back-end; python -m pytest tests/test_test_runs_api.py -v`，结果 1 error，失败原因是 `apps.test_runs` 不存在。
  - 2026-06-23：创建 `apps/test_runs` app，新增 `TestRun`、`FailureCase` 模型、首个迁移、Allure 解析服务、`ApiTestRunner` 适配器、serializers、views 和 urls。
  - 2026-06-23：将 `apps.test_runs` 加入后端 `INSTALLED_APPS`，并挂载 `/api/test-runs/` 路由。
  - 2026-06-23：首次运行 Stage 6 API 测试遇到 MySQL 长索引错误：`Specified key was too long`，移除 `(test_run, node_id)` 唯一约束。
  - 2026-06-23：因首次失败迁移污染复用测试库，运行 `python -m pytest tests/test_test_runs_api.py -v --create-db` 重建测试库，随后只剩列表响应结构缺口。
  - 2026-06-23：补充 `TestRunViewSet.list()` 返回 `count/results`，并设置模型 `__test__ = False` 避免 pytest 误收集 Django 模型类。
  - 2026-06-23：运行 Stage 6 API 测试确认 GREEN：`cd back-end; python -m pytest tests/test_test_runs_api.py -v`，结果 7 passed。
  - 2026-06-23：运行 Stage 6 精确测试：`cd back-end; python -m pytest tests/test_allure_results_parser.py tests/test_test_runs_api.py -v`，结果 9 passed。
  - 2026-06-23：运行 `cd back-end; python manage.py check`，结果 System check identified no issues。
  - 2026-06-23：运行后端回归：`cd back-end; python -m pytest -v`，结果 19 passed。
  - 2026-06-23：创建 `docs/test-runs-api.md`，记录 Stage 6 范围、模型、接口、Allure 解析、测试命令和问题处理。
- Files created/modified:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
  - `docs/superpowers/plans/2026-06-22-cicd-test-platform.md`
  - `AGENTS.md`
  - `README.md`
  - `.gitignore`
  - `docs/api-test-migration.md`
  - `api-test/`
  - `.idea/workspace.xml`

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| N/A | 需求设计阶段 | 不运行测试 | 未运行 | N/A |
| 文档对齐 | 更新 `AGENTS.md`、`README.md` 和计划记录 | 不需要运行自动化测试 | 未运行，仅做文档更新 | N/A |
| Stage 2 RED | `cd api-test; python -m pytest tests/test_runpytest_commands.py -v` | 迁移前失败 | 5 failed | passed |
| Stage 2 GREEN | `cd api-test; python -m pytest tests/test_runpytest_commands.py -v` | 迁移后通过 | 5 passed | passed |
| Stage 2 回归 | `cd api-test; python runpytest.py --case-path test_case/test_gbif_case --clean` | demo 可执行并生成报告 | 14 passed, 1 skipped；Allure HTML 已生成 | passed |
| PyCharm 配置 RED | `cd api-test; python -m pytest tests/test_pycharm_migration_config.py -v` | 旧路径配置被测试捕获 | 2 failed | passed |
| PyCharm 配置 GREEN | `cd api-test; python -m pytest tests/test_pycharm_migration_config.py -v` | 旧路径清除 | 2 passed | passed |
| PyCharm 等效单测 | `cd api-test/test_case/test_gbif_case; python -m pytest test_gbif_api.py::TestGbifAPI::test_species_search_by_keyword -q` | 单测可执行 | 1 passed | passed |
| Stage 3 node id RED | `cd api-test; python -m pytest tests/test_pytest_nodeids.py -v` | `tools` 包不存在导致失败 | 1 error: `ModuleNotFoundError` | passed |
| Stage 3 CI runner RED | `cd api-test; python -m pytest tests/test_ci_runner.py -v` | `tools` 包不存在导致失败 | 1 error: `ModuleNotFoundError` | passed |
| Stage 3 stale cache RED | `cd api-test; python -m pytest tests/test_ci_runner.py -v` | 旧 `lastfailed` 污染被捕获 | 1 failed, 6 passed | passed |
| Stage 3 retry_count RED | `cd api-test; python -m pytest tests/test_ci_runner.py::test_build_pytest_command_rejects_negative_rerun_count -v` | 负数重试次数被测试捕获 | 1 failed | passed |
| Stage 3 GREEN | `cd api-test; python -m pytest tests/test_pytest_nodeids.py tests/test_ci_runner.py -v` | Stage 3 功能测试通过 | 13 passed | passed |
| Stage 3 回归 | `cd api-test; python -m pytest tests -v` | api-test 自身测试全部通过 | 20 passed | passed |
| Stage 3 真实烟测 | `cd api-test; python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id stage3-smoke --clean` | 执行器可真实运行模块并输出 summary | exit code 0；summary passed；failed_nodeids [] | passed |
| Stage 3 最终烟测 | `cd api-test; python -m tools.ci_runner --case-path test_case/test_gbif_case --retry-mode module --run-id stage3-final --clean` | 最终实现可真实运行模块并生成 Allure HTML | exit code 0；Allure HTML 生成成功 | passed |
| Markdown 规则文件整理回归 | `cd api-test; python -m pytest tests -v` | 文档新增不影响 api-test 测试发现 | 20 passed | passed |
| Stage 4 ci_runner RED | `cd api-test; python -m pytest tests/test_ci_runner.py -v` | Jenkins env 适配缺失被测试捕获 | 2 failed, 8 passed | passed |
| Stage 4 Jenkins 静态 RED | `cd jenkins; python -m pytest tests/test_pipeline_static.py -v` | Jenkins Pipeline 文件缺失被测试捕获 | 3 failed | passed |
| Stage 4 artifact RED | `cd jenkins; python -m pytest tests/test_pipeline_static.py::test_pipeline_preserves_artifacts_when_pytest_fails -v` | pytest 失败阻断归档被测试捕获 | 1 failed | passed |
| Stage 4 ci_runner GREEN | `cd api-test; python -m pytest tests/test_ci_runner.py -v` | Jenkins 参数兼容测试通过 | 10 passed | passed |
| Stage 4 Jenkins 静态 GREEN | `cd jenkins; python -m pytest tests/test_pipeline_static.py -v` | Jenkins 参数、stages、跨平台分支、归档发布检查通过 | 4 passed | passed |
| Stage 4 api-test 回归 | `cd api-test; python -m pytest tests -v` | api-test 自身测试全部通过 | 22 passed | passed |
| Stage 4 Jenkins 回归 | `cd jenkins; python -m pytest tests -v` | Jenkins 静态测试全部通过 | 4 passed | passed |
| Stage 4 Jenkins env 烟测 | `cd api-test; python -m tools.ci_runner --from-jenkins-env` | Jenkins 环境变量入口可真实执行模块 | exit code 0；Allure HTML 生成成功 | passed |
| Stage 5 初始 RED | `cd back-end; python -m pytest tests/test_accounts_api.py -v` | Django 工程缺失导致失败 | 1 error: settings 未配置 | passed |
| Stage 5 环境依赖安装 | `cd back-end; python -m pip install -r requirements.txt` | 补齐后端测试依赖 | 安装成功；提示全局 `django-celery-beat` 依赖旧 Django | passed |
| Stage 5 初始 GREEN | `cd back-end; python -m pytest tests/test_accounts_api.py -v` | 账户 API 测试通过 | 5 passed | passed |
| Stage 5 createsuperuser RED | `cd back-end; python -m pytest tests/test_accounts_api.py::test_create_superuser_defaults_to_admin_role -v` | 捕获超级管理员默认角色错误 | 1 failed: `member != admin` | passed |
| Stage 5 GREEN | `cd back-end; python -m pytest tests/test_accounts_api.py -v` | 登录、角色、权限测试通过 | 6 passed | passed |
| Stage 5 Django check | `cd back-end; python manage.py check` | Django 配置无系统检查问题 | System check identified no issues | passed |
| Stage 5 database settings RED | `cd back-end; python -m pytest tests/test_database_settings.py -v` | 捕获 pytest 下 SQLite 回退 | 1 failed: sqlite3 != mysql | passed |
| Stage 5 database settings GREEN | `cd back-end; python -m pytest tests/test_database_settings.py -v` | 强制 MySQL localhost:3306 配置通过 | 1 passed | passed |
| Stage 5 accounts under forced MySQL | `cd back-end; python -m pytest tests/test_accounts_api.py -v` | 账户 API 在强制 MySQL 配置下通过 | 6 passed | passed |
| Stage 6 Allure parser RED | `cd back-end; python -m pytest tests/test_allure_results_parser.py -v` | `apps.test_runs` 缺失导致失败 | 1 error: `ModuleNotFoundError` | passed |
| Stage 6 API RED | `cd back-end; python -m pytest tests/test_test_runs_api.py -v` | `apps.test_runs` 缺失导致失败 | 1 error: `ModuleNotFoundError` | passed |
| Stage 6 MySQL index RED | `cd back-end; python -m pytest tests/test_test_runs_api.py -v` | 捕获长 node id 唯一索引不兼容 MySQL | 7 errors: `Specified key was too long` | passed |
| Stage 6 rebuild test DB | `cd back-end; python -m pytest tests/test_test_runs_api.py -v --create-db` | 清理失败迁移残留并继续验证 | 1 failed, 6 passed | passed |
| Stage 6 API GREEN | `cd back-end; python -m pytest tests/test_test_runs_api.py -v` | 测试任务和失败重试 API 通过 | 7 passed | passed |
| Stage 6 focused GREEN | `cd back-end; python -m pytest tests/test_allure_results_parser.py tests/test_test_runs_api.py -v` | Allure 解析与 API 全部通过 | 9 passed | passed |
| Stage 6 Django check | `cd back-end; python manage.py check` | Django 配置无系统检查问题 | System check identified no issues | passed |
| Stage 6 backend regression | `cd back-end; python -m pytest -v` | 后端回归全部通过 | 19 passed | passed |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| N/A | None | 1 | N/A |
| 2026-06-23 | Stage 3 初始 RED：`ModuleNotFoundError: No module named 'tools'` | 1 | 创建 `api-test/tools` 包和实现文件 |
| 2026-06-23 | Stage 3 补强 RED：旧 `lastfailed` cache 污染当前运行失败列表 | 1 | 在 pytest 执行前清理旧 cache |
| 2026-06-23 | Stage 3 补强 RED：`retry_count=-1` 未被拒绝 | 1 | 增加非负校验 |
| 2026-06-23 | Stage 4 初始 RED：Jenkins env 适配函数不存在 | 1 | 新增 Jenkins env 适配函数和 CLI 开关 |
| 2026-06-23 | Stage 4 初始 RED：Jenkins Pipeline 文件不存在 | 1 | 创建 Jenkinsfile 和 Groovy Pipeline |
| 2026-06-23 | Stage 4 补强 RED：pytest 失败会阻断归档 | 1 | 使用 `catchError` 让归档和 Allure 发布继续执行 |
| 2026-06-23 | Stage 5 初始 RED：Django settings 未配置 | 1 | 创建后端 Django/DRF 工程和 accounts app |
| 2026-06-23 | Stage 5 环境错误：`--reuse-db` 无法识别 | 1 | 安装 `pytest-django` 等 `back-end/requirements.txt` 依赖 |
| 2026-06-23 | Stage 5 补强 RED：超级管理员默认 `member` | 1 | 新增自定义 `UserManager`，使 `create_superuser()` 默认 `admin` |
| 2026-06-23 | Stage 5 MySQL warning：默认库不存在 | 1 | 文档记录 `CREATE DATABASE` |
| 2026-06-23 | Stage 5 数据库配置 RED：pytest 下仍回退 SQLite | 1 | 删除 SQLite 分支，强制 MySQL `localhost:3306` |
| 2026-06-23 | Stage 5 push 失败：`Empty reply from server` | 1 | 后续重新推送成功，`main` 与 `origin/main` 已同步到 `05ad778` |
| 2026-06-23 | Stage 6 初始 RED：`ModuleNotFoundError: No module named 'apps.test_runs'` | 1 | 创建 `apps.test_runs` app、模型、服务、序列化器、视图和 URL |
| 2026-06-23 | Stage 6 MySQL 长索引错误：`Specified key was too long` | 1 | 移除 `(test_run, node_id)` 唯一约束，保留完整 node id 字段 |
| 2026-06-23 | Stage 6 复用测试库残留：`Table 'test_runs_testrun' already exists` | 1 | 使用 `--create-db` 重建 MySQL 测试库 |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Stage 6 complete, ready for commit and push |
| Where am I going? | Stage 7：Jenkins 查询与触发 API |
| What's the goal? | 为现有接口自动化框架设计并实现 CICD 与网页端测试平台能力 |
| What have I learned? | 见 `findings.md` |
| What have I done? | 已完成 Stage 2 迁移、PyCharm 旧路径修复、Stage 3 node id 与 CI 执行器、Stage 4 Jenkins Groovy Pipeline、Stage 5 DRF 后端基础工程与用户角色、Stage 6 测试任务与失败用例 API、RED/GREEN 测试和文档记录 |
