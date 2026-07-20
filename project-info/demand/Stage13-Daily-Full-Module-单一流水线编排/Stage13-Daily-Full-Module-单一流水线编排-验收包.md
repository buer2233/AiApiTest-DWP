# Stage13-Daily-Full-Module-单一流水线编排：验收包

## 当前结论

代码、静态测试和独立审查整改已完成；固定 Jenkins Platform Bootstrap Job #26 已执行但在 Health 阶段因数据库 schema 未就绪失败。旧分模块 Daily Job 与历史没有删除。

## 需求与视觉

- 需求已冻结：`Stage13-Daily-Full-Module-单一流水线编排-需求说明.md`。
- 主人已选择 C01：顶部环境快照与下方全宽目录台账；区域、权限和组件映射见 `../../UI/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-UI原型.md`。
- RTM：`../../test_case/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-可追溯矩阵.md`。

## 实施摘要

- Daily 唯一父 Pipeline、三类各自最多 10 Job 并发、父级聚合 Allure 与环境 YAML 协议已实现。
- 环境目录 CRUD、YAML 导入、同步审计、失败重试、冲突保护及 member/admin 边界已实现。
- `/environments` 已按 C01 实现 R1 环境快照和仅 admin 的 R2-R4 管理区；未加入模块子任务、模块级 Allure 或 Daily 触发入口。
- 最终后端复审整改已关闭：member 不再获得目录审计；Daily Jenkins 基础设施失败不会被写成成功；queue 状态持久化失败具备补偿和受控 503。

## 已验证证据

| 范围 | 证据 | 结果 |
| --- | --- | --- |
| Task 4 完整定向回归 | 整改代理运行后端 pytest | `97 passed`，coverage `60%` |
| Task 4 重点复跑 | `back-end` 的环境目录、Daily 父同步、API/Swagger 测试 | `50 passed` |
| Jenkins 静态 | Daily 和 Pipeline 静态测试 | 整改代理 `57 passed`；重点复跑 `15 passed` |
| 前端单测 | `npm run test:unit` | `9 files / 22 passed` |
| 前端类型 | `npm run typecheck` | 通过 |
| 代码完整性 | `git diff --check` | 通过，只有既有 CRLF 提示 |

## 固定 Jenkins 环境验收

- Job：`AiApiTest-DWP-Platform-Bootstrap #26`，参数 `build_all=false`、`run_full_tests=true`，终态 `FAILURE`。
- 成功阶段：Preflight、Dependency Assurance、Deploy。backend live probe 为 200，基础 MySQL/Jenkins 容器在 Deploy 前后保持同一 ID。
- 失败诊断：backend ready 为 `503 schema_not_ready`，数据库连接可用但 schema 未就绪；全局 Health deadline 随后使 frontend 和 worker probe 失败，Tests 阶段未执行。
- Jenkins artifact 名称：`platform-bootstrap-summary.json`、`health.json`、`health-backend-ready.log`、`health-frontend-*.log`、`health-worker.log`。原始内容只留 Jenkins artifact，未提交 Git。
- 处理边界：固定 Job 与 AI 都禁止执行 migration。主人/平台运维须按批准的数据库迁移流程补齐 schema 后，再运行同一固定 Job；不得以直接启动服务替代验收。

实际原始 pytest coverage HTML 已清理，未作为 Git 产物保留。

## 待执行的固定环境验收

- 入口：Windows 使用 `scripts/trigger-platform-bootstrap.ps1`，仅触发固定 Platform Bootstrap Job。
- 待获取的 Jenkins artifact：Stage13 Playwright 结果与关键页面截图、平台构建摘要、后端/前端全量回归摘要。
- 残余风险：真实 Jenkins Allure 插件失败、Git push 回调与远端时序只能在该固定 Job 中验证；本地没有启动 Docker、Django、Vite 或 Jenkins。
