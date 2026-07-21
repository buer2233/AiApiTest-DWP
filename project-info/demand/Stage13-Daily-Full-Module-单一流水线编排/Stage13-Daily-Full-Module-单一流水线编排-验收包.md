# Stage13-Daily-Full-Module-单一流水线编排：验收包

## 当前结论

v2.2 自动 schema 与首次数据初始化已完成 TDD 和独立审查；Task8 已修复 #27 的 Tests 阻断并完成本地全量门禁。固定 Jenkins Platform Bootstrap Job 的全绿运行态验收待触发；旧分模块 Daily Job 与历史按主人 A 裁决保留至全绿后由主人/运维受控删除。

## 需求与视觉

- 需求已冻结：`Stage13-Daily-Full-Module-单一流水线编排-需求说明.md`。
- 主人已选择 C01：顶部环境快照与下方全宽目录台账；区域、权限和组件映射见 `../../UI/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-UI原型.md`。
- RTM：`../../test_case/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-可追溯矩阵.md`。

## 实施摘要

- Daily 唯一父 Pipeline、三类各自最多 10 Job 并发、父级聚合 Allure 与环境 YAML 协议已实现。
- 环境目录 CRUD、YAML 导入、同步审计、失败重试、冲突保护及 member/admin 边界已实现。
- `/environments` 已按 C01 实现 R1 环境快照和仅 admin 的 R2-R4 管理区；未加入模块子任务、模块级 Allure 或 Daily 触发入口。
- 最终后端复审整改已关闭：member 不再获得目录审计；Daily Jenkins 基础设施失败不会被写成成功；queue 状态持久化失败具备补偿和受控 503。
- Platform Bootstrap 现通过一次性 `backend-bootstrap` 容器依次执行 `migrate --noinput`、`seed_environment` 与 `init_admin --bootstrap-only`；已有库增量迁移，已有环境或账号不被覆盖，readiness 保持只读。
- Task8 将 E2E 测试容器的前端代理固定指向 Compose backend 服务；旧 Daily Job 仅在严格批准值和精确白名单均合法时删除，默认保留并移除 TimerTrigger。

## 已验证证据

| 范围 | 证据 | 结果 |
| --- | --- | --- |
| Task 4 完整定向回归 | 整改代理运行后端 pytest | `97 passed`，coverage `60%` |
| Task 4 重点复跑 | `back-end` 的环境目录、Daily 父同步、API/Swagger 测试 | `50 passed` |
| Jenkins 静态 | Daily 和 Pipeline 静态测试 | 整改代理 `57 passed`；重点复跑 `15 passed` |
| 前端单测 | `npm run test:unit` | `9 files / 22 passed` |
| 前端类型 | `npm run typecheck` | 通过 |
| 代码完整性 | `git diff --check` | 通过，只有既有 CRLF 提示 |
| Task 7 Jenkins 定向回归 | schema 初始化、阶段、Deploy/Summary、静态门禁 | `23 passed` |
| Task 7 后端定向回归 | 管理员 bootstrap-only、环境投影、readiness | `23 passed` |
| Task 7 独立审查 | F5 规格与代码质量 | 批准，无 Critical/Important/Minor |
| Task8 Jenkins 全量 | `python -m pytest jenkins/tests -q` | `274 passed, 1 skipped` |
| Task8 后端全量 | `python -m pytest tests -q` | 退出码 `0`，coverage `90%` |
| Task8 前端类型 | `npm run typecheck` | 通过 |
| Task8 独立审查 | 后端、前端、Jenkins、资料及整改复审 | 批准；最终全分支审查代理两次并发断开，未产生文件修改 |

## 固定 Jenkins 环境验收

- Job：`AiApiTest-DWP-Platform-Bootstrap #27`，参数 `build_all=true`、`run_full_tests=true`，终态 `FAILURE`。
- 成功阶段：Preflight、Dependency Assurance、Schema & Initial Data、Deploy、Health。backend ready 已通过，证明空库 schema 初始化不再阻断服务就绪；基础 MySQL/Jenkins 容器保持受管边界。
- Tests 失败诊断：后端 `test_trend_window_uses_local_date_for_snapshot_completion` 固定日期落出当前 7 天窗口；前端 Playwright 的 3 个既有用例失败；api-runner 静态测试命中 Stage13 `progress.md` 中既有退休证据路径。三项均未由 F5 代码触及。
- Jenkins artifact 名称：`platform-bootstrap-summary.json`、`schema-initialization.json`、`health.json`、相关 `test-*.log` 和 Playwright 结果。原始内容只留 Jenkins artifact，未提交 Git。
- 处理边界：仅固定 Job 的一次性 `backend-bootstrap` 服务获准执行标准迁移和首次数据初始化；AI、宿主机、常驻服务与 ready endpoint 仍禁止 migration。不得以直接启动服务替代验收。

实际原始 pytest coverage HTML 已清理，未作为 Git 产物保留。

## 待执行的固定环境验收

- 入口：Windows 使用 `scripts/trigger-platform-bootstrap.ps1`，仅触发固定 Platform Bootstrap Job。
- 待获取的 Jenkins artifact：Task8 修复后的全绿 Stage13 Playwright 结果与关键页面截图、平台构建摘要、后端/前端全量回归摘要。
- 残余风险：真实 Jenkins Allure 插件失败、Git push 回调与远端时序仍只能在该固定 Job 中验证；全绿后还需由主人/运维在私有配置批准精确白名单并重启 Jenkins bootstrap，方可永久删除旧 Job 及其构建历史。
