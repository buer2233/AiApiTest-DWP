# Stage13-Daily-Full-Module-单一流水线编排：验收包

## 当前结论

v2.3 自动 schema 与首次数据初始化已完成 TDD 和独立审查；Task8 已消除 #27 的 Tests 阻断，并由固定 Jenkins Platform Bootstrap Job #29 完成全绿运行态验收。主人已完成私有精确授权；Jenkins Init 已删除两条旧分模块 Daily Job 及其构建历史，认证 API 与启动日志均已复核。

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
- Task8 将 E2E 测试容器的前端代理固定指向 Compose backend 服务；旧 Daily Job 仅在严格批准值和精确白名单均合法时删除，未授权时默认保留并移除 TimerTrigger。
- Jenkins 镜像实际使用的 `throttle-concurrents` 插件要求八参数 `ThrottleJobProperty` 构造器；已以最小兼容修复保证 Init 不会在三类独立十并发分类配置阶段中断，从而能继续执行受控删除分支。

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
| Task8 固定环境验收 | `AiApiTest-DWP-Platform-Bootstrap #29`；`build_all=true`、`run_full_tests=true` | `SUCCESS`；Preflight、Dependency Assurance、Schema & Initial Data、Deploy、Health、Tests 全部成功 |
| Jenkins 插件兼容 RED / GREEN | `test_init_uses_jenkins_plugin_constructor_signatures_for_throttle_and_scm` | RED：旧六参数调用不匹配；GREEN：八参数调用通过 |
| Jenkins 静态全量回归 | `python -m pytest jenkins/tests -q` | `275 passed, 1 skipped` |
| Jenkins 插件兼容独立审查 | 八参数 API、三类独立十并发和测试覆盖 | 批准；Critical/Important/Minor 均为 `0` |
| Jenkins Init 与受控删除运行态验收 | 重建后 Jenkins 启动日志与认证 Job API 条件轮询 | Init 无 Groovy 失败；两条精确旧 Job 为 `404`，Daily 父/Worker、两条重试和 Bootstrap 均为 `200` |

## 固定 Jenkins 环境验收

- Job #27（历史失败）：Schema & Initial Data、Deploy、Health 成功；Tests 被趋势固定日期、旧 Stage3 UI 断言与退休证据路径阻断。
- Job #28（Task8 首次复验失败）：53 passed、5 skipped、1 failed；唯一失败为 Stage3 C01 R1 摘要地址 locator 跨区域匹配两个合法 URL。`93b4cbd` 已将断言限定到“环境通过率”区域。
- Job #29：参数 `build_all=true`、`run_full_tests=true`，终态 `SUCCESS`。Preflight、Dependency Assurance、Schema & Initial Data（`migrate`、`seed_environment`、bootstrap-only 管理员初始化）、Deploy、Health、Tests 均无诊断失败；backend/前端健康与前端 API 代理均为 HTTP 200。
- Jenkins artifact 名称：`platform-bootstrap-summary.json`、`platform-bootstrap-summary.md`、`schema-initialization.json`、`health.json`、`tests.json`、`test-frontend-playwright-run.log`、Junit、Allure 归档和 Playwright 报告。原始内容只留 Jenkins artifact，未提交 Git。
- 处理边界：仅固定 Job 的一次性 `backend-bootstrap` 服务获准执行标准迁移和首次数据初始化；AI、宿主机、常驻服务与 ready endpoint 仍禁止 migration。不得以直接启动服务替代验收。

实际原始 pytest coverage HTML 已清理，未作为 Git 产物保留。

## 受控删除已完成

- 主人在私有根 `.env` 设置严格批准值与两条精确白名单后，已授权仅 Jenkins 服务的镜像构建和保留 `aiapitest-jenkins-home` 数据卷的重建；未删除数据卷，未管理 MySQL 或应用服务。
- 初次重建揭示运行镜像缺少插件与历史 Init 覆盖问题；迁移历史 Init 后，又通过运行镜像 `javap` 定位并修复新版插件的八参数构造器兼容问题。修复提交为 `582e3e3`、`edb7dc2`。
- 最终启动日志明确记录删除 `AiApiTest-DWP-Daily-Full-Module-test_gbif_case` 与 `AiApiTest-DWP-Daily-Full-Module-test_gbif_case_module2` 及其构建历史；认证 API 复核两条均为 HTTP `404`。
- 唯一 Daily 父 Job、Daily Worker、模块重试、失败重试和 Platform Bootstrap 均为 HTTP `200`；未对其他 Jenkins Job、平台数据库历史或应用服务作删除操作。
