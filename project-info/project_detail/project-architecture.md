# AiApiTest-DWP Project Architecture

## 1. 项目定位

`AiApiTest-DWP` 是一个面向 AI 协作和企业级 CICD 的自动化测试平台。项目采用 monorepo 单仓库结构，将接口自动化执行核心、Jenkins 流水线、DRF 后端、Vue 3 前端、Docker 基础设施和项目交接资料统一维护。

平台不绑定具体业务系统。所有测试用例、平台接口、Jenkins 脚本、Docker 配置和前端页面都必须保持可迁移、可复用，不提交真实账号、密码、token、cookie、Jenkins API Token、生产地址或敏感业务常量。

## 2. 总体架构原则

- Jenkins 是严格执行主干：平台侧所有测试执行、模块重试、失败重试和报告生成都必须通过 Jenkins。
- `api-test` 是测试执行协议唯一实现位置：pytest 参数、失败 node id、重试模式、Allure 产物和 summary 协议都在该模块演进。
- DRF 后端不直接执行 pytest，不拼接 pytest 命令，不重复实现失败重试算法。
- DRF 后端负责平台编排和数据治理：权限、任务、模块快照、失败用例、Jenkins 状态同步、报告入口和审计。
- Vue 3 前端负责管理后台体验：模块通过率、失败用例、重试操作、Jenkins 任务和报告入口。
- Docker 负责基础服务，不默认把业务应用全部容器化。

## 3. 模块组成

| 模块 | 目录 | 技术栈 | 核心职责 |
| --- | --- | --- | --- |
| 接口自动化执行核心 | `api-test/` | Python、pytest、requests、allure-pytest | 测试用例、接口方法、失败 node id、重试执行器、Allure 原始结果 |
| Jenkins 执行主干 | `jenkins/` | Jenkins、Groovy、Pipeline | 参数化 Job、流水线编排、节点环境、归档、Allure 发布 |
| 后端平台层 | `back-end/` | Python、Django REST Framework、MySQL | 用户权限、任务模型、Jenkins 触发和同步、模块快照、失败用例、报告入口 |
| 前端展示层 | `front-end/` | Vue 3、Vite、TypeScript、Element Plus | 企业级管理后台、筛选表格、弹窗、状态操作、报告入口 |
| 基础设施 | `docker/` | Docker Compose、MySQL、Jenkins | 本地依赖服务、部署说明、可选 Jenkins 工具链镜像 |
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

## 8. 开发流程架构

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

Docker 和 Jenkins 属于基础设施设计阶段，不要求每个需求都重复产出；需要调整时按实际工作执行。

## 9. 报告与产物

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

## 10. 模块边界

- `api-test/` 不负责 Web 页面、数据库模型或 Jenkins stage 编排。
- `jenkins/` 不负责 pytest 重试算法和后端数据模型。
- `back-end/` 不直接执行 pytest，不绕过 Jenkins 执行测试。
- `front-end/` 不直接访问 Jenkins 凭据、服务器文件路径或运行产物目录。
- `docker/` 不存放业务代码和运行报告。
- `project-info/` 不存放业务实现代码或运行产物。

## 11. 安全原则

- 不提交真实账号、密码、token、cookie、租户密钥、Jenkins API Token、生产 URL 或敏感地址。
- `.env` 属于本地私有配置，不进入 git。
- 示例配置必须使用占位符或环境变量。
- Jenkins 凭据通过 Jenkins Credentials、环境变量或本地私有配置管理。
- 报告、日志、抓包和运行时产物不作为业务代码提交。

## 12. 架构图

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
