# Stage13-Daily-Full-Module-单一流水线编排：Task8 验收阻断整改设计

## 定级与冻结

- 定级：M/L。涉及 Jenkins Job 生命周期、Platform Bootstrap 全量回归、后端测试时钟、前端 E2E 契约与运行器网络配置。
- 主人于 2026-07-21 选择 A：先修复并通过同一固定 Platform Bootstrap Job 的全绿验收，再永久删除精确指定的两个旧 Daily Job 及其全部构建历史。
- 不新增页面、DRF API、数据库表或应用环境旁路入口；现有 C01 R1 UI 范围保持不变。

## 根因与目标

| 阻断 | 根因 | 整改目标 |
| --- | --- | --- |
| 旧 Daily Job 未删除 | 当前 init Groovy 和静态测试刻意只移除 TimerTrigger | 受控 allowlist 删除，默认关闭且只在主人批准后执行 |
| 后端全量回归 | 趋势测试固定历史日期，真实本地日期窗口已越界 | 冻结测试时钟或使用相对日期，不改生产 API |
| 前端 E2E | 一个 locator 匹配多个节点；两条 Stage3 断言已被 Stage13 C01 取代 | 收紧 locator，按 C01 R1 更新旧 E2E 与追溯资料 |
| E2E 容器网络 | Vite proxy 回退容器自身 `127.0.0.1:8000` | 显式注入 Compose backend 服务地址 |
| 静态门禁 | 历史资料仍出现已退休证据目录字面路径 | 更新为 Jenkins Artifact 追溯说明，不提交运行产物 |

## 受控删除协议

1. Jenkins init 默认只移除旧 Daily TimerTrigger，保留所有 Job 与历史。
2. 仅当私有 `JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED=true` 且 `JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES` 为精确 allowlist 时，才删除 allowlist 中存在且匹配旧 Daily 前缀的 `WorkflowJob`。
3. allowlist 不能包含唯一 Daily 父 Job、Worker Job、空名称或不匹配前缀的 Job；非法配置只保留 Job 并输出脱敏审计诊断。
4. 删除在同一固定 Platform Bootstrap Job 全绿验收之后，由主人/平台运维重启 Jenkins bootstrap 触发；AI 不直接删除 Job、构建历史或管理 Jenkins 容器。

## TDD 与验收

- 每项生产逻辑先新增最小 RED 测试并确认按预期失败，再进行 GREEN 与 REFACTOR。
- 定向后端、前端、Jenkins 静态/单元回归均须通过；随后只通过固定 Platform Bootstrap Job 执行完整回归。
- Job 全绿后，验收包登记 build、摘要和 Artifact 名称；主人/平台运维配置批准标志与 allowlist 后重启 Jenkins bootstrap，复核仅两个精确 Job 被删除。
