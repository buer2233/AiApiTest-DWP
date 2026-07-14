# 平台环境准备-Jenkins统一平台环境启动流水线-验收包

## 1. 需求概览

| 项 | 内容 |
| --- | --- |
| 需求名 | 平台环境准备-Jenkins统一平台环境启动流水线 |
| 需求分级 | L |
| 关联模块 | api-test / back-end / front-end / jenkins / docker / AGENTS |
| 需求冻结日期 | 2026-07-13 |
| 本包状态 | 骨架，待 Task 1-6 自动聚合证据 |

## 2. 逐条验收结论

- 42 条 AC 当前均为“待实现/待测”。
- 主表以 `../Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-可追溯矩阵.md` 为准；Task 6 将逐条回写结论和证据。

## 3. 测试证据索引（待填）

| 阶段 | 必需证据 | 当前状态 |
| --- | --- | --- |
| 后端 Task 1 | 健康 API/worker RED、GREEN、全量 pytest、覆盖率 | 待生成 |
| Docker/前端 Task 2 | Compose 静态 RED/GREEN、镜像构建、Nginx/容器健康 | 待生成 |
| Pipeline/helper Task 3 | 参数、依赖、错误日志、helper RED/GREEN | 待生成 |
| 业务 runner Task 4 | 无动态安装、label 门禁、docker cp 产物回传 | 待生成 |
| 文档门禁 Task 5 | AGENTS/.env/文档静态测试 | 待生成 |
| 真实验收 Task 6 | build_all true/false、失败诊断、冒烟/全量、Allure、helper | 待生成 |

## 4. 一致性报告

- RTM：`../Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-可追溯矩阵.md`。
- UI 映射：`../../UI/Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-UI区域语义拆解与实现范围映射.md`。
- 当前结果：42 条 AC 与 62 条 TC 双向无遗漏/孤儿；Docker CLI/Compose/daemon/Socket 四类预检故障只断言结构化 code 稳定、非空、彼此可区分，并保留退出码/证据/建议/不部署；其他未冻结故障同样只断言可区分语义和结构，不新增公共枚举；实现位置和验收状态待开发阶段补齐。

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

- 后端：待 Task 1。
- Docker/前端：待 Task 2。
- Jenkins/helper：待 Task 3/4。
- 文档与 AI 门禁：待 Task 5。
- 独立对抗审查：待每任务 reviewer 和最终 whole-branch review。

## 6. 待主人确认项

| 编号 | 事项 | agent 的处理 | 需主人确认 |
| --- | --- | --- | --- |
| 暂无 | 冻结规格目前无遗留裁决 | 按自主流水线连续推进 | 否 |

## 7. 已知限制 / 后续项

- Docker Socket 方案仅面向受信任本地 Jenkins，不是生产安全部署承诺。
- 环境 Job 由用户手工创建；仓库不自动覆盖 Jenkins Job。

## 验收结论（主人签字）

- [ ] 全部 AC 达成
- [ ] 测试证据充分可信
- [ ] RTM 无漂移
- [ ] 待确认项已逐条裁决

**验收人（主人）**：`__________`　**日期**：`__________`　**结论**：`通过 / 打回（附原因）`
