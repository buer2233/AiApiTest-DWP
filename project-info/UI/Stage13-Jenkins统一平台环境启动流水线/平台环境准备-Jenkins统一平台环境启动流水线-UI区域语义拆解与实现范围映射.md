# 平台环境准备-Jenkins统一平台环境启动流水线-UI区域语义拆解与实现范围映射

## 1. UI 阶段结论

- 本需求不新增平台 Vue 页面、路由、组件、按钮、弹窗、字段或说明文字。
- 用户可在 Jenkins 原生参数页手工点击构建；AI 或用户也可通过仓库 helper 触发、轮询同一个 Jenkins Job。两种入口遵循同一 Pipeline 契约。
- 用户必须先手工启动 MySQL 与 Jenkins。环境 Pipeline 只检查二者，不启动、停止、重建或重启它们。
- 本阶段交互面固定为 Jenkins 参数页、Console、Build Summary 与 Allure/归档页面；这些均是外部系统原生页面，不进入 Vue DOM。
- 本阶段高保真视觉产物是可编辑的 draw.io 架构/交互图，不是产品页面原型。冻结需求已明确“无新增 Vue UI”，因此 imagegen 五候选图和 Figma 产品页面落稿流程不适用；强行生成产品页面候选图会错误扩大实现范围。
- `DESIGN-claude.md` 仅用于架构图的暖色画布、珊瑚强调色、深色执行面和克制层级，不改变 Jenkins 原生界面，也不构造新的产品 UI。

## 2. 输入、产物与追溯

| 项 | 路径 / 结论 |
| --- | --- |
| 冻结需求 | `../../demand/Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-需求说明.md` |
| 需求状态 | L 级，2026-07-13 已由主人冻结，共 42 条 AC |
| UI 语义说明 | `平台环境准备-Jenkins统一平台环境启动流水线-UI区域语义拆解与实现范围映射.md` |
| 架构/交互图源文件 | `平台环境准备-Jenkins统一平台环境启动流水线-architecture.drawio` |
| 产品页面候选图 | 不适用：需求明确不新增 Vue 产品 UI |
| 前端实现边界 | `front-end/src` 不新增 DOM、route、组件或业务交互；只允许后续实施容器构建、Nginx SPA/代理/健康配置及相关测试配置 |

## 3. 交互与架构主链

### 3.1 触发前置条件

1. 用户在宿主环境手工启动 MySQL 与 Jenkins，并等待二者进入可检查状态。
2. 用户在 Jenkins 原生 `Build with Parameters` 页面设置 `build_all`、`run_full_tests` 后点击构建；或 AI/用户调用仓库 helper 传递同名参数。
3. helper 只调用 Jenkins API、轮询 queue/build 并解释结构化结果，不直接执行 Docker、pip、npm 或应用进程命令。
4. Jenkins Pipeline 在 Preflight 阶段只检查 MySQL、Jenkins、根 `.env`、workspace、Docker CLI/Compose 和 Docker Socket；检查失败时不进入依赖或部署阶段。

### 3.2 七阶段 Pipeline

`Checkout/Workspace -> Bootstrap Preflight -> Dependency Assurance -> Deploy -> Health -> Smoke/Full Tests -> Archive & Summary`

| 阶段 | 核心行为 | 成功反馈 | 失败边界 |
| --- | --- | --- | --- |
| Checkout/Workspace | 校验仓库与 workspace 模式 | 进入 Preflight | 不创建应用服务 |
| Bootstrap Preflight | 只读检查 Jenkins、MySQL、`.env`、Docker/Compose、Socket | 输出检查结果并进入依赖阶段 | 固定错误码 + 证据 + 修复建议 + rerun，不部署 |
| Dependency Assurance | 检查 backend、frontend、api-runner 三域哈希、label 和镜像完整性；每域最多构建一次 | `SATISFIED/REUSED` 或 `INSTALL_SUCCESS/BUILD_SUCCESS` | 全部域检查完成后聚合失败，部署前终止 |
| Deploy | 固定 Compose project `aiapitest-dwp` 管理 backend、frontend/Nginx、jenkins-sync-worker | 按全量/增量语义创建或重建应用服务 | 保留容器现场，不回滚、不停服、不删 volume |
| Health | 检查 backend live/ready、frontend/Nginx、代理和 worker 心跳 | 全部健康后进入测试 | 区分配置、数据库、schema、代理、心跳和超时原因 |
| Smoke/Full Tests | 默认无凭据冒烟；可选平台自身全量回归 | 生成标准测试证据 | 不运行外部业务 `test_case` 全量；失败仍保留服务 |
| Archive & Summary | `docker cp` 回传 runner 产物，归档日志/状态/报告，输出地址 | Summary 与 Allure/归档入口可访问 | 导出失败保留 runner，并返回 `RUNNER_ARTIFACT_EXPORT_FAILED` |

### 3.3 容器与产物关系

- Jenkins controller 通过受信任本地 Docker Socket 控制镜像构建、Compose 应用部署和短生命周期测试容器。
- 常驻应用服务为 `backend`、`frontend`（Node 多阶段构建后由 Nginx 运行）和 `jenkins-sync-worker`。
- MySQL 与 Jenkins 属于人工 bootstrap 边界，永久排除在环境 Pipeline 生命周期管理之外。
- `api-runner` 不作为常驻业务服务；现有通用、Daily、模块重试和失败重试 Job 只在已验证的 api-runner 镜像中执行 `tools/ci_runner.py`。
- runner 使用镜像内已校验源码，不把 Jenkins 容器 workspace 作为宿主 Docker bind source。
- `summary.json`、`failed_nodeids.json`、`console.log`、`allure-results/`、`allure-report/` 在删除 runner 前通过 `docker cp` 回传到 `api-test/runtime/ci-runs/{run_id}/`。

## 4. 区域语义拆解

| 区域编号 | 图片位置 / 交互区域 | 区域类型 | 是否进入前端 | 前端落点 | 触发条件 | 禁止项 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | 图上方触发区：Jenkins `Build with Parameters` 参数页 | Jenkins 外部系统页面 | 否 | 不进入 Vue DOM；Jenkins 原生 Job 参数页 | 用户打开固定环境 Job；helper 走同一参数契约但不展示页面 | 不复制为平台表单；不新增“启动环境”按钮、路由或弹窗；不得展示私有 Jenkins 凭据 |
| R2 | 图下方 Jenkins 输出区：Console | Jenkins 外部系统页面 | 否 | 不进入 Vue DOM；Jenkins 原生 Console Output | 构建开始后查看或由 helper 读取脱敏结果 | 不把 stage 日志、Docker 输出、错误诊断块复制到产品页面；敏感值必须为 `***` |
| R3 | 图下方 Jenkins 输出区：Build Summary | Jenkins 外部系统页面 | 否 | 不进入 Vue DOM；当前 Jenkins build 摘要 | `post/always` 生成 | 不在 Vue 中新增摘要卡片；不得硬编码 localhost、端口或历史 build URL |
| R4 | 图下方 Jenkins 输出区：Allure / artifact | Jenkins/Allure 外部页面 | 否 | 不进入 Vue DOM；Jenkins 插件入口或归档下载 | 测试证据生成并执行归档；插件发布失败时使用归档 | 不新增独立 Allure 服务或 Vue 报告页；插件告警不得改写基础设施成功状态 |
| R5 | 图下方范围冻结区：平台 Vue 页面 | 不实现说明 | 否 | `front-end/src` 无新增 DOM、route、组件、按钮、弹窗或帮助文字 | 无产品 UI 触发条件 | 不得把整张架构图、参数、Console、Summary、Allure 或风险说明一比一复刻到 Vue 页面 |
| R6 | 图中的箭头、色块、阶段关系、Docker Socket 风险、错误码与边界注记 | 设计标注层 | 否 | 不进入 DOM；仅用于设计、RTM、测试和验收资料 | 阅读本说明或 `.drawio` 文件 | 不进入产品截图、可访问名称、Playwright DOM 断言、日志文案或用户可操作控件 |

## 5. 前端实现范围映射

| 用户路径 / 状态 | Vue route | Vue 组件 / DOM | 用户动作 | 实际交互落点 | Playwright / 验收点 | Stage13 前端动作 |
| --- | --- | --- | --- | --- | --- | --- |
| 手工启动基础服务 | 无 | 无 | 用户在宿主环境启动 MySQL、Jenkins | Docker/Compose 外部 bootstrap 操作 | MySQL/Jenkins 容器 ID 在环境 Job 全量构建前后不变 | 不实现 UI |
| 手工触发环境 Job | 无 | 无 | 在 Jenkins 设置两个布尔参数并点击构建 | R1 Jenkins 原生参数页 | 默认 `build_all=true`、`run_full_tests=false`；两参数正确传入 | 不实现 UI |
| AI/用户 helper 触发 | 无 | 无 | 调用 PowerShell/Shell helper | Jenkins API queue/build | 输出 build URL、终态、错误码和证据；日志不泄露用户名/token | 不实现 UI |
| 查看实时阶段与诊断 | 无 | 无 | 查看 Console 或由 helper 轮询 | R2 Jenkins Console | 固定 stage、依赖状态和诊断块可检索；失败不旁路修复 | 不实现 UI |
| 查看构建结果与地址 | 无 | 无 | 打开当前 build 摘要 | R3 Build Summary | 成功显示 Jenkins/MySQL/frontend/backend/API/health/Allure 地址；失败显示首因、全部错误码、证据、建议与 rerun | 不实现 UI |
| 查看测试报告 | 无 | 无 | 打开 Allure 或下载归档 | R4 Jenkins 插件/Artifact | 插件失败仅告警，原始结果/HTML 仍可取得 | 不实现 UI |
| 使用现有平台页面 | 既有 route 保持不变 | 既有组件保持不变 | 正常使用平台 | R5 既有 Vue 应用 | DOM、导航与可访问名称不因 Stage13 新增产品元素 | 仅验证无意外新增 DOM |
| 阅读架构风险与流程 | 无 | 无 | 查看设计资料 | R6 设计标注层 | 标注不进入产品 DOM、截图和 Playwright 页面断言 | 不实现 UI |

## 6. Jenkins 原生交互字段与反馈

### 6.1 R1 参数页

| 字段 | Jenkins 控件 | 默认值 | 含义 | 校验 |
| --- | --- | --- | --- | --- |
| `build_all` | boolean parameter | `true` | true：使用缓存构建全部应用镜像并强制重建应用容器；false：增量处理缺失或变化服务 | 任一模式都排除 MySQL/Jenkins，保留 volumes |
| `run_full_tests` | boolean parameter | `false` | false：固定无凭据冒烟；true：平台自身全量回归 | 不运行依赖外部业务系统的业务接口全量 |

固定 Job：`AiApiTest-DWP-Platform-Bootstrap`；Pipeline script path：`jenkins/Jenkinsfile.platform-bootstrap`；Job 由用户手工创建并禁止并发构建。

### 6.2 R2 Console 诊断块

失败诊断固定包含：`stage / code / target / reason / observed / evidence / suggestion / rerun`。环境变量只展示键名和是否存在，密码、token、Cookie、Authorization 等值不得进入日志。

### 6.3 R3 Summary

- 成功：输出各依赖域状态、应用服务健康状态、测试状态、公开访问地址与当前 Allure 入口。
- 失败：输出首要失败原因、全部错误码、证据路径、修复建议和重新构建入口。
- 地址公开主机、IP 和端口来自根 `.env`；Allure Job/build 路径由 Jenkins runtime 生成。

### 6.4 R4 Allure / Artifact

- Jenkins Allure 插件可用时展示当前 build 报告入口。
- 插件发布失败时只告警，原始 `allure-results/`、HTML 报告和标准运行产物仍归档。
- 不新增常驻 Allure 服务，不增加 Vue 代理页面。

## 7. 状态、异常、边界与权限校准

| 分类 | 覆盖结论 |
| --- | --- |
| 正常场景 | 覆盖人工 bootstrap、手工/AI 双入口、三域满足或一次构建、全量/增量部署、健康、默认冒烟、可选全量、Summary 与 Allure |
| 异常场景 | 覆盖 `.env` 缺失、Docker/Compose/Socket 不可用、MySQL 未运行或不健康、三域聚合失败、部署/健康/测试失败、Allure 插件告警、runner 产物导出失败 |
| 边界场景 | 覆盖无变化增量不重建、全量保留缓存、每域最多构建一次、有限轮询/测试超时、Job 名编码、local-mounted/SCM workspace、失败保留现场 |
| 权限场景 | Jenkins 参数、Console、Summary 与 Allure 由 Jenkins 自身权限控制；Docker Socket 仅限受信任本地 Jenkins；普通平台用户不获得环境 Job 配置权 |
| 数据保护 | 禁止 `down -v`、删除命名 volume、执行 migration/init admin、在宿主机或运行容器动态安装依赖 |
| 容器化兼容 | 服务间使用 Compose 服务名；公开地址和端口由根 `.env` 注入；固定 project name 为 `aiapitest-dwp`；不写个人绝对路径或真实凭据 |

## 8. 视觉产物说明

- 架构图使用单页横向布局：上方为触发与人工 bootstrap，中部为七阶段 Pipeline，下方为 Docker/Compose 拓扑和 Jenkins 原生输出区域。
- 暖色画布和珊瑚强调色用于主触发与部署动作；深色用于 Pipeline 执行面；绿色用于健康/成功语义；黄色用于 bootstrap/风险边界；红色仅用于失败或禁止范围。
- 图中的颜色、连线和风险文字只帮助理解架构，不代表产品组件、状态标签或可点击控件。
- draw.io 源文件必须通过结构校验；如本机 draw.io CLI 不可用，Markdown 与 `.drawio` 先作为正式替代交付，PNG 缺失原因记录在本说明和 Task 0B 报告中。

## 9. UI 阶段完成门禁

- [x] R1-R6 均有稳定编号、区域类型、是否进入前端、落点、触发条件和禁止项。
- [x] 已冻结页面/路由/组件/DOM 映射，结论为“无新增 Vue 产品 UI”。
- [x] 已覆盖人工 bootstrap、手工/AI 触发、七阶段主链、应用服务、Docker Socket、runner 与 `docker cp` 产物回传。
- [x] 已区分 Jenkins 原生页面、Allure 外部页面、Vue 不实现区域和设计标注层。
- [x] 已说明 imagegen/Figma 产品页面流程不适用，未擅自新增产品 UI。
- [x] 未修改需求、测试用例或业务代码。

