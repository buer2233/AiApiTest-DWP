# AiApiTest-DWP Project Architecture

## 1. 项目定位

`AiApiTest-DWP` 是一个面向 AI 协作和企业级 CICD 的自动化测试平台。项目采用 monorepo 单仓库结构，将接口自动化执行核心、Jenkins 流水线、DRF 后端、Vue 3 前端、Docker 基础设施和项目交接资料统一维护。

平台不绑定具体业务系统。所有测试用例、平台接口、Jenkins 脚本、Docker 配置和前端页面都必须保持可迁移、可复用，不提交真实账号、密码、token、cookie、Jenkins API Token、生产地址或敏感业务常量。

平台当前 Docker 阶段以 MySQL 和 Jenkins 基础依赖为主；后期必须支持将完整测试平台作为一个 Docker Compose 项目整体打包部署。整体部署不是单一巨大镜像，而是用多个职责明确的服务容器编排 DRF、Vue、Jenkins、MySQL、Nginx、`api-test` runner 和报告产物。

## 2. 总体架构原则

- Jenkins 是严格执行主干：平台侧所有测试执行、模块重试、失败重试和报告生成都必须通过 Jenkins。
- `api-test` 是测试执行协议唯一实现位置：pytest 参数、失败 node id、重试模式、Allure 产物和 summary 协议都在该模块演进。
- DRF 后端不直接执行 pytest，不拼接 pytest 命令，不重复实现失败重试算法。
- DRF 后端负责平台编排和数据治理：权限、任务、模块快照、失败用例、Jenkins 状态同步、报告入口和审计。
- Vue 3 前端负责管理后台体验：模块通过率、失败用例、重试操作、Jenkins 任务和报告入口。
- Docker 当前负责基础服务，后期必须支持整个平台 Compose 化部署。
- 后续所有模块设计必须兼容容器网络、环境变量、持久化 volume 和可重建镜像，不能依赖个人本机绝对路径、宿主机固定端口或手工不可复现配置。

## 3. 模块组成

| 模块 | 目录 | 技术栈 | 核心职责 |
| --- | --- | --- | --- |
| 接口自动化执行核心 | `api-test/` | Python、pytest、requests、allure-pytest | 测试用例、接口方法、失败 node id、重试执行器、Allure 原始结果 |
| Jenkins 执行主干 | `jenkins/` | Jenkins、Groovy、Pipeline | 参数化 Job、流水线编排、节点环境、归档、Allure 发布 |
| 后端平台层 | `back-end/` | Python、Django REST Framework、MySQL | 用户权限、任务模型、Jenkins 触发和同步、模块快照、失败用例、报告入口 |
| 前端展示层 | `front-end/` | Vue 3、Vite、TypeScript、Element Plus | 企业级管理后台、筛选表格、弹窗、状态操作、报告入口 |
| 基础设施 | `docker/` | Docker Compose、MySQL、Jenkins、Nginx、应用镜像 | 当前基础依赖服务；后期完整平台 Compose 编排、部署说明和工具链镜像 |
| 项目资料 | `project-info/` | Markdown、draw.io、原型资料 | 需求、测试用例、UI 原型、架构图和交接资料 |

## 4. 核心执行链路

```text
用户
  -> Vue 3 前端
  -> DRF API
  -> Jenkins API
  -> Jenkins 参数化 Job
  -> api-test/tools/ci_runner.py
  -> pytest
  -> Allure 原始结果、summary、失败 node id
  -> Jenkins 归档和报告发布
  -> DRF 同步任务、模块快照、失败用例和报告入口
  -> Vue 3 前端展示
```

整体 Docker 化后，链路不改变，只改变部署边界：

```text
用户
  -> nginx 容器统一入口
  -> frontend 静态资源 / backend API
  -> backend 容器调用 jenkins 容器
  -> Jenkins controller 调度 api-test runner 或 Jenkins agent
  -> runner 执行 api-test/tools/ci_runner.py
  -> 产物写入 Jenkins workspace 或共享 volume
  -> Jenkins 归档并发布 Allure
  -> backend 同步任务和报告入口
```

## 5. Jenkins Job 架构

平台需要多个 Jenkins Job，但必须由统一 Pipeline 模板治理，避免每个模块手写脚本。

建议 Job 类型：

| Job 类型 | 作用 | 说明 |
| --- | --- | --- |
| 每日全量 Job | 每天凌晨 1 点执行全部测试模块 | 刷新当天模块快照和失败用例数据 |
| 模块重试 Job | 重跑单个模块目录 | 更新模块统计、运行日期和执行时间 |
| 失败重试 Job | 只重跑当前模块失败用例 | 更新模块统计，但不更新运行日期和执行时间 |
| 可选 Worker Job | 承接拆分后的模块执行 | 用于并发调度和最多 10 任务限制 |

设计约束：

- 每类重试 Job 独立，模块重试和失败重试不能共用同一个执行入口。
- 每类 Job 同时最多允许 10 个任务执行。
- 同一环境、同一模块同一时间只能存在一个模块重试或失败重试任务。
- Jenkins 直接调用 `api-test/tools/ci_runner.py`，不在 Groovy 中复制 pytest 逻辑。
- 容器化后 Jenkins controller 不应承载大量测试执行负载；推荐使用 `api-runner` 镜像或 Jenkins agent 执行 pytest、Allure 和产物生成。
- Jenkins 的插件、Job 模板、凭据占位符和初始化策略应逐步固化为 JCasC、Job DSL 或初始化脚本，避免整体部署后仍依赖大量手工配置。

## 6. 后端数据职责

DRF 后端负责将 Jenkins 执行结果转化为平台数据。

核心数据域：

| 数据域 | 说明 |
| --- | --- |
| 测试环境 | 环境标识、环境类型、展示名称和基础地址 |
| 测试模块 | 模块标识、pytest 路径、模块名、负责人和排序 |
| 模块展示快照 | 固定模块行，保存当前展示通过率、成功数、失败数、错误数、运行日期和运行时间 |
| 失败用例记录 | 只新增或更新状态，不物理删除，支持失败、跳过、通过、不展示 |
| Jenkins 任务记录 | 所有执行任务只新增，保存 queue、build、Job URL、报告 URL 和状态 |
| 模块执行锁 | 控制同一模块同一时间只能执行一种重试 |

详细字段草案见 `project-info/demand/需求草稿-测试平台架构阶段.md`。

## 7. 前端架构

`front-end/` 使用 Vue 3 企业级管理后台技术栈：

- Vue 3
- Vite
- TypeScript
- Element Plus
- Vue Router
- Pinia
- Axios
- TanStack Query for Vue
- Vitest
- Vue Test Utils
- Playwright

核心页面：

- 登录页和登录态守卫。
- 模块通过率页。
- 失败用例弹窗。
- Jenkins 任务列表。
- 模块重试和失败重试操作。
- Allure 报告入口。

前端只通过 DRF API 获取数据和发起操作，不直接访问服务器文件路径，不绕过后端权限访问 Jenkins 或报告产物。

容器化部署时，前端构建产物由 `frontend` 或 `nginx` 服务承载。前端 API 地址应使用相对路径或部署时注入的环境配置，不能写死本机 IP、宿主机端口或 Jenkins 内网地址。

## 8. 整体 Docker 化部署架构

后期完整平台建议由一个 Docker Compose 项目编排，服务边界如下：

| 服务 | 职责 | 关键依赖 |
| --- | --- | --- |
| `nginx` | 统一入口、静态资源、反向代理 `/api` 和可选报告入口 | `frontend`、`backend`、可选 `jenkins` |
| `frontend` | Vue 3 构建产物或前端静态服务 | 构建阶段依赖 Node，运行阶段不持有业务状态 |
| `backend` | DRF API、权限、任务编排、Jenkins 状态同步 | `mysql`、`jenkins` |
| `mysql` | 平台数据持久化 | volume 保存数据库数据 |
| `jenkins` | Jenkins controller、Job 编排、Allure 发布 | Jenkins home volume、runner/agent |
| `api-runner` 或 Jenkins agent | pytest、Allure、`api-test` 执行环境 | Jenkins 调度，读取仓库代码或构建镜像内代码 |

整体部署原则：

- 容器内部依赖使用 Compose 服务名，例如 `mysql:3306`、`jenkins:8080`、`backend:8000`。
- 宿主机端口只用于外部访问，不作为容器间调用地址。
- MySQL 数据、Jenkins home、报告归档、上传文件和运行日志必须通过 volume 管理。
- 镜像内只放应用代码、静态资源和工具链，不打包 `.env`、数据库数据、Jenkins home 或 Allure HTML 历史报告。
- `api-test` runner 镜像应包含 Python、pytest、requests、allure-pytest、Allure CLI 和执行器依赖。
- Jenkins Credentials、DRF 密钥、数据库密码、API token 等敏感配置只能通过环境变量、私有配置或 Jenkins Credentials 注入。
- 后续新增模块时必须同步评估 Dockerfile、Compose 服务、健康检查、日志输出和可迁移配置。

## 9. 开发流程架构

每个需求必须按固定 loop 推进：

```text
需求分析
  -> 功能测试用例
  -> UI 原型图
  -> 后端接口测试先行
  -> DRF 后端开发
  -> Playwright UI 测试先行
  -> Vue 3 前端开发
  -> 联调验收
```

阶段产物目录：

| 阶段 | 目录 | 产物 |
| --- | --- | --- |
| 需求分析 | `project-info/demand/` | 需求说明书、功能设计、表设计 |
| 功能测试用例 | `project-info/test_case/` | 分模块、分优先级的详细测试用例 |
| UI 原型 | `project-info/UI/` | 原型图和交互说明 |
| 后端开发 | `back-end/` | DRF 代码、pytest 接口测试、迁移 |
| 前端开发 | `front-end/` | Vue 代码、Playwright UI 测试、组件测试 |

Docker 和 Jenkins 属于基础设施设计阶段，不要求每个需求都重复产出；需要调整时按实际工作执行。但每个需求在设计后端接口、前端访问、Jenkins 执行、报告入口或文件路径时，都必须校验是否兼容后期整体 Docker 化部署。

## 10. 报告与产物

`api-test/tools/ci_runner.py` 输出标准运行产物：

```text
api-test/runtime/ci-runs/<run_id>/
├── console.log
├── failed_nodeids.json
├── summary.json
├── allure-results/
└── allure-report/
```

Jenkins 负责归档运行目录和发布 Allure。DRF 后端负责记录报告入口和同步失败用例。前端只展示后端授权后的报告入口。

容器化后，报告产物可以先由 Jenkins workspace 归档，也可以演进为共享 volume 或对象存储。无论采用哪种方式，前端都不能直接拼接服务器文件路径，必须通过 DRF 授权后的报告入口访问。

## 11. 模块边界

- `api-test/` 不负责 Web 页面、数据库模型或 Jenkins stage 编排。
- `jenkins/` 不负责 pytest 重试算法和后端数据模型。
- `back-end/` 不直接执行 pytest，不绕过 Jenkins 执行测试。
- `front-end/` 不直接访问 Jenkins 凭据、服务器文件路径或运行产物目录。
- `docker/` 不存放业务代码和运行报告，但负责描述业务服务如何构建为镜像并被 Compose 编排。
- `project-info/` 不存放业务实现代码或运行产物。

## 12. 安全原则

- 不提交真实账号、密码、token、cookie、租户密钥、Jenkins API Token、生产 URL 或敏感地址。
- `.env` 属于本地私有配置，不进入 git。
- 示例配置必须使用占位符或环境变量。
- Jenkins 凭据通过 Jenkins Credentials、环境变量或本地私有配置管理。
- 报告、日志、抓包和运行时产物不作为业务代码提交。
- 整体 Docker 化部署不等于生产安全方案；生产化还需要单独补充 HTTPS、备份恢复、权限隔离、镜像扫描、日志审计和网络策略。

## 13. 架构图

本目录包含新的 draw.io 架构图源文件和导出图片：

```text
project-info/project_detail/project-architecture.drawio
project-info/project_detail/project-architecture.png
project-info/project_detail/project-architecture.drawio.png
```

本机 draw.io desktop CLI 安装路径：

```text
C:\Users\admin\AppData\Local\Programs\draw.io\draw.io.exe
```

重新导出 PNG 可使用：

```powershell
$drawio = "$env:LOCALAPPDATA\Programs\draw.io\draw.io.exe"
& $drawio -x -f png --width 2000 -o "project-info\project_detail\project-architecture.png" "project-info\project_detail\project-architecture.drawio"
& $drawio -x -f png -e -s 2 -o "project-info\project_detail\project-architecture.drawio.png" "project-info\project_detail\project-architecture.drawio"
python C:\Users\admin\.codex\skills\drawio-skill\scripts\repair_png.py project-info\project_detail\project-architecture.drawio.png
```
