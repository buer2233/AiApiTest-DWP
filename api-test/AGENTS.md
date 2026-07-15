# api-test/AGENTS.md

本目录是接口自动化执行核心。进入 `api-test/` 工作前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- `api-test/` 是 pytest 用例、接口方法、失败 node id、重试执行器和 Allure 原始结果的唯一实现位置。
- Jenkins 只负责调度本目录的统一执行器；DRF 后端只读取 Jenkins 状态和执行产物，不直接拼 pytest 命令。
- 本目录不实现 Jenkins Groovy 编排、DRF API、Vue 页面、数据库模型或平台权限逻辑。

## 固定 loop 中的位置

- 当需求涉及测试执行协议、pytest 参数、失败重试、模块重试、Allure 产物、summary 输出或用例组织方式时，必须先确认对应需求文档、功能测试用例和必要的 UI/API 契约已经存在。
- 修改执行器或工具代码时，必须先在 `tests/` 编写 pytest 测试，再实现，再回归。
- 新增业务自动化用例前，应能追溯到 `project-info/demand/` 的需求和 `project-info/test_case/` 的测试设计，不允许脱离 loop 直接堆用例。

## 目录约定

- 接口方法放在 `page_api/`。
- pytest 用例放在 `test_case/test_*_case/`，平台按该目录区分模块。
- `tools/` 放可复用执行工具，例如 `pytest_nodeids.py` 和 `ci_runner.py`。
- `tests/` 放 `api-test` 自身单元测试和执行器契约测试。
- `runtime/`、`report/`、`logs/` 是运行产物目录，不作为业务代码提交。
- `test_data/` 只放通用、脱敏、可复用的测试数据。

## 执行协议

- 使用 pytest、requests、allure-pytest、pytest-rerunfailures。
- 失败重试以 pytest node id 为核心数据结构，不能改写 pytest 原始 node id 字符串。
- `tools/ci_runner.py` 必须使用相对 `api-test/` 的路径，不写死本机绝对路径。
- Allure 原始结果写入 `report/allure-results/` 或 `runtime/ci-runs/<run_id>/allure-results/`。
- Allure HTML 报告写入 `report/allure-report/` 或 `runtime/ci-runs/<run_id>/allure-report/`。
- Jenkins 和 DRF 依赖的执行摘要必须稳定输出到 `runtime/ci-runs/<run_id>/`，至少包含模块、总数、通过数、失败数、错误数、跳过数、失败 node id、报告路径和执行状态。

## 常用命令

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
- 修改失败重试、summary、Allure 归档或 node id 逻辑时，必须覆盖正常执行、失败执行、重试成功、重试仍失败、空失败列表和路径不存在等场景。
- `api-test` 自身回归命令：

```powershell
python -m pytest tests -v
```

## 安全和禁止事项

- 不在用例或配置中提交真实账号、密码、token、cookie、租户密钥、生产 URL 或敏感地址。
- 不把重试逻辑复制到 Jenkins Groovy、DRF 后端或 Vue 前端。
- 不提交 `runtime/`、`report/allure-results/`、`report/allure-report/`、`logs/`、`.pytest_cache/`、`__pycache__/` 等产物。

## 平台环境唯一入口（强制）

- 平台应用环境重启、依赖检查/安装、`backend`/`frontend`/`jenkins-sync-worker` 启动、停止或重建，以及平台冒烟/全量环境验收，AI 必须且只能触发固定 Jenkins 环境 Job。
- 固定环境 Job 由本地 Compose Jenkins 启动时通过版本化 init Groovy 幂等创建或修复；主人启动 MySQL/Jenkins bootstrap 后只需在 Jenkins 页面点击构建，不得手工创建另一条旁路 Job。
- Windows 唯一入口为 `scripts/trigger-platform-bootstrap.ps1`；Linux/macOS/Git Bash 唯一入口为 `scripts/trigger-platform-bootstrap.sh`。用户在 Jenkins 页面手工点击同一 Job 也使用相同 Pipeline、参数、阶段和结果契约。
- AI 禁止直接执行应用服务 `docker compose up/restart/stop/down`、`docker build`、宿主机或运行容器的 `pip install`、`npm install/npm ci`，也禁止直接启动 Django `runserver`、Vite 或同步 worker 替代环境 Job。
- MySQL 与 Jenkins 仅由主人/平台运维按 `docker/DEPLOYMENT.md` 完成 bootstrap；环境 Job/helper 永不管理这两个基础服务。AI 只能检查并反馈，不能代替主人/平台运维启动。
- 禁止 `down -v`、volume 删除、`chmod 666 /var/run/docker.sock`、migration、初始化管理员、`collectstatic`、自动 rollback 或输出真实凭据。环境失败必须阅读 Jenkins 结构化诊断，引导主人修复后重新构建，不能旁路处理。
