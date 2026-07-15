# 平台环境准备-Jenkins统一平台环境启动流水线-验收包

## 1. 需求概览

| 项 | 内容 |
| --- | --- |
| 需求名 | 平台环境准备-Jenkins统一平台环境启动流水线 |
| 需求分级 | L |
| 关联模块 | api-test / back-end / front-end / jenkins / docker / AGENTS |
| 需求冻结日期 | 2026-07-13 |
| 本包状态 | Task 1-6 已聚合；最终独立审查已收口为 0 Critical / 0 Important / 0 Minor；Build #23 全量重建默认 Smoke 与 Build #24 增量全量回归均成功 |

## 2. 逐条验收结论

- 42 条 AC 的实现位置、自动化测试和受控故障验证已回写到 RTM；最终真实成功链由 Build #23（全量重建默认 Smoke）与 Build #24（增量全量回归）验证，Build #22 保留 helper 真实触发证据。
- 主表以 `../Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-可追溯矩阵.md` 为准；基础服务故障、依赖失败和超时等破坏性分支仍坚持受控测试，不以停止主人服务制造证据。

## 3. 测试证据索引

| 阶段 | 必需证据 | 当前状态 |
| --- | --- | --- |
| 后端 Task 1 | 健康 API/worker RED、GREEN、全量 pytest、覆盖率 | 已提交 Stage13 健康实现与测试；Jenkins Build #24 artifact：后端 `230 passed / 91%` |
| Docker/前端 Task 2 | Compose 静态 RED/GREEN、镜像构建、Nginx/容器健康 | 已提交 Stage13 Compose、Dockerfile、Nginx 与静态测试；Jenkins Build #23/#24 artifact 完成镜像、Nginx、容器健康验证 |
| Pipeline/helper Task 3 | 参数、依赖、错误日志、helper RED/GREEN | 已提交 Stage13 Pipeline/helper 与自动化测试；Jenkins Build #22 artifact 验证 helper 真实触发成功 |
| 业务 runner Task 4 | 无动态安装、label 门禁、docker cp 产物回传 | 已提交 Stage13 runner 实现、测试与说明；Jenkins Build #24 artifact 验证全量回归、Allure 与归档 |
| 文档门禁 Task 5 | AGENTS/.env/文档静态测试 | 已提交 Stage13 AGENTS、环境模板、部署文档与静态门禁；Jenkins Build #24 artifact 验证全量回归通过 |
| 静态验收 Task 6 | 回归、语法、Compose config、安全与产物审计 | 已提交 Stage13 静态测试与验收资料；最终运行归档见下方 Jenkins Build artifact 索引 |
| 真实 Jenkins 验收 Task 6 | build_all true/false、冒烟/全量、Allure、helper | Jenkins Build #23 artifact：`build_all=true/run_full_tests=false` 全量重建默认 Smoke 成功；Jenkins Build #24 artifact：`build_all=false/run_full_tests=true` 增量全量成功，后端 `230 passed / 91%`；Jenkins Build #22 artifact：helper 增量冒烟成功 |

### Jenkins Build artifact 索引

- Jenkins Build #22 artifact：PowerShell helper 真实触发、queue/build 轮询、增量部署与默认 Smoke 成功。
- Jenkins Build #23 artifact：`build_all=true` 全量重建、应用服务健康检查与默认 Smoke 成功。
- Jenkins Build #24 artifact：`build_all=false` 增量复用、全量测试、Summary、Allure 与归档成功；后端 `230 passed / 91%`。

## 4. 一致性报告

- RTM：`../Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-可追溯矩阵.md`。
- UI 映射：`../../UI/Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-UI区域语义拆解与实现范围映射.md`。
- 当前结果：42 条 AC 与 62 条 TC 双向无遗漏/孤儿；Docker CLI/Compose/daemon/Socket 四类预检故障只断言结构化 code 稳定、非空、彼此可区分，并保留退出码/证据/建议/不部署；Build #23/#24 已验证成功状态机、全量/增量、地址、归档和全量测试，Build #22 已验证 helper 路径。

### UI 覆盖校准结论

| 分类 | 验收校准结论 |
| --- | --- |
| 正常 | 手工/AI 触发、七阶段成功链、Summary 与 Allure 已映射到 R1-R4 外部系统页面。 |
| 异常 | 预检、依赖、部署、健康、helper、Allure 和 runner 导出失败均落在 R2-R4 的诊断/证据面，不进入 Vue 页面。 |
| 边界 | 增量幂等、一次构建、有限超时、Job URL 编码、local-mounted/SCM 已覆盖，不新增 Vue route 或控件。 |
| 权限 | Jenkins 原生权限控制 R1-R4；普通平台用户无环境 Job 配置入口；Docker Socket 仅限受信任本地 Jenkins。 |
| 安全 | 脱敏、Docker GID、禁止 `chmod 666`/`down -v`/宿主机动态安装已覆盖；R6 标注不进入日志或 DOM。 |
| DOM 范围 | R1-R4 为外部页面，R5 明确不实现，R6 为设计标注层；R1-R6 均不进入 `front-end/src` 新 DOM、产品截图或 Playwright 页面断言。 |

## 5. 实现摘要（待填）

- 后端：`common/health.py`、`metrics/management/commands/sync_jenkins_results.py` 与 Stage13 health/heartbeat pytest；Task 1 独立审查闭环。
- Docker/前端：Dockerfile、Nginx、Compose、不可变镜像标签与静态测试；Task 2 独立审查通过。
- Jenkins/helper：`jenkins/scripts/platform_bootstrap/`、`Jenkinsfile.platform-bootstrap`、两个 trigger wrapper，以及 `api_runner_lifecycle.py` / `api_runner_cli.py`；Task 3、Task 4 独立审查通过。
- 文档与 AI 门禁：根及五个模块 `AGENTS.md`、`.env.example`、`docker/DEPLOYMENT.md`、`jenkins/README.md`、`README.md` 和 `docs/自主开发流水线.md`；Task 5 最终独立审查通过。
- Task 6 回归：已提交的 Stage13 静态测试覆盖后端、Jenkins、api-test 与前端；最终真实构建结果及后端 `230 passed / 91%` 以 Jenkins Build #24 artifact 为准。
- 真实 Jenkins：Jenkins Build #23 artifact 验证全量重建默认冒烟、Jenkins Build #24 artifact 验证增量全量、Jenkins Build #22 artifact 验证 helper 增量冒烟；Summary/Allure/artifact 均由 Jenkins Build 归档。
- 独立对抗审查：Task 1-6 已闭环；最终修复复审为 0 Critical / 0 Important / 0 Minor。

## 6. 待主人确认项

| 编号 | 事项 | agent 的处理 | 需主人确认 |
| --- | --- | --- | --- |
| 暂无 | 冻结规格目前无遗留裁决 | 按自主流水线连续推进 | 否 |

## 7. 已知限制 / 后续项

- Docker Socket 方案仅面向受信任本地 Jenkins，不是生产安全部署承诺。
- 环境 Job 由本地 Compose Jenkins 启动时的版本化 init Groovy 幂等创建或修复；仓库不允许创建第二条环境旁路 Job。
- Jenkins/MySQL 基础容器由主人启动的边界已验证；环境 Job 仅检查它们并保持其 ID，不管理生命周期。
- 前端 Vitest、build、Playwright 已完成实际回归；构建 warning 来自第三方 PURE annotation 和现有 chunk size，未新增 Stage13 warning。
- 已跟踪和本次生成的本地 evidence 目录、根临时文件与临时目录均已清理，`.gitignore` 已统一忽略运行证据。

## 验收结论（主人签字）

- [ ] 全部 AC 达成
- [ ] 测试证据充分可信
- [ ] RTM 无漂移
- [ ] 待确认项已逐条裁决

**验收人（主人）**：`__________`　**日期**：`__________`　**结论**：`通过 / 打回（附原因）`
