# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-可追溯矩阵

## 1. 基本信息

- 需求阶段：`Stage6-P5Jenkins执行闭环与平台接入`
- 需求文档：`../../demand/Stage6-P5Jenkins执行闭环与平台接入/环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-需求说明.md`
- 功能测试用例：`环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-功能测试用例.md`
- UI 原型：`../../UI/Stage6-P5Jenkins执行闭环与平台接入/环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-UI原型.md`
- 状态：已完成开发回归，等待主人终审签字。

## 2. 证据索引

| 证据编号 | 路径 | 结论 |
| --- | --- | --- |
| EV-P5-BE-RED | `历史验证记录（backend-stage6-p5-review-red-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 独立审查缺口 RED：11 failed, 24 passed |
| EV-P5-BE-REVIEW | `历史验证记录（backend-stage6-p5-review-green-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 审查修复目标测试：35 passed |
| EV-P5-FINAL-RED | `历史验证记录（backend-stage6-p5-final-review-red-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 最终只读审查缺口 RED：导入缺失触发失败 |
| EV-P5-FINAL-REVIEW | `历史验证记录（backend-stage6-p5-final-review-green-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 最终审查修复目标测试：40 passed |
| EV-P5-BE-FULL | `历史验证记录（backend-stage6-p5-full-green-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 后端全量：123 passed, 5 warnings，覆盖率 89% |
| EV-P5-API-JENKINS | `历史验证记录（api-test-stage6-p5-regression-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | api-test + Jenkins 静态契约：33 passed |
| EV-P5-FE-UNIT | `历史验证记录（stage6-p5-frontend-unit-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 前端单元：8 passed |
| EV-P5-FE-E2E | `历史验证记录（stage6-p5-frontend-playwright-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 前端 Playwright Chromium：40 passed |
| EV-P5-FE-BUILD | `历史验证记录（stage6-p5-frontend-build-final-20260705.txt，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 前端生产构建通过，存在既有 chunk size warning |
| EV-P5-SHOT-1 | `历史验证记录（screenshots/stage6-p5-modules-actions-desktop-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 模块操作桌面截图 |
| EV-P5-SHOT-2 | `历史验证记录（screenshots/stage6-p5-case-retry-dialog-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | 用例失败重试弹窗截图 |
| EV-P5-SHOT-3 | `历史验证记录（screenshots/stage6-p5-jenkins-tasks-desktop-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | Jenkins 任务弹窗桌面截图 |
| EV-P5-SHOT-4 | `历史验证记录（screenshots/stage6-p5-jenkins-tasks-mobile-20260705.png，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）` | Jenkins 任务弹窗移动端截图 |

## 3. AC 追溯矩阵

| AC 编号 | 功能测试用例 | 后端 / Jenkins 证据 | 前端证据 | 状态 |
| --- | --- | --- | --- | --- |
| AC-P5-1.1 | TC-P5-F1-001 | EV-P5-BE-REVIEW、EV-P5-API-JENKINS | EV-P5-FE-E2E | 通过 |
| AC-P5-1.2 | TC-P5-F1-002 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-1.3 | TC-P5-F1-003 | EV-P5-BE-FULL、EV-P5-API-JENKINS | EV-P5-FE-UNIT | 通过 |
| AC-P5-2.1 | TC-P5-F2-001 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-2.2 | TC-P5-F2-002 | EV-P5-BE-REVIEW、EV-P5-FINAL-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-2.3 | TC-P5-F2-003 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-2.4 | TC-P5-F2-004 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-2.5 | TC-P5-F2-005 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-2.6 | TC-P5-F2-006、TC-P5-F2-007 | EV-P5-BE-REVIEW、EV-P5-FINAL-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-3.1 | TC-P5-F3-001 | EV-P5-BE-REVIEW、EV-P5-FINAL-REVIEW | 不涉及当前页面直接操作 | 通过 |
| AC-P5-3.2 | TC-P5-F3-002 | EV-P5-BE-REVIEW、EV-P5-BE-FULL | EV-P5-FE-E2E | 通过 |
| AC-P5-3.3 | TC-P5-F3-003 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-3.4 | TC-P5-F3-004 | EV-P5-BE-REVIEW、EV-P5-FINAL-REVIEW | 不涉及当前页面直接操作 | 通过 |
| AC-P5-4.1 | TC-P5-F4-001 | EV-P5-BE-REVIEW | EV-P5-FE-E2E、EV-P5-SHOT-1 | 通过 |
| AC-P5-4.2 | TC-P5-F4-002、TC-P5-F4-007 | EV-P5-BE-REVIEW | EV-P5-FE-E2E、EV-P5-SHOT-2 | 通过 |
| AC-P5-4.3 | TC-P5-F4-003 | EV-P5-BE-REVIEW | EV-P5-FE-E2E、EV-P5-SHOT-2 | 通过 |
| AC-P5-4.4 | TC-P5-F4-004 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-4.5 | TC-P5-F4-005 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-4.6 | TC-P5-F4-006 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-5.1 | TC-P5-F5-001 | EV-P5-BE-REVIEW、EV-P5-API-JENKINS | EV-P5-FE-E2E | 通过 |
| AC-P5-5.2 | TC-P5-F5-002 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-5.3 | TC-P5-F5-003 | EV-P5-BE-REVIEW、EV-P5-FINAL-REVIEW | 不涉及当前页面直接操作 | 通过 |
| AC-P5-5.4 | TC-P5-F5-004 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-6.1 | TC-P5-F6-001 | EV-P5-BE-REVIEW | EV-P5-FE-E2E、EV-P5-SHOT-3、EV-P5-SHOT-4 | 通过 |
| AC-P5-6.2 | TC-P5-F6-002、TC-P5-F6-006 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-6.3 | TC-P5-F6-003 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-6.4 | TC-P5-F6-004 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-6.5 | TC-P5-F6-005 | 不涉及后端新增断言 | EV-P5-FE-E2E | 通过 |
| AC-P5-7.1 | TC-P5-F7-001 | EV-P5-BE-REVIEW | EV-P5-FE-E2E、EV-P5-SHOT-1 | 通过 |
| AC-P5-7.2 | TC-P5-F7-002 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-7.3 | TC-P5-F7-003 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-7.4 | TC-P5-F7-004 | EV-P5-BE-REVIEW | EV-P5-FE-E2E | 通过 |
| AC-P5-7.5 | TC-P5-F7-005 | 不涉及后端新增断言 | EV-P5-FE-E2E、EV-P5-SHOT-4 | 通过 |

## 4. 缺口结论

- RED 阶段暴露的 RUN_ID、queue pending、building、canceling 幂等、Allure 未生成、模块重试归档与趋势、disabled reasons、Daily discovery 缺口均已由 EV-P5-BE-REVIEW 和 EV-P5-FINAL-REVIEW 覆盖转绿。
- 前端仍只调用 DRF API；Jenkins 和 Allure 链接仅作为后端返回的外链新页打开，不做 iframe 嵌入。
- 本阶段没有新增敏感配置提交，真实 Jenkins 凭据仍要求只放本地 `.env` 或 Jenkins 私有凭据。
