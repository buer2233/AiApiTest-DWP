# 平台环境准备-Jenkins统一平台环境启动流水线-功能测试用例

## 1. 概览

| 项 | 内容 |
| --- | --- |
| 需求来源 | `../../demand/Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-需求说明.md` |
| 需求分级 | L |
| 覆盖范围 | F1-F6、42 条 AC；bootstrap、依赖、部署、健康、测试、归档、AI helper |
| 测试平台 | Windows Docker Desktop 与 Linux Docker Engine；本地挂载 Jenkins 与远端 SCM Job |
| 安全基线 | 不使用真实凭据；敏感值统一为占位符；禁止 `down -v` 和宿主机动态安装 |
| UI 范围映射 | `../../UI/Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-UI区域语义拆解与实现范围映射.md` |

## 2. 公共前置条件与测试数据

- `P0` 用例阻断核心一键启动、安全或数据保留；`P1` 覆盖重要异常与跨平台；`P2` 覆盖兼容和提示质量。
- 私有 `.env` 使用脱敏值，公开 URL/端口来自 `.env.example` 对应变量。
- 基础容器名为 `aiapitest-mysql`、`aiapitest-jenkins`；固定 Compose project 为 `aiapitest-dwp`。
- Jenkins 启动 init Groovy 幂等创建或修复推荐环境 Job `AiApiTest-DWP-Platform-Bootstrap`，参数 `build_all=true`、`run_full_tests=false`。
- 每条用例执行前记录 MySQL/Jenkins/应用容器 ID；测试后按预期确认是否保持或变化。
- 失败用例仅使用受控无敏感测试输入；不得删除命名 volume 或修改真实业务数据。

## 3. F1 Bootstrap 前置检查与诊断

| 用例编号 | AC | 优先级 | 测试目标 | 前置条件 / 测试数据 | 操作步骤 | 预期结果 / 后置条件 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S13-F1-001` | `AC-S13-1.1` | P0 | `.env` 缺失时阻断且不部署 | 临时 workspace 无根 `.env`；应用容器状态已记录 | 触发环境 Job；查看 Preflight、Summary、artifact | 构建以 `CONFIG_ENV_MISSING` 失败；指出 `.env.example` 和重新构建步骤；无镜像安装/应用容器变化 |
| `TC-S13-F1-002` | `AC-S13-1.2` | P0 | 区分 Docker CLI/Compose/daemon/Socket 故障 | 分别模拟命令不存在、Compose 不可用、daemon 不可达、Socket 未挂载；每类场景重复执行两次 | 四类分别执行 Preflight | 每类返回稳定且非空的结构化 code，同类重复执行 code 一致，四类 code 彼此可区分；均含原始命令退出码、证据和修复建议；不进入依赖构建或应用部署；不在测试阶段新增未冻结公共枚举 |
| `TC-S13-F1-003` | `AC-S13-1.3` | P0 | 当前 Job 不管理 Jenkins controller | Jenkins 正在执行 Job，记录 controller ID | 执行 `build_all=true` 至完成 | Jenkins 只被检查；无 stop/restart/recreate 命令；controller ID 不变 |
| `TC-S13-F1-004` | `AC-S13-1.4` | P0 | MySQL 未运行时给出可操作指引 | 受控测试环境中 MySQL 容器为 stopped；不得删除 volume | 触发 Job | `BOOTSTRAP_MYSQL_NOT_RUNNING`；日志指导用户手工启动并等待 healthy 后 rerun；Pipeline 不启动 MySQL、不部署应用 |
| `TC-S13-F1-005` | `AC-S13-1.5` | P0 | MySQL unhealthy 时保留现场 | MySQL running 但 health 为 unhealthy | 触发 Job并查看归档 | `BOOTSTRAP_MYSQL_UNHEALTHY`；归档 ps 和脱敏 MySQL 日志；不重启 MySQL；给出排查与 rerun 指引 |
| `TC-S13-F1-006` | `AC-S13-1.6` | P0 | Docker Socket GID 权限诊断 | Socket 已挂载；Jenkins supplemental group 不匹配 | 触发 Job | `DOCKER_SOCKET_PERMISSION_DENIED`；提示配置实际 `DOCKER_GID` 并由用户重建 Jenkins；不建议 `chmod 666` |

## 4. F2 不可变镜像依赖与业务 runner

| 用例编号 | AC | 优先级 | 测试目标 | 前置条件 / 测试数据 | 操作步骤 | 预期结果 / 后置条件 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S13-F2-001` | `AC-S13-2.1` | P0 | 无变化增量复用三域镜像 | backend/frontend/api-runner 的依赖和构建输入 hash 均匹配 | 以 `build_all=false` 执行 Dependency Assurance | 三域依赖=`SATISFIED`、镜像=`REUSED`；无 build/install 命令 |
| `TC-S13-F2-002` | `AC-S13-2.2` | P0 | backend 清单变化只安装一次 | 修改受控 requirements 输入，现有 label 不匹配 | 执行环境 Job并统计 build 调用 | backend 仅一次受保护构建；成功为 `INSTALL_SUCCESS`；记录新 hash 和完整日志 |
| `TC-S13-F2-003` | `AC-S13-2.3` | P0 | 多域失败仍聚合且各一次 | 让 frontend、api-runner 构建分别稳定失败 | 执行 Job | 两域各只尝试一次；分别 `INSTALL_FAILED` 和诊断块；backend 仍完成检查；最终统一失败 |
| `TC-S13-F2-004` | `AC-S13-2.4` | P0 | 依赖失败不改变应用服务 | 记录已有应用容器 ID；制造任一域失败 | 执行 Job | Deployment stage 未运行；所有现有应用容器 ID/状态不变；依赖日志归档 |
| `TC-S13-F2-005` | `AC-S13-2.5` | P1 | 全量构建复用 Docker cache | 三域镜像已存在且依赖未变 | `build_all=true` 执行 | 三域各执行一次构建；命令无 `--no-cache`；依赖层允许 cache hit；结果可审计 |
| `TC-S13-F2-006` | `AC-S13-2.6` | P0 | 源码变化触发构建但不误报安装 | 仅修改某域源码/Dockerfile，依赖清单不变 | `build_all=false` 执行 | 对应镜像一次 `BUILD_SUCCESS`；依赖仍为 `SATISFIED`；其他域复用 |
| `TC-S13-F2-007` | `AC-S13-2.7` | P0 | 业务 Pipeline 无动态安装旁路 | 读取通用、Daily、模块重试、失败重试脚本 | 执行静态测试 | 不含 venv、pip install、install_missing_requirements；只在 api-runner 中调用 ci_runner |
| `TC-S13-F2-008` | `AC-S13-2.8` | P0 | runner 未准备时业务 Job 明确失败 | api-runner 缺失或 label/hash 不匹配 | 触发任一业务 Job | 用例执行前 `API_RUNNER_IMAGE_NOT_READY`；引导先跑环境 Job；无临时安装 |
| `TC-S13-F2-009` | `AC-S13-2.9` | P0 | local/SCM 均使用镜像内源码 | 分别使用 local-mounted 与 SCM Job | 触发业务 Job并检查 docker create/run 参数 | runner label 与当前仓库匹配；使用镜像内源码；无 Jenkins workspace bind mount |

## 5. F3 全量/增量应用部署

| 用例编号 | AC | 优先级 | 测试目标 | 前置条件 / 测试数据 | 操作步骤 | 预期结果 / 后置条件 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S13-F3-001` | `AC-S13-3.1` | P0 | 全量只重建应用服务 | MySQL/Jenkins/backend/frontend/worker 均运行，记录 ID | `build_all=true` 构建 | backend/frontend/worker ID 更新；MySQL/Jenkins ID 不变；volume 保留 |
| `TC-S13-F3-002` | `AC-S13-3.2` | P0 | 无变化增量不重建 | 所有应用健康且 hash/config 不变 | `build_all=false` 构建 | 应用容器 ID 不变；仅执行检查、健康和测试 |
| `TC-S13-F3-003` | `AC-S13-3.3` | P0 | 增量恢复缺失或停止服务 | 分别移除一个应用容器、停止另一个；其余健康 | `build_all=false` 构建 | 只创建/启动必要服务；无关健康服务不重建 |
| `TC-S13-F3-004` | `AC-S13-3.4` | P0 | 部署失败保留现场 | 制造端口冲突或无效应用配置 | 执行部署 | `DEPLOY_SERVICE_FAILED`；构建失败；归档 Compose 状态/日志；不回滚、不停服 |
| `TC-S13-F3-005` | `AC-S13-3.5` | P0 | 禁止删除卷或管理 bootstrap | 静态扫描 Jenkins/Compose/helper/文档 | 执行安全门禁 | 无 `down -v`、MySQL/Jenkins recreate、命名 volume 删除；发现即测试失败 |
| `TC-S13-F3-006` | `AC-S13-3.6` | P0 | 固定 Compose project 跨 workspace 一致 | local-mounted 与不同目录名 SCM workspace | 分别执行环境 Job | 均命中 `aiapitest-dwp` 同一容器集合；不创建第二套服务/网络/volume |

## 6. F4 健康、冒烟与全量回归

| 用例编号 | AC | 优先级 | 测试目标 | 前置条件 / 测试数据 | 操作步骤 | 预期结果 / 后置条件 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S13-F4-001` | `AC-S13-4.1` | P0 | live 只验证 DRF 存活 | DB/Jenkins 检查函数设置为不可调用哨兵 | GET `/api/v1/health/live/` | 200，`code=ok`、`status=live`；不访问 DB/Jenkins；无敏感字段 |
| `TC-S13-F4-002` | `AC-S13-4.2` | P0 | ready 成功与 schema 门禁 | 配置有效、DB 可用、MigrationExecutor plan 为空 | GET `/api/v1/health/ready/` | 200；三个 checks 为 valid/available/ready；不执行 migration |
| `TC-S13-F4-003` | `AC-S13-4.3` | P0 | Nginx SPA 和 `/api` 代理 | frontend/backend 容器健康 | 请求 Nginx 配置声明的健康入口、现有 SPA route、代理 ready | 均 2xx；SPA fallback 正确；`/api` 指向 Compose backend，不泄露内部地址 |
| `TC-S13-F4-004` | `AC-S13-4.4` | P0 | worker 心跳新鲜度 | watch worker 成功完成 cycle，随后模拟心跳过期 | 检查容器 health | 新鲜时 healthy；过期时 `HEALTH_WORKER_STALE`；写入失败使 worker 非零退出 |
| `TC-S13-F4-005` | `AC-S13-4.5` | P0 | 默认冒烟无账号依赖 | `run_full_tests=false`，未提供验收账号 | 执行 Job | 只跑固定基础/跨服务冒烟；不读取登录账号；通过后输出证据 |
| `TC-S13-F4-006` | `AC-S13-4.6` | P0 | 平台全量范围正确 | `run_full_tests=true` | 执行 Job并记录测试清单 | 包含后端、前端、Jenkins/Docker、api-test 工具/协议；排除外部业务 test_case 全量 |
| `TC-S13-F4-007` | `AC-S13-4.7` | P0 | 健康/测试失败不停止服务 | 制造 ready 超时或测试失败，记录容器 ID | 执行 Job | Jenkins build FAILURE；服务继续运行且 ID 保留；诊断与测试证据归档 |
| `TC-S13-F4-008` | `AC-S13-4.8` | P0 | ready 三类安全原因码 | 分别模拟配置非法、DB 不可达、未应用 migration | 三次请求 ready | 503；reason_code 分别准确；后续未执行检查为 unknown；无地址/凭据/SQL/migration 名 |
| `TC-S13-F4-009` | `AC-S13-4.9` | P0 | 全量测试只用不可变载体 | 检查实际测试命令与镜像构建日志 | `run_full_tests=true` 执行 | backend/frontend-test/api-runner 执行；浏览器预装；运行期无 pip/npm/npx 安装 |

## 7. F5 构建摘要、地址、Allure 与产物

| 用例编号 | AC | 优先级 | 测试目标 | 前置条件 / 测试数据 | 操作步骤 | 预期结果 / 后置条件 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S13-F5-001` | `AC-S13-5.1` | P0 | 成功摘要输出全部入口 | `.env` 配置脱敏测试 URL；构建成功 | 查看 Build Summary | Jenkins、MySQL、frontend、backend、API docs、live/ready、Allure 均有标签和 URL |
| `TC-S13-F5-002` | `AC-S13-5.2` | P0 | 失败摘要可直接排查 | 制造一个明确预检/健康失败 | 查看 Summary | 首因、全部错误码、证据、修复步骤、rerun 均存在；非笼统提示 |
| `TC-S13-F5-003` | `AC-S13-5.3` | P1 | 多依赖失败逐域可追踪 | 两个依赖域失败 | 查看 Console/Summary/artifact | 每域独立状态、错误码和日志链接；汇总顺序稳定 |
| `TC-S13-F5-004` | `AC-S13-5.4` | P1 | Allure 插件失败只告警 | 禁用/模拟插件发布失败，原始报告存在 | 执行 post 阶段 | 插件错误只告警；allure-results/report 归档；基础设施成功不被改写 |
| `TC-S13-F5-005` | `AC-S13-5.5` | P0 | 全链路敏感信息脱敏 | 输入含密码/token/Cookie/Authorization 的受控值 | 执行失败与归档扫描 | 控制台和 artifacts 无明文；敏感值为 `***` 或被拒绝写入 |
| `TC-S13-F5-006` | `AC-S13-5.6` | P0 | runner 产物跨 workspace 回传 | local-mounted 与 SCM 各执行一次 runner | 等待 runner 结束、删除后检查 workspace | 五类标准产物通过 `docker cp` 落到 `api-test/runtime/ci-runs/{run_id}/`；容器删除后仍可归档 |
| `TC-S13-F5-007` | `AC-S13-5.7` | P0 | 测试失败仍导出；导出失败保留 runner | 场景A测试命令失败；场景B模拟 docker cp 失败 | 执行业务 Job | A finally 先导出再删容器；B `RUNNER_ARTIFACT_EXPORT_FAILED`、保留容器 ID/现场和人工导出指引 |

## 8. F6 AI helper 与唯一入口

| 用例编号 | AC | 优先级 | 测试目标 | 前置条件 / 测试数据 | 操作步骤 | 预期结果 / 后置条件 |
| --- | --- | --- | --- | --- | --- | --- |
| `TC-S13-F6-001` | `AC-S13-6.1` | P0 | helper 正确触发和轮询 | 私有 `.env` 含脱敏 Jenkins 配置；Job 可用 | PowerShell/Shell helper 分别传两参数 | 获取 queue/build URL；参数一致；轮询至终态；输出结构化结果 |
| `TC-S13-F6-002` | `AC-S13-6.2` | P0 | helper 错误分类和脱敏 | 分别模拟认证失败、Job 不存在、轮询超时 | 执行 helper | 三类故障分别返回可相互区分的固定结构化错误结果；均含脱敏原因、修复建议和非零退出；用户名/token 不出现在日志；不在测试阶段新增未冻结公共错误码 |
| `TC-S13-F6-003` | `AC-S13-6.3` | P0 | AI 只解释 Pipeline 失败 | Pipeline 返回结构化失败 artifact/摘要 | helper 结束并读取结果 | 向用户返回错误码、证据、rerun；不执行 Docker/pip/npm 旁路修复 |
| `TC-S13-F6-004` | `AC-S13-6.4` | P0 | AGENTS 与静态门禁禁止旁路 | 扫描根和相关模块规则、helper、Jenkinsfile | 执行静态测试 | 明确唯一入口；直接应用重启、宿主 pip/npm、`down -v` 被禁止；关键文件缺失即失败 |
| `TC-S13-F6-005` | `AC-S13-6.5` | P1 | 启动自动创建的 Job 与 helper 契约一致 | Jenkins 已由主人启动且 init Groovy 已创建/修复固定 Job | 确认 Job 名、Jenkinsfile、无 cron 和 `LOCAL_WORKSPACE_REPO=true`，再分别 UI 点击与 helper 触发相同参数 | 只有一个固定 Job；两者进入同一 Jenkinsfile、阶段和结果契约；Jenkins 重启后会幂等修复配置 |

## 9. 异常、边界、安全与并发扩展用例

| 用例编号 | 关联 AC | 优先级 | 场景与步骤 | 确定预期 |
| --- | --- | --- | --- | --- |
| `TC-S13-ERR-001` | `AC-S13-2.3` | P0 | 让 backend 镜像构建超过冻结超时 | 仅构建一次；依赖域为 `INSTALL_FAILED`；诊断块的 reason/observed/evidence 能明确识别超时并区别于网络、冲突和完整性故障；其余域继续检查 |
| `TC-S13-ERR-002` | `AC-S13-2.3` | P0 | 构建时模拟包仓库 DNS/网络不可达 | 仅构建一次；结构化诊断能明确识别网络不可达并与超时、依赖冲突和完整性故障区分；保留完整 build 日志和网络排查建议 |
| `TC-S13-ERR-003` | `AC-S13-2.3` | P0 | 分别制造 pip/npm 版本冲突和完整性检查失败 | 两类失败的 reason/observed/evidence 可相互区分且保留对应构建日志；每域不二次安装或构建；不部署；不在测试阶段新增未冻结公共枚举 |
| `TC-S13-BND-001` | `AC-S13-2.1`,`2.2` | P1 | requirements 为空、lock 文件缺失、image label 缺失分别执行 | 空清单/缺 lock 明确配置失败；缺 label 触发一次构建；均不静默 SATISFIED |
| `TC-S13-SEC-001` | `AC-S13-1.6`,`6.4` | P0 | 静态扫描 Docker/部署脚本含 `chmod 666 /var/run/docker.sock` | 安全门禁失败并指出 DOCKER_GID/group_add 替代方案 |
| `TC-S13-ERR-004` | `AC-S13-4.3`,`4.7` | P0 | backend 停止或 Nginx upstream 配错后请求 `/api` | 返回与配置、数据库、schema、心跳和超时故障可区分的代理健康失败诊断；结构包含 历史验证记录（suggestion/rerun；服务现场和，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档） Nginx 日志保留 |
| `TC-S13-BND-002` | `AC-S13-4.7` | P1 | 健康轮询超时配置为 0、负数、非数字和极大值 | 非法值回退安全默认并告警；所有轮询仍有有限上限，不无限等待 |
| `TC-S13-ERR-005` | `AC-S13-5.1`,`5.2` | P0 | 删除任一必需公开 URL/端口配置 | `CONFIG_REQUIRED_ENV_MISSING`；列出缺失键名但不显示值；不使用硬编码 localhost 回退 |
| `TC-S13-BND-003` | `AC-S13-5.1` | P1 | Jenkins Job 名含空格、中文或 folder 层级 | Summary/Allure URL 正确编码且可点击，不出现重复或丢失路径分隔 |
| `TC-S13-ERR-006` | `AC-S13-6.2` | P1 | helper 获得 queue URL 后 queue item 被 Jenkins 清理且未发现 build | 返回可与认证失败、Job 不存在、网络不可达、取消和超时区分的非零结构化结果，包含 queue URL 和重试建议；不猜测最新 build；不自行命名未冻结公共错误码 |
| `TC-S13-ERR-007` | `AC-S13-6.2` | P0 | helper 触发或轮询期间 Jenkins 网络不可达/5xx | 返回可与认证失败、Job 不存在、queue 丢失、取消和超时区分的非零结构化结果；凭据脱敏；已有 build 不被取消；不执行旁路修复 |
| `TC-S13-ST-007` | `AC-S13-6.2` | P1 | 用户在 Jenkins 取消运行中环境 build | helper 明确返回“构建已取消”终态和 build URL，与超时、失败和网络不可达状态可区分，不把取消误报为超时 |
| `TC-S13-CONC-001` | `AC-S13-6.2`,`6.5` | P0 | 环境 Job 已运行时再次通过 helper/UI 触发 | 第二次返回当前运行 build 或明确 busy/禁止并发结果；不启动第二个环境变更，不同时操作 Compose；不要求未冻结的具体 busy 枚举值 |
| `TC-S13-ERR-008` | `AC-S13-5.6`,`5.7` | P0 | `docker cp` 成功退出但缺少任一必需标准产物 | 产物完整性校验失败，按 `RUNNER_ARTIFACT_EXPORT_FAILED` 保留 runner，不生成虚假成功归档 |

## 10. 状态流转与组合回归

| 组合编号 | 优先级 | 状态路径 | 预期 |
| --- | --- | --- | --- |
| `TC-S13-ST-001` | P0 | queued -> preflight -> dependency_check -> deploy -> health -> tests -> success | 每阶段顺序固定，成功摘要/地址/证据完整 |
| `TC-S13-ST-002` | P0 | preflight -> failed | 无依赖构建和部署；bootstrap 容器不变 |
| `TC-S13-ST-003` | P0 | dependency_check -> install_failed -> failed | 其余域仍检查；无部署；聚合诊断完整 |
| `TC-S13-ST-004` | P0 | deploy/health/tests -> failed | 保留应用现场，不回滚、不停服，始终归档 |
| `TC-S13-ST-005` | P1 | runner test failed -> artifact export success -> runner removed | Jenkins 获得标准产物，业务测试失败状态与基础设施状态按既有协议处理 |
| `TC-S13-ST-006` | P0 | runner ended -> artifact export failed -> runner retained | 构建以基础设施错误失败，容器可供人工导出 |

## 11. UI 覆盖校准

- 校准来源：`../../UI/Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-UI区域语义拆解与实现范围映射.md`。

| 分类 | 功能测试覆盖校准结论 |
| --- | --- |
| 正常 | F1-F6 主用例和 `TC-S13-ST-001` 覆盖 R1 参数、R2 Console、R3 Summary、R4 Allure/Artifact 的正常链路；实际交互均在 Jenkins/Allure 外部页面。 |
| 异常 | `TC-S13-ERR-*` 与失败状态组合覆盖预检、依赖、部署、健康、helper、Allure 和 runner 导出异常；反馈落在 R2-R4，不复制进平台 Vue 页面。 |
| 边界 | `TC-S13-BND-*`、local-mounted/SCM、有限超时、URL 编码与无变化增量场景已校准；不新增 Vue route、组件或控件。 |
| 权限 | Jenkins 参数、Console、Summary、Allure 由 Jenkins 自身权限控制；普通平台用户不获得环境 Job 配置入口，Docker Socket 仅限受信任本地 Jenkins。 |
| 安全 | `TC-S13-SEC-001`、脱敏、禁止 `down -v`、禁止宿主机动态安装及 Docker Socket GID 边界已覆盖；R6 风险/错误码标注只属于设计资料。 |
| DOM 范围 | R1-R4 是外部系统页面，R5 明确不实现，R6 为设计标注层；R1-R6 均不得进入 `front-end/src` 新 DOM、截图或 Playwright 页面断言。 |

## 12. 覆盖自检

- 需求 AC：42 条。
- AC 主用例：42 条，一对一覆盖，无遗漏。
- 异常/边界/安全/并发扩展用例：14 条。
- 组合状态用例：6 条。
- 总用例：62 条。
- 每条扩展和组合用例均在 RTM 的扩展映射表中关联具体 AC 或需求 §5 状态机。
- UI 覆盖校准已完成：正常、异常、边界、权限、安全场景均与 R1-R6 对齐，且没有把 Jenkins/Allure/设计标注误实现为 Vue DOM。
