# 平台环境准备-Jenkins统一平台环境启动流水线-需求说明书

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 平台环境准备-Jenkins统一平台环境启动流水线 |
| 需求分级 | L |
| 裁剪说明 | 不裁剪。本需求跨 Jenkins、Docker Compose、DRF、Vue/Nginx、Jenkins 同步 worker、`api-test` runner、依赖治理、测试门禁和 AI 协作规则，改变平台统一环境启动协议。 |
| 关联模块 | `jenkins` / `docker` / `back-end` / `front-end` / `api-test` / 根协作规范 |
| 文档状态 | 已冻结 |
| 负责人 | 主人 |
| 需求质量评分 | 94/100（业务价值 27/30、功能需求 24/25、用户体验 18/20、技术约束 15/15、范围优先级 10/10） |

---

## §0 待澄清清单（澄清门禁）

| 编号 | 待澄清点 | 可选方案 / 影响面 | 主人裁决 | 状态 |
| --- | --- | --- | --- | --- |
| Q1 | `build_all` 是否管理 Jenkins controller | A：Jenkins 为人工 bootstrap；B：外部 agent/两阶段重启 Jenkins | 采用 A；用户自行启动 Jenkins，Pipeline 只检查 Jenkins | 已确认 |
| Q2 | MySQL 是否由 Pipeline 管理 | A：MySQL 为人工 bootstrap；B：Pipeline 管理 MySQL | 采用 A；用户自行启动 MySQL，Pipeline 只检查 MySQL | 已确认 |
| Q3 | 后端、前端、worker、runner 的运行形态 | A：正式容器化；B：宿主机进程 | 采用 A；应用服务纳入 Compose，runner 按任务启动 | 已确认 |
| Q4 | Jenkins 如何获得 Docker 控制能力 | A：controller 工具镜像 + Docker Socket；B：独立 Docker agent | 采用 A；限定受信任本地 Jenkins | 已确认 |
| Q5 | `build_all=true` 是否禁用构建缓存 | A：保留缓存并强制重建容器；B：每次 `--no-cache` | 采用 A；保留缓存，避免无变化依赖重复下载 | 已确认 |
| Q6 | 多组依赖检查失败如何处理 | A：全部检查后汇总失败；B：首错立即终止 | 采用 A；每域最多安装一次，汇总后在部署前终止 | 已确认 |
| Q7 | 默认冒烟是否依赖登录账号 | A：无凭据健康冒烟；B：必须真实登录 | 采用 A；全量或专项验收才使用私有账号 | 已确认 |
| Q8 | 全量测试是否包含外部业务接口用例 | A：只跑平台自身回归；B：同时运行全部业务用例 | 采用 A；业务全量继续由 Daily Job 负责 | 已确认 |
| Q9 | 应用启动或测试失败是否自动回滚 | A：保留现场；B：自动回滚 | 采用 A；保留容器和日志，不自动回滚或停服 | 已确认 |
| Q10 | Allure 是否新增独立服务 | A：继续 Jenkins 构建级入口；B：新增常驻服务 | 采用 A；复用 Jenkins 插件和归档 | 已确认 |
| Q11 | 后端健康探针方式 | A：新增 live/ready；B：复用文档页 | 采用 A；无凭据、无敏感信息的独立探针 | 已确认 |
| Q12 | 环境 Job 是否自动创建 | A：init Groovy 自动创建；B：用户手工创建 | 采用 A；与既有 local-mounted Job 一样，由 Jenkins 启动 init Groovy 幂等创建或修复固定 Job | 已确认（2026-07-14 验收裁决） |
| Q13 | 依赖安装位置 | A：只安装到不可变镜像；B：运行容器/宿主机动态安装 | 采用 A；通过清单哈希和镜像构建完成一次安装 | 已确认 |
| Q14 | 后续 AI 如何使用该 Pipeline | A：helper 自动触发/轮询；B：只能提示用户点击 | 采用 A；AI 禁止旁路 Docker 和依赖命令 | 已确认 |
| Q15 | 应用部署阶段统一失败码 | 冻结前已批准的错误码设计包含 `DEPLOY_SERVICE_FAILED`；需写回正式规格以供测试断言 | 采用 `DEPLOY_SERVICE_FAILED`，按具体 target/reason 区分服务和原因 | 已确认 |

---

## §1 需求背景与目标

- **背景**：
  - 当前平台环境启动分散在 Docker、后端 `runserver`、前端 Vite、同步 worker、依赖安装和测试命令中，用户需要理解多个目录和工具链才能完成环境准备。
  - 当前 `docker-compose.yml` 只管理 MySQL 和 Jenkins；后端、前端和 worker 尚未容器化，无法由 Jenkins 稳定守护宿主机进程。
  - 现有 Jenkins Pipeline 主要执行 `api-test`，不存在固定的平台环境准备 Job；依赖失败日志和环境健康反馈也没有统一契约。
  - 后续 AI 若直接执行零散 Docker、pip、npm 命令，容易绕过 Jenkins 主干、产生不可复现依赖或误操作数据卷。
- **目标**：
  - 用户只需自行启动 MySQL 和 Jenkins Docker 容器；Jenkins 启动 init Groovy 幂等创建或修复固定 Job 后，在 Jenkins 页面点击构建，即可完成应用镜像准备、服务启动、健康检查、默认冒烟和访问地址输出。
  - 后续 AI 只能通过仓库 helper 触发和轮询该 Job，不能直接重启应用容器或在宿主机安装依赖。
  - 所有失败均提供结构化、脱敏、可操作的诊断，明确引导用户修复问题后重新构建。
- **成功指标 / 价值**：
  - `build_all=true` 一次构建后，`backend`、`frontend`、`jenkins-sync-worker` 全部健康，MySQL/Jenkins 容器未被重启，默认冒烟通过。
  - `build_all=false` 且代码、配置、依赖无变化时，不发生无意义的镜像重建和容器重建。
  - 每个依赖域每次 Pipeline 最多执行一次安装构建；安装成功或失败均有完整日志和确定状态。
  - 任一失败在 Jenkins 摘要中给出固定错误码、失败原因、证据、修复建议和重新构建入口。
  - AI 环境重启和依赖检查操作均可追溯到 Jenkins build URL，不存在仓库认可的旁路流程。

## §2 范围

- **做（in scope）**：
  - 新增固定平台环境 Jenkinsfile 和可复用 Pipeline 脚本；本地 Compose Jenkins 启动时由版本化 init Groovy 幂等创建或修复 Job。
  - 为 Jenkins 工具镜像安装 Docker CLI/Compose，并挂载 Docker Socket。
  - 为 DRF 后端增加生产型镜像和 `backend` Compose service。
  - 为 Vue 前端增加 Node 多阶段构建、Nginx 运行镜像和 `frontend` Compose service。
  - 复用 backend 镜像增加 `jenkins-sync-worker` Compose service。
  - 增加按任务启动的 `api-runner` 工具镜像，不作为常驻业务服务。
  - 改造现有通用、Daily、模块重试和失败重试 Jenkins Pipeline：全部使用已由环境 Job 验证的 `api-runner` 镜像执行 `tools/ci_runner.py`，移除业务 Job 内的 venv 创建和动态依赖安装。
  - 建立三域依赖清单哈希、完整性检查、一次构建安装和聚合失败日志。
  - 实现 `build_all` 全量/增量模式、健康检查、无凭据冒烟、可选平台全量回归。
  - 新增 DRF `live`/`ready` API、Nginx 健康入口和 worker 心跳健康检查。
  - 归档 Compose 状态、容器日志、依赖日志、测试证据，并输出所有访问地址和当前 Allure 链接。
  - 新增 Jenkins API helper，供 AI 触发、轮询并解释结构化结果。
  - 更新根及相关模块 `AGENTS.md`、`.env.example`、部署/快速启动文档和静态门禁测试。
- **不做（out of scope）**：
  - 不由环境 Pipeline 启动、停止、重建或重启 MySQL、Jenkins。
  - 不执行 Django migration、静态资源收集、管理员创建或基础数据初始化。
  - 不删除 MySQL、Jenkins、Allure 或测试产物 volume，不执行 `docker compose down -v`。
  - 不新增平台 Vue 页面、路由、组件或弹窗。
  - 不新增独立 Allure 常驻服务。
  - 不在环境 Job 中执行依赖外部业务系统的 `api-test/test_case` 全量。
  - 不改变 `tools/ci_runner.py` 的参数、重试、summary、failed node ids 和 Allure 执行协议；只改变现有业务 Job 的执行载体和依赖准备位置。
  - 不创建第二条环境旁路 Job；仅由版本化 init Groovy 幂等创建或修复固定环境 Job。
  - 不实现自动镜像/容器回滚。
  - 不把 Docker Socket 方案描述为生产安全部署方案。

## §3 用户角色与权限矩阵

| 角色 | 可执行操作 | 禁止操作 | 数据可见范围 |
| --- | --- | --- | --- |
| 平台运维/主人 | 自行启动 MySQL/Jenkins；确认 init 已创建/修复后构建环境 Job；查看日志、摘要和报告 | 未确认时删除 volume；把真实凭据写入 Job 脚本 | 本地平台全部服务与构建证据 |
| AI 协作代理 | 通过仓库 helper 触发/轮询环境 Job；读取结构化错误并反馈 | 直接执行应用 Docker 重启、`pip install`、`npm install`；输出凭据 | Jenkins build 状态、脱敏日志和公开地址 |
| Jenkins 环境 Job | 检查 bootstrap 服务；构建镜像；管理应用服务；执行测试和归档 | 管理 MySQL/Jenkins 生命周期；执行 migration/init admin；删除 volume | 当前 workspace、Docker 应用服务、脱敏环境配置 |
| 普通平台用户 | 使用启动后的前端和后端能力 | 配置或触发环境 Job | 已授权平台业务数据 |

---

## §4 功能清单与验收标准

### F1 Bootstrap 前置检查与可操作诊断

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 校验 workspace、根 `.env`、必要环境变量、Docker CLI、Compose、Docker Socket、Jenkins 运行状态、MySQL 容器和健康状态。
  - Jenkins 通过 Compose `group_add` 使用根 `.env` 的 `DOCKER_GID` 获得 Docker Socket 最小必要组权限；禁止通过 `chmod 666` 放宽 Socket 权限。
  - Windows Docker Desktop 默认允许使用文档给出的兼容 GID；Linux 部署必须按宿主机 Docker Socket 实际 GID 配置 `DOCKER_GID`，并由用户自行重建 Jenkins bootstrap 容器。
  - 前置检查失败时不进入依赖构建或应用部署。
  - 每个失败均输出统一诊断块：`历史验证记录（suggestion/rerun，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）`。
- **关联数据表**：不涉及持久化；证据写入当前 Jenkins workspace/构建归档。
- **验收标准**：
  - `AC-S13-1.1` — Given `.env` 不存在 When 执行 Job Then 以 `CONFIG_ENV_MISSING` 失败，列出模板路径和重新构建指引，不创建应用容器。
  - `AC-S13-1.2` — Given Docker CLI、Compose 或 Socket 不可用 When 预检 Then 输出对应固定错误码、原始命令退出码和修复建议。
  - `AC-S13-1.3` — Given Jenkins 正在执行当前 Job When 预检 Then 只检查 Jenkins，不重启或重建 controller。
  - `AC-S13-1.4` — Given MySQL 容器未运行 When 预检 Then 以 `BOOTSTRAP_MYSQL_NOT_RUNNING` 失败，指导用户启动 MySQL、等待 healthy 后重新构建。
  - `AC-S13-1.5` — Given MySQL 已运行但不健康 When 预检 Then 以 `BOOTSTRAP_MYSQL_UNHEALTHY` 失败并归档 MySQL 状态/脱敏日志，不操作该容器。
  - `AC-S13-1.6` — Given Docker Socket 已挂载但 Jenkins 用户无访问权限 When 预检 Then 以 `DOCKER_SOCKET_PERMISSION_DENIED` 失败，输出实际访问结果、`DOCKER_GID` 配置和用户自行重建 Jenkins 的指引，不建议 `chmod 666`。
- **异常场景**：读取配置异常、Docker daemon 不可达、Compose 文件非法均须明确区分，不统一包装为“环境失败”。
- **边界值**：日志中环境变量只显示键名和是否存在，敏感值显示为 `***`。
- **并发 / 幂等**：预检只读，不改变服务状态。

### F2 不可变镜像依赖检查与一次安装

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 依赖域固定为 `backend`、`frontend`、`api-runner`。
  - 通过 requirements/package-lock 依赖哈希、完整镜像构建输入哈希、镜像 label 和镜像内完整性检查判断依赖及镜像是否满足。
  - 构建输入哈希至少覆盖目标 Dockerfile、依赖清单、模块源码和会进入镜像的运行配置；源码变化必须触发增量镜像构建。
  - 需要安装时，每个依赖域在一次 Pipeline 中最多执行一次目标镜像构建；pip/npm 安装仅发生在 Dockerfile 构建层。
  - 单域失败后继续检查其余域，最终汇总失败，并在部署前终止。
  - 环境 Job 验证成功的 `api-runner` 镜像是所有现有业务测试 Job 的唯一 Python/pytest/Allure 运行环境；业务 Job 不再创建 venv 或执行 pip 安装。
  - api-runner 使用镜像内源码执行，不把 Jenkins 容器内 workspace 作为宿主 Docker bind source；源码版本由镜像构建输入 label 与当前仓库哈希校验。
- **关联数据表**：不涉及持久化；依赖日志和状态归档到 Jenkins build。
- **验收标准**：
  - `AC-S13-2.1` — Given 三域依赖和完整构建输入均满足且 `build_all=false` When 检查 Then 三域依赖状态均为 `SATISFIED`、镜像状态均为 `REUSED`，不调用镜像构建。
  - `AC-S13-2.2` — Given backend 清单变化 When 检查 Then backend 只构建一次，成功后状态为 `INSTALL_SUCCESS` 并记录清单哈希。
  - `AC-S13-2.3` — Given frontend 和 api-runner 均构建失败 When 检查 Then 两域各只尝试一次，均输出 `INSTALL_FAILED` 和独立诊断块，最后统一失败。
  - `AC-S13-2.4` — Given 任一依赖失败 When 汇总完成 Then 不启动或重启应用服务，已有容器保持原状态。
  - `AC-S13-2.5` — Given `build_all=true` When 检查 Then 三域均使用 Docker 缓存构建一次，不使用 `--no-cache`，无依赖变化时允许复用缓存层。
  - `AC-S13-2.6` — Given依赖清单未变但后端源码、前端源码或目标 Dockerfile 已变化 When `build_all=false` Then 对应镜像只构建一次，依赖状态仍可为 `SATISFIED`，镜像状态为 `BUILD_SUCCESS`。
  - `AC-S13-2.7` — Given扫描通用、Daily、模块重试和失败重试 Pipeline When 回归 Then 不包含 venv 创建、`pip install` 或 `install_missing_requirements`，并只在 `api-runner` 容器中调用 `tools.ci_runner.py`。
  - `AC-S13-2.8` — Given `api-runner` 镜像缺失或依赖/构建输入 label 与当前仓库不匹配 When 任一业务 Job 启动 Then 在执行用例前以 `API_RUNNER_IMAGE_NOT_READY` 失败，指导先运行环境 Job，不在业务 Job 中临时安装依赖。
  - `AC-S13-2.9` — Given本地挂载或远端 SCM workspace When 业务 Job 启动 api-runner Then runner 使用镜像内已校验源码，不创建指向 Jenkins 容器 workspace 的 Docker bind mount。
- **异常场景**：Docker build 超时、网络失败、包版本冲突、`pip check`/`npm` 完整性失败必须使用不同原因文本并保留构建日志。
- **边界值**：清单为空、lock 文件缺失或镜像 label 缺失视为需要构建或明确配置失败，不静默通过。
- **并发 / 幂等**：同一 Job 禁止并发构建；重复执行在无变化时结果一致。

### F3 应用服务全量/增量部署

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 管理服务固定为 `backend`、`frontend`、`jenkins-sync-worker`。
  - Compose project identity 固定为代码级名称 `aiapitest-dwp`；不得由 Jenkins Job 名、workspace 目录名或 SCM checkout 路径隐式推导。
  - `build_all=true` 使用已完成构建的应用镜像强制重建全部应用容器。
  - `build_all=false` 只创建缺失/停止服务，并由 Compose 对配置或镜像变化进行增量重建。
  - MySQL/Jenkins 永久排除；任何模式均保留 volumes 和运行产物。
- **关联数据表**：不新增表；后端运行使用现有 MySQL 数据。
- **验收标准**：
  - `AC-S13-3.1` — Given `build_all=true` When 部署 Then 三个应用容器 ID 更新，MySQL/Jenkins 容器 ID 不变。
  - `AC-S13-3.2` — Given `build_all=false` 且无代码/配置/镜像变化 When 部署 Then健康应用容器不被无意义重建。
  - `AC-S13-3.3` — Given 某应用服务缺失或已停止 When 增量部署 Then 仅恢复必要服务。
  - `AC-S13-3.4` — Given 部署命令失败 When 处理 Then 以 `DEPLOY_SERVICE_FAILED` 失败并保留当前容器现场、Compose 状态和日志，不执行回滚或停服。
  - `AC-S13-3.5` — Given 任意运行模式 When 检查命令 Then 不出现 `down -v`、MySQL/Jenkins recreate 或 volume 删除。
  - `AC-S13-3.6` — Given本地挂载 workspace 与远端 SCM workspace 路径不同 When 执行环境 Job Then 均命中 `aiapitest-dwp` 同一 Compose project 和同一组应用容器，不创建第二套同名平台服务。
- **异常场景**：端口占用、网络冲突、镜像不存在、容器启动失败均输出服务级错误码和修复建议。
- **边界值**：服务已存在但 unhealthy 时允许 Compose 按冻结模式处理，随后必须通过健康阶段验证。
- **并发 / 幂等**：环境 Job 禁止并发执行，避免两个 build 同时操作同一 Compose project。

### F4 健康检查、冒烟与平台全量回归

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 后端提供 `/api/v1/health/live/` 和 `/api/v1/health/ready/`。
  - frontend Nginx 提供健康入口并代理 `/api` 到 backend；worker 每轮写入本地心跳文件，容器 healthcheck 检查心跳新鲜度。
  - 默认运行无凭据冒烟；`run_full_tests=true` 时运行平台自身全量回归。
  - `run_full_tests=true` 的执行载体固定为不可变镜像：backend 镜像执行后端 pytest；frontend 域的测试 target 预装 Node 依赖和固定版本 Playwright 浏览器；api-runner 镜像执行 `api-test` 工具/协议测试及 Jenkins/Docker 静态测试。
  - 全量测试只启动短生命周期测试容器，不在 Jenkins controller、宿主机或正在提供服务的应用容器中安装依赖。
- **关联数据表**：不新增表；ready 只读检查数据库连接和必要 schema，不执行迁移。
- **验收标准**：
  - `AC-S13-4.1` — Given DRF 进程正常 When 请求 live Then 返回 200 和最小 `live` 状态，不访问外部 Jenkins。
  - `AC-S13-4.2` — Given数据库可连接且必要 schema 存在 When 请求 ready Then 返回 200；数据库或 schema 未准备时返回 503 且不泄露连接信息。
  - `AC-S13-4.3` — Given frontend 正常 When 冒烟 Then页面、SPA 路由和 `/api/v1/health/ready/` 代理均可访问。
  - `AC-S13-4.4` — Given worker 正常轮询 When 检查健康 Then 心跳在阈值内；心跳过期时以 `HEALTH_WORKER_STALE` 失败。
  - `AC-S13-4.5` — Given 默认参数 When 执行测试 Then 只运行固定无凭据冒烟集合，不要求平台账号。
  - `AC-S13-4.6` — Given `run_full_tests=true` When 执行 Then 完成后端 pytest、前端单测/构建/Playwright、Jenkins/Docker 静态测试和 `api-test` 工具/协议测试，不执行外部业务 `test_case` 全量。
  - `AC-S13-4.7` — Given健康或测试失败 When Pipeline 结束 Then 构建标记失败但服务不被停止，诊断和测试证据完整归档。
  - `AC-S13-4.8` — Given必要配置缺失、数据库不可连接或存在未应用迁移 When 请求 ready Then 分别返回安全 reason code `configuration_invalid`、`database_unavailable`、`schema_not_ready`，Pipeline 可据此给出不同修复建议。
  - `AC-S13-4.9` — Given `run_full_tests=true` When 检查执行命令 Then 所有测试均在已验证的 backend/frontend-test/api-runner 镜像中执行，Playwright 浏览器在镜像构建阶段准备，测试阶段不发生 pip/npm/npx 依赖安装。
- **异常场景**：健康检查超时、HTTP 非 2xx、代理失败、测试进程超时必须区分错误码。
- **边界值**：所有轮询和测试必须有有限超时；非法超时配置回退安全默认值并记录告警。
- **并发 / 幂等**：健康与冒烟为只读操作，不修改业务数据。

### F5 构建摘要、报告和访问地址

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - `post/always` 归档依赖日志、Compose config/ps、应用容器日志、健康结果、冒烟/全量测试结果和报告。
  - 短生命周期测试容器退出后，在删除容器前使用 `docker cp` 将标准产物导出到 Jenkins 当前 workspace 的既有协议路径；禁止依赖 Jenkins 容器 workspace 的宿主机 bind mount。
  - 构建摘要输出 Jenkins、MySQL、frontend、backend、API 文档、live/ready、当前 Allure 报告地址。
  - 地址的公开主机、IP 和端口来自根 `.env`；Allure Job/build 路径来自 Jenkins runtime。
- **关联数据表**：不涉及业务持久化。
- **验收标准**：
  - `AC-S13-5.1` — Given构建成功 When 查看摘要 Then 所有公开入口均有明确标签和可访问 URL。
  - `AC-S13-5.2` — Given构建失败 When 查看摘要 Then 显示首要失败原因、全部错误码、证据路径、修复建议和重新构建提示。
  - `AC-S13-5.3` — Given多个依赖失败 When 查看摘要 Then 每个依赖域均有独立状态和日志链接。
  - `AC-S13-5.4` — Given Allure Jenkins 插件发布失败 When 结束 Then 只告警，原始 Allure 结果/HTML 仍归档，基础设施成功状态不被插件缺失改写。
  - `AC-S13-5.5` — Given日志包含密码/token/Cookie/Authorization When 归档 Then 敏感值被脱敏或拒绝写入。
  - `AC-S13-5.6` — Given local-mounted 或 SCM 两种 Job 模式 When api-runner/测试容器结束 Then `summary.json`、`failed_nodeids.json`、`console.log`、`allure-results/`、`allure-report/` 均通过 `docker cp` 回传到 `api-test/runtime/ci-runs/{run_id}/`，容器删除后仍可归档。
  - `AC-S13-5.7` — Given测试命令失败但容器仍可读取 When 执行 finally Then 仍先导出产物再删除容器；Given `docker cp` 失败 Then 以 `RUNNER_ARTIFACT_EXPORT_FAILED` 失败并保留 runner 容器 ID、脱敏诊断和人工导出指引，不删除该 runner。
- **异常场景**：某 URL 缺少配置时使用 `CONFIG_REQUIRED_ENV_MISSING` 失败，不输出硬编码 localhost 回退。
- **边界值**：Job 名包含空格或层级时，Allure URL 必须正确编码。
- **并发 / 幂等**：每个 build 使用独立证据目录，不覆盖历史 build。

### F6 AI Jenkins helper 与强制唯一入口

- **能做什么 / 做到什么程度 / 满足什么要求**：
  - 提供 Windows/Linux 兼容 helper，读取私有 Jenkins 配置，触发由启动 init Groovy 创建/修复的推荐环境 Job，传递两个布尔参数，轮询 queue/build 并输出结构化结果。
  - 根及 `jenkins`、`docker`、`back-end`、`front-end`、`api-test` 规则明确：AI 环境重启和依赖检查必须使用 helper/Pipeline。
  - 静态门禁检查关键规则、helper、Jenkinsfile 和禁止旁路文本仍存在。
- **关联数据表**：不涉及业务持久化；Jenkins build 提供审计轨迹。
- **验收标准**：
  - `AC-S13-6.1` — Given有效 Jenkins 私有凭据 When AI helper 触发 Then 获得 queue/build URL，参数与用户请求一致并轮询至终态。
  - `AC-S13-6.2` — Given认证失败、Job 不存在或超时 When helper 执行 Then 返回固定错误码、脱敏原因和用户修复建议。
  - `AC-S13-6.3` — Given Pipeline 返回结构化失败 When helper 结束 Then 向用户反馈错误码、证据和重新构建方式，不直接执行旁路修复。
  - `AC-S13-6.4` — Given扫描仓库 AI 规则 When 回归 Then 明确禁止直接应用容器重启、宿主机 pip/npm 安装和 `down -v`。
  - `AC-S13-6.5` — Given用户不使用 helper When 操作 Then 仍可在 Jenkins 页面手工点击 Job，二者调用同一 Pipeline 契约。
- **异常场景**：queue 被清理、Jenkins 暂时不可达、构建取消均应返回可区分结果。
- **边界值**：helper 日志不得输出 Jenkins 用户名/token；轮询间隔和总超时必须有安全默认值。
- **并发 / 幂等**：若 Job 已运行，helper 不启动并发环境变更；返回当前 build 或明确 busy 错误。

---

## §5 状态机定义

### Pipeline 状态

| 源状态 | 事件 / 操作 | 目标状态 | 守卫条件 | 副作用 |
| --- | --- | --- | --- | --- |
| queued | Jenkins 分配 executor | preflight | Job 未被并发构建占用 | 创建当前 build 证据目录 |
| preflight | bootstrap 检查全部通过 | dependency_check | Jenkins/MySQL/Docker/.env 可用 | 不修改服务 |
| preflight | 任一 bootstrap 检查失败 | failed | 固定错误码已生成 | 归档预检证据，不部署 |
| dependency_check | 三域均 satisfied/install_success | deploy | 每域构建次数 <= 1 | 使用已验证镜像 |
| dependency_check | 任一域 install_failed | failed | 其余域检查已完成 | 汇总失败，不部署 |
| deploy | Compose 应用部署完成 | health_check | 仅管理应用服务 | 容器按参数创建/重建 |
| deploy/health_check | 部署或健康失败 | failed | 日志已采集 | 保留容器现场 |
| health_check | 全部健康 | tests | live/ready/frontend/worker 通过 | 执行冒烟或全量 |
| tests | 测试通过 | success | 报告已生成 | 输出地址和摘要 |
| tests | 测试失败 | failed | 测试证据已生成 | 保留服务，归档证据 |

### 依赖域状态

| 状态 | 含义 | 允许后续动作 |
| --- | --- | --- |
| `SATISFIED` | 依赖清单 label 和镜像内依赖完整性检查均通过 | 允许复用依赖层；镜像仍可能因源码变化而构建 |
| `INSTALL_SUCCESS` | 本次唯一一次目标镜像构建成功且完整性通过 | 允许部署 |
| `INSTALL_FAILED` | 唯一一次构建或完整性检查失败 | 不再安装；完成其他域检查后 Pipeline 失败 |

镜像构建状态独立记录为 `REUSED`、`BUILD_SUCCESS`、`BUILD_FAILED`，禁止把“源码变化导致的镜像构建”误报为“发生依赖安装”。

---

## §6 数据表设计

本需求不新增或修改业务数据表，不创建 Django migration。

| 数据/产物 | 持久化位置 | 写入策略 | 关键约束 |
| --- | --- | --- | --- |
| MySQL 平台数据 | 既有 `aiapitest-mysql-data` volume | 完全保留；Pipeline 只读健康检查 | 禁止 `down -v` |
| Jenkins 配置/历史 | 既有 `aiapitest-jenkins-home` volume | 完全保留 | Pipeline 不管理 Jenkins 生命周期 |
| api-test Allure/运行产物 | runner 内生成，经 `docker cp` 回传到 Jenkins workspace 的 `api-test/runtime/ci-runs/{run_id}/` 后归档 | 按 build/run 隔离，继续既有保留策略 | 不覆盖历史 run；回传成功后才删除 runner |
| Stage13 环境证据 | Jenkins 当前 build artifacts | 每次构建独立目录 | 日志脱敏，不提交运行产物到 git |
| worker 心跳 | worker 容器临时文件系统 | 每轮覆盖时间戳 | 仅用于容器 healthcheck，不作为业务数据 |

---

## §7 API 与 Pipeline 契约

### GET `/api/v1/health/live/`

- **用途 / 权限**：无认证 liveness，仅确认 DRF 进程可响应；不得读取数据库或 Jenkins。
- **请求参数**：无。
- **成功响应**：HTTP 200。

```json
{
  "code": "ok",
  "message": "service is alive",
  "data": {"status": "live"}
}
```

- **错误码**：进程无法响应时由 HTTP/容器层判定；接口本身不返回内部异常详情。
- **分页 / 筛选 / 排序**：不适用。
- **关键状态流转 / 幂等**：只读、幂等。

### GET `/api/v1/health/ready/`

- **用途 / 权限**：无认证 readiness，依次检查必要配置、数据库连接和 Django 已安装应用是否存在未应用迁移；不执行迁移，不检查 Jenkins。
- **请求参数**：无。
- **成功响应**：HTTP 200。

```json
{
  "code": "ok",
  "message": "service is ready",
  "data": {
    "status": "ready",
    "checks": {
      "configuration": "valid",
      "database": "available",
      "schema": "ready"
    }
  }
}
```

- **错误响应**：HTTP 503。

```json
{
  "code": "service_not_ready",
  "message": "service is not ready",
  "data": {
    "status": "not_ready",
    "failed_check": "database",
    "reason_code": "database_unavailable",
    "checks": {
      "configuration": "valid",
      "database": "unavailable",
      "schema": "unknown"
    }
  }
}
```

| HTTP | 业务码 | 安全原因码 | 含义 | 触发条件 |
| --- | --- | --- | --- | --- |
| 503 | `service_not_ready` | `configuration_invalid` | 必要配置无效 | 必填配置缺失或格式非法；不返回配置值 |
| 503 | `service_not_ready` | `database_unavailable` | 数据库不可连接 | 连接失败、超时或认证失败；不返回连接串 |
| 503 | `service_not_ready` | `schema_not_ready` | 数据库 schema 未就绪 | 使用 Django `MigrationExecutor` 计算后仍存在未应用 migration |

- **安全约束**：不返回数据库主机、端口、库名、账号、异常堆栈、migration 名称或 SQL；未执行的后续检查返回 `unknown`。
- **关键状态流转 / 幂等**：只读、幂等。

### Jenkins 环境 Job 契约

- **推荐 Job 名**：`AiApiTest-DWP-Platform-Bootstrap`。
- **Pipeline script path**：`jenkins/Jenkinsfile.platform-bootstrap`。
- **创建方式**：本地 Compose Jenkins 启动时由 `jenkins/scripts/configure-local-mounted-jobs.groovy` 幂等创建或修复；固定 `LOCAL_WORKSPACE_REPO=true`、无 cron。
- **并发策略**：禁止并发构建。

| 参数 | 类型 | 默认 | 含义 |
| --- | --- | --- | --- |
| `build_all` | boolean | `true` | true：缓存重建全部应用镜像并强制重建应用容器；false：增量处理缺失或变化服务 |
| `run_full_tests` | boolean | `false` | false：固定无凭据冒烟；true：平台自身全量回归 |

全量测试执行载体固定如下：

| 测试集合 | 执行镜像/target | 依赖准备时机 | 运行时禁止事项 |
| --- | --- | --- | --- |
| backend pytest | 已验证 backend 镜像 | backend 镜像构建阶段 | 禁止运行时 pip install |
| frontend Vitest/build | frontend test target | frontend 单次受控构建中的共享 npm 依赖层 | 禁止运行时 npm install/npm ci |
| frontend Playwright | frontend Playwright test target，浏览器版本与 package lock 匹配 | 镜像构建阶段预装浏览器 | 禁止运行时 `npx playwright install` |
| api-test 工具/协议测试 | 已验证 api-runner 镜像 | api-runner 镜像构建阶段 | 禁止创建 venv 或 pip install |
| Jenkins/Docker 静态测试 | 已验证 api-runner 镜像 | api-runner 镜像构建阶段 | 禁止使用 Jenkins controller Python |

- **阶段顺序**：Checkout/Workspace -> Bootstrap Preflight -> Dependency Assurance -> Deploy -> Health -> Tests -> Archive & Summary。
- **结果语义**：关键阶段失败则 Jenkins build 为 FAILURE；Allure 插件发布失败只告警，原始报告仍归档。
- **业务 Job 前置语义**：api-runner 镜像缺失或 label 与当前仓库不匹配时返回 `API_RUNNER_IMAGE_NOT_READY`，引导先运行本环境 Job；业务 Job 不自行修复依赖。
- **runner 产物交接**：业务 Job 使用可追踪名称创建 runner 容器，执行后在 `finally` 中 `docker cp` 标准产物到当前 Jenkins workspace；导出成功后删除 runner，导出失败则保留 runner 并返回 `RUNNER_ARTIFACT_EXPORT_FAILED`。

### AI helper 契约

```text
scripts/trigger-platform-bootstrap.ps1 -BuildAll {true|false} -RunFullTests {true|false}
scripts/trigger-platform-bootstrap.sh --build-all {true|false} --run-full-tests {true|false}
```

- helper 读取根私有 `.env` 中 Jenkins URL、Job 名和认证信息；真实凭据不进入命令行参数或日志。
- helper 触发参数化构建、跟踪 queue/build、轮询终态并输出 build URL、状态、结构化错误码和证据入口。
- helper 不直接调用 Docker、pip、npm 或应用进程命令。

---

## §8 UI 字段级规格与实现范围冻结

本需求不新增平台 Vue 页面。交互只发生在 Jenkins 与命令行 helper，UI 阶段仍需输出范围冻结说明。

| 区域 | 处理方式 | 字段/内容 | 状态与反馈 |
| --- | --- | --- | --- |
| R1 Jenkins 参数页 | Jenkins 原生页面直接展示 | `build_all`、`run_full_tests` | 默认值分别为 true/false |
| R2 Jenkins Console | Jenkins 原生页面直接展示 | stage、依赖状态、诊断块、脱敏日志 | 成功/失败均可检索固定错误码 |
| R3 Build Summary | Jenkins 构建摘要 | 服务地址、首要失败、错误码、证据、rerun | 成功显示入口；失败显示修复和重建指引 |
| R4 Allure | Jenkins 插件/归档页面 | 当前 build 测试报告 | 插件失败只告警，归档仍可下载 |
| R5 平台 Vue 页面 | 不实现 | 无新增 DOM、路由、按钮或说明文字 | 既有页面保持不变 |
| R6 设计标注层 | 仅设计说明不实现 | Docker Socket 风险、阶段关系、错误码解释 | 不进入产品 DOM 或 Playwright 页面断言 |

前端实现范围映射：`front-end/src` 不新增业务页面；仅新增容器构建、Nginx 配置、健康/代理验证和必要测试配置。

---

## §9 架构影响评估

| 维度 | 是否影响 | 影响说明与应对 |
| --- | --- | --- |
| 模块边界 | 是 | Jenkins 继续只编排；环境逻辑下沉到可测试脚本/Dockerfile；DRF 只新增健康 API；api-test 执行协议仍归 `api-test` |
| 数据模型 | 否 | 不新增表、不迁移；ready 只读检查既有数据库/schema |
| 权限 | 是 | Docker Socket 赋予 Jenkins 主机级 Docker 控制能力，只允许受信任本地 Jenkins；健康 API 无认证但不泄露详情 |
| Jenkins 执行链路 | 是 | 新增独立环境 Jenkinsfile、参数、阶段、helper 和归档契约；现有通用/Daily/重试 Job 改用已验证 api-runner 镜像，移除动态 venv/pip 安装 |
| `api-test` 执行协议 | 是（仅载体） | `tools/ci_runner.py` 参数、重试和产物协议不变；执行载体统一为 api-runner 镜像，业务 Job 不再准备依赖 |
| 报告 / Allure 协议 | 是 | 环境 Job 生成本 build 报告并继续复用 Jenkins 插件/归档；不新增报告服务 |
| Docker Compose 部署 | 是 | 从 MySQL/Jenkins 扩展到 backend/frontend/worker/api-runner；增加健康检查、镜像和 Docker Socket |
| 安全 | 是 | 需要 Docker Socket 风险说明、helper 凭据脱敏、日志敏感扫描和受信任 Job 限制 |
| Vue 前端 | 是（部署） | 业务页面不变；新增多阶段镜像、Nginx SPA/代理/健康配置 |
| DRF 后端 | 是 | 新增镜像、gunicorn 运行入口、live/ready API；不执行 migration |

API/Pipeline 契约冻结结论：DRF 新增两个只读健康接口；Jenkins 新增独立参数化环境 Job；现有业务 Job 统一改用 api-runner 镜像；业务 API 和 `api-test` 参数/重试/产物协议不变。

---

## §10 容器化兼容检查

| 检查项 | 是否存在 | 整改方案 |
| --- | --- | --- |
| 本机绝对路径 | 是，现有本地 workspace 挂载可配置 | 继续使用 `PROJECT_WORKSPACE`/`AIAPITEST_LOCAL_WORKSPACE`，Pipeline 和镜像只引用仓库相对路径 |
| 宿主机固定端口 | 否（设计要求） | MySQL/Jenkins/backend/frontend 对外端口和公开 URL均由根 `.env` 注入；容器间使用服务名 |
| 真实凭据 | 否（设计要求） | 仅根私有 `.env`/Jenkins Credentials 保存；`.env.example` 只列通用网络变量；日志脱敏 |
| 不可迁移业务常量 | 否 | 服务名、Job 推荐名和固定默认值由代码维护；地址/端口不写死个人环境 |
| Jenkins bootstrap 配置依赖 | 是，主人已确认 | 主人启动 MySQL/Jenkins bootstrap；版本化 init Groovy 自动创建/修复 Job，文档提供 script path、参数、并发和工具镜像配置验收清单 |
| Docker Socket 高权限 | 是 | 仅受信任本地 Jenkins；不得运行不受信任 SCM/PR；部署文档显式告警，不视为生产方案 |
| Docker Socket 组权限 | 是 | Compose 使用 `group_add` 注入 `DOCKER_GID`；Linux 按 `stat` 获取实际 GID，Windows Docker Desktop 使用兼容默认值；禁止 `chmod 666` |
| 不可重建运行状态 | 否 | MySQL/Jenkins/报告数据使用 volume；应用镜像和容器可重建；依赖不写入宿主机 |

新增或调整的通用网络配置必须同步 `.env.example`。相对 Stage13 前的 32 项公开配置，当前模板为 40 项，新增项共 8 个：

- `JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME`：固定环境 Job 名。
- `JENKINS_SYNC_HEARTBEAT_MAX_AGE_SECONDS`：同步 worker 心跳最大年龄。
- `DOCKER_GID`：Docker Socket 的宿主机组 ID；属于部署权限配置，不包含凭据。
- `BACKEND_BIND_HOST`、`BACKEND_HOST_PORT`：backend 容器公开映射。
- `FRONTEND_BIND_HOST`、`FRONTEND_HOST_PORT`：frontend 容器公开映射。
- `FRONTEND_PLAYWRIGHT_BASE_IMAGE`：frontend 构建与测试 target 使用的 Playwright 基础镜像。

既有 `BACKEND_SERVICE_URL`、`BACKEND_API_BASE_URL` 和 `FRONTEND_SERVICE_URL` 继续作为公开服务地址配置。

敏感项继续只存在私有 `.env`：Jenkins 用户名/API Token、数据库密码、Django 密钥、私有验收账号。

Compose 文件必须使用顶层固定 `name: aiapitest-dwp`，保证本地挂载和远端 SCM workspace 均操作同一 Compose project；该名称为代码级部署身份，不由 `.env` 随意覆盖。

启动后不建议修改：MySQL/Jenkins volume、MySQL 数据库私有配置、Jenkins 公共 URL、Job 名、Compose project name 和 Docker Socket 挂载/GID 策略；修改前必须评估历史链接、helper 配置和重建影响。

---

## §11 非功能要求

- **性能**：无变化增量构建应主要完成检查和健康验证；全量构建允许复用 Docker layer cache。健康轮询和测试必须有有限超时。
- **安全**：不记录真实凭据；健康 API 不返回内部地址/异常；Docker Socket 仅限受信任本地 Jenkins；禁止不受信任 Job 使用该 controller。
- **可用性**：bootstrap/依赖失败不改变应用服务；部署后失败保留现场；不自动回滚或停服。
- **兼容性**：Pipeline 继续使用 `isUnix()` 兼容 Windows/Linux Jenkins 节点；应用容器统一使用 Linux 镜像和 Compose 服务名通信。
- **可观测性**：固定 stage、固定错误码、结构化诊断块、依赖域汇总、Compose 状态、容器日志、测试证据和 build summary。
- **可维护性**：复杂逻辑放入可单测脚本，Jenkins Groovy 只负责编排；Dockerfile 依赖层由清单驱动。
- **幂等性**：重复全量构建重建应用但保留数据；重复增量构建在无变化时不重建健康服务。
- **数据保护**：任何自动流程不得执行 `down -v`、删除命名 volume 或清理未超期历史报告。

---

## §12 验收口径汇总

| AC 编号 | 验收点摘要 | 关联功能 |
| --- | --- | --- |
| `AC-S13-1.1~1.6` | bootstrap 检查、MySQL/Jenkins边界、Socket 权限和可操作诊断 | F1 |
| `AC-S13-2.1~2.9` | 三域依赖/构建输入、每域一次安装构建、业务 Job runner/源码门禁 | F2 |
| `AC-S13-3.1~3.6` | 全量/增量部署、固定 Compose project、基础服务不变、卷保留 | F3 |
| `AC-S13-4.1~4.9` | live/ready 子码、前端代理、worker 心跳、不可变镜像冒烟/全量 | F4 |
| `AC-S13-5.1~5.7` | 构建摘要、地址、Allure、runner 产物回传、失败证据和脱敏 | F5 |
| `AC-S13-6.1~6.5` | AI helper、Jenkins API、禁止旁路和手工兼容 | F6 |

最终验收必须包含：

1. 后端健康 API RED/GREEN、后端全量 pytest 与覆盖率证据。
2. Jenkins/Pipeline/Compose/helper 静态和单元测试 RED/GREEN 证据。
3. frontend Nginx、SPA、代理、健康、单测、构建和 Playwright 证据。
4. api-runner 工具/执行协议测试与依赖镜像完整性证据。
5. 真实 Jenkins `build_all=true` 构建：应用容器 ID 更新，MySQL/Jenkins ID 不变。
6. 真实 Jenkins `build_all=false` 无变化构建：应用容器不重建。
7. MySQL 未启动、依赖构建失败、健康超时等受控失败证据，证明日志详细且可指导重新构建。
8. 默认冒烟和 `run_full_tests=true` 平台全量回归证据。
9. AI helper 真实触发/轮询、认证失败脱敏和 busy/超时测试证据。
10. 独立 review subagent 无未闭环 Critical/Important。
11. RTM 逐条覆盖全部 42 条 AC，验收包聚合所有证据链接。

---

## §13 变更记录

| 日期 | 版本 | 变更内容 | 原因 |
| --- | --- | --- | --- |
| 2026-07-12 | 0.1 | 建立 L 级需求，完成现有 Jenkins/Docker/服务/依赖入口盘点 | 主人提出统一环境 Pipeline 新需求 |
| 2026-07-13 | 0.2 | 闭环 14 项关键裁决，批准架构、Pipeline、错误日志、测试和安全设计 | 需求澄清与分段设计确认完成 |
| 2026-07-13 | 0.3 | 补齐业务 Job api-runner 唯一依赖入口、固定 Compose project、Docker GID、ready 安全子码和全量测试镜像载体 | 独立规格审查 1 Critical / 4 Important 闭环 |
| 2026-07-13 | 0.4 | 冻结 runner 镜像内源码与 `docker cp` 产物回传协议，回传失败保留容器现场 | 独立规格复审新增 1 Important 闭环 |
| 2026-07-13 | 0.5 | 回写冻结前已批准的 `DEPLOY_SERVICE_FAILED` 错误码 | 测试设计审查发现正式规格遗漏已批准值 |
| 2026-07-15 | 0.6 | 记录 Platform Bootstrap Job 由 init Groovy 自动创建/修复的最终裁决，以及 Build #23 全量 Smoke、Build #24 增量全量验收结果 | 首轮 Jenkins 现场验收与最终独立审查闭环 |

---

## §14 冻结确认（主人签字门禁）

- [x] §0 待澄清清单全部闭环
- [x] §9 架构影响评估已完成
- [x] §7 API/Pipeline 契约完整、可冻结
- [x] §10 容器化兼容检查完成
- [x] §4 每个功能点均有可测 Given-When-Then 验收标准
- [x] 主人已复核本书面规格并确认冻结

**方案方向批准人（主人）**：主人　　**批准日期**：2026-07-13

**书面规格冻结人（主人）**：主人　　**冻结日期**：2026-07-13

> 主人确认“冻结通过”后，文档状态改为“已冻结”，下游功能测试、UI 范围说明、后端/Jenkins/Docker/前端 TDD、独立审查和真实验收自动连续推进。
>
> 后续如遇本文件未覆盖的关键决策，必须按熔断协议暂停上报并回写 §0/§13，禁止自行脑补。
