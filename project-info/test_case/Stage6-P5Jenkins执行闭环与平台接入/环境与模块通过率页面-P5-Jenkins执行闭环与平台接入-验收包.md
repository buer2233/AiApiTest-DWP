# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-验收包

## 1. 验收结论

- 需求定级：M 档，完整 loop。
- 需求状态：已冻结，主人在对话中确认并采纳推荐裁决。
- 开发状态：后端、Jenkins 契约、api-test、前端均已完成回归。
- 验收建议：通过，等待主人终审签字。

## 2. 本阶段交付范围

- 后端接入 Jenkins 任务触发、取消、同步、执行锁和任务列表。
- 平台触发失败重试、模块重试时传入 `RUN_ID=TestRun.run_key`，Jenkins artifact 目录与后端同步 key 对齐。
- 支持每日全量 Jenkins build 发现入口 `POST /api/v1/jenkins-tasks/sync`，按 active daily Job binding 创建或同步 `daily_full` 任务。
- 失败重试同步只更新当前用例状态、失败数和通过率，不更新模块日期和执行时间。
- 模块重试和每日全量同步会更新模块统计、日期、执行时间、归档旧当前用例、写入新失败用例和 `ModuleRunHistory`。
- 前端模块页补齐失败重试、模块重试、用例详情勾选重试、Jenkins 任务弹窗、取消任务、报告/Jenkins 外链和移动端状态。
- Jenkins 共享 Pipeline 新增 `RUN_ID` 参数，优先使用平台传入 run key。

## 3. 不做事项

- 本阶段不新增全局 Jenkins 任务独立路由。
- 本阶段不把 Jenkins / Allure 页面 iframe 嵌入平台。
- 本阶段不对 Jenkins / Allure 外链增加平台 Cookie 二次验证。
- 本阶段不把真实 Jenkins 用户名、API Token、Cookie 或生产 URL 写入仓库。
- 本阶段不把 Jenkins workspace 文件路径作为后端同步来源，仍通过 Jenkins API / artifact URL 同步。

## 4. 关键代码变更

| 模块 | 文件 | 摘要 |
| --- | --- | --- |
| 后端模型/API | `../../../back-end/metrics/models.py`、`../../../back-end/metrics/views.py`、`../../../back-end/metrics/serializers.py`、`../../../back-end/config/urls.py` | Jenkins 任务、执行锁、Job binding、触发/取消/同步/API 返回和 disabled reasons |
| Jenkins service | `../../../back-end/metrics/jenkins_service.py` | Jenkins 触发、取消、queue/build/artifact 同步和公开 URL 转换 |
| Jenkins Pipeline | `../../../jenkins/scripts/api-test-pipeline.groovy` | 新增 `RUN_ID` 参数并透传给 `ci_runner` |
| api-test | `../../../api-test/tools/ci_runner.py` | summary 统计字段和 Jenkins 运行目录契约 |
| 前端 | `../../../front-end/src/views/ModulesView.vue`、`../../../front-end/src/components/metrics/CaseDetailsDialog.vue`、`../../../front-end/src/components/metrics/JenkinsTasksDialog.vue`、`../../../front-end/src/api/metrics.ts`、`../../../front-end/src/types/metrics.ts` | 模块操作、用例重试、任务弹窗、轮询、外链和 API 类型 |

## 5. 验证证据

| 阶段 | 命令 | 证据 | 结论 |
| --- | --- | --- | --- |
| 后端审查修复 RED | `pytest tests/test_metrics_jenkins_execution_api.py tests/test_metrics_jenkins_service.py ../jenkins/tests/test_pipeline_static.py` | `历史验证记录（backend-stage6-p5-review-red-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 11 failed, 24 passed |
| 后端审查修复 GREEN | 同上 | `历史验证记录（backend-stage6-p5-review-green-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 35 passed |
| 最终审查修复 RED | `pytest tests/test_metrics_jenkins_execution_api.py tests/test_metrics_jenkins_service.py ../jenkins/tests/test_pipeline_static.py` | `历史验证记录（backend-stage6-p5-final-review-red-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 缺少真实 discovery 服务函数触发失败 |
| 最终审查修复 GREEN | 同上 | `历史验证记录（backend-stage6-p5-final-review-green-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 40 passed |
| 后端全量 | `pytest` | `历史验证记录（backend-stage6-p5-full-green-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 123 passed, 5 warnings，覆盖率 89% |
| api-test + Jenkins 静态契约 | `pytest tests/test_ci_runner.py ../jenkins/tests/test_pipeline_static.py` | `历史验证记录（api-test-stage6-p5-regression-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 33 passed |
| 前端单元 | `npm run test:unit` | `历史验证记录（stage6-p5-frontend-unit-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 8 passed |
| 前端 E2E | `npx playwright test --project=chromium` | `历史验证记录（stage6-p5-frontend-playwright-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 40 passed |
| 前端构建 | `npm run build` | `历史验证记录（stage6-p5-frontend-build-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 构建通过；存在既有 chunk size warning |

## 6. 截图证据

| 截图 | 路径 |
| --- | --- |
| 模块操作桌面态 | `历史验证记录（screenshots/stage6-p5-modules-actions-desktop-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` |
| 用例重试弹窗 | `历史验证记录（screenshots/stage6-p5-case-retry-dialog-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` |
| Jenkins 任务弹窗桌面态 | `历史验证记录（screenshots/stage6-p5-jenkins-tasks-desktop-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` |
| Jenkins 任务弹窗移动态 | `历史验证记录（screenshots/stage6-p5-jenkins-tasks-mobile-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` |

## 7. 容器化兼容检查

- 后端请求 Jenkins 使用 `JENKINS_API_BASE_URL`，返回给前端的 queue/build/artifact/report URL 会转换为 `JENKINS_PUBLIC_BASE_URL`。
- 前端仍从根 `.env` 读取 Vite 配置，不写死 Jenkins / Allure 地址，也不直接调用 Jenkins API。
- Docker / Jenkins 迁移时只需通过环境变量、Jenkins Job binding 和标准 volume 提供服务地址及凭据。
- `.env.example` 只保留非敏感配置模板；真实账号、密码、token、cookie 不进入仓库。

## 8. 独立审查处理

- 独立审查发现的 Critical / Important 缺口已全部补 RED 测试并转 GREEN：
  - RUN_ID 协议不一致。
  - queued / building 中间态误失败。
  - 缺少 Daily discovery / bulk sync。
  - module_rerun / daily_full 未归档当前用例、未写趋势。
  - canceling 重复取消不幂等。
  - Allure 未生成未使任务失败。
  - 模块行缺少 disabled reasons。
- 最终只读子代理审查结果回写在 planning 进度中。
- 最终只读子代理审查发现 4 个 Important，均已补测试并修复：
  - `discover_daily` 从空实现改为通过 Jenkins API 扫描 active daily Job binding。
  - queue item 已取消时同步为 `canceled` 并释放锁。
  - Daily cron 发现任务使用 Jenkins BUILD_TAG 规则生成 `run_id`，后端按该 key 拉取 artifact。
  - Pipeline 使用 `try/finally` 保证 Allure 校验失败时仍归档 runtime 目录，后端可读取 summary 诊断。

## 9. 主人终审签字

- 终审人：主人
- 终审日期：
- 终审结论：
- 备注：
