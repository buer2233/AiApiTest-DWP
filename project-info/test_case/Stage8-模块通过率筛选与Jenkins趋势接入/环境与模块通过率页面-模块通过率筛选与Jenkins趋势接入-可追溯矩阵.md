# 环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-可追溯矩阵

## 1. 基本信息

- 需求阶段：`Stage8-模块通过率筛选与Jenkins趋势接入`
- 需求文档：`../../demand/Stage8-模块通过率筛选与Jenkins趋势接入/环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-需求说明.md`
- 功能测试用例：`环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-功能测试用例.md`
- UI 原型：`../../UI/Stage8-模块通过率筛选与Jenkins趋势接入/环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-UI区域语义拆解与实现范围映射.md`
- 状态：已完成后端、前端、Jenkins/Docker 静态回归；Phase 8 独立对抗审查复审通过。

## 2. 证据索引

| 证据编号 | 路径 | 结论 |
| --- | --- | --- |
| EV-S8-BE-TARGET | `../../../back-end/tests/evidence/backend-stage8-phase5-target-green-20260707.txt` | Stage8 后端目标测试：55 passed，覆盖率 72% |
| EV-S8-BE-FULL | `../../../back-end/tests/evidence/backend-stage8-phase5-full-green-20260707.txt` | 后端全量测试：140 passed，覆盖率 89% |
| EV-S8-BE-CHECK | `../../../back-end/tests/evidence/backend-stage8-phase5-manage-check-20260707.txt` | Django system check 无问题 |
| EV-S8-BE-MIGRATION | `../../../back-end/tests/evidence/backend-stage8-phase5-makemigrations-check-20260707.txt` | 迁移检查无新增 migration |
| EV-S8-FE-API-RED | `../../../front-end/tests/evidence/stage8-frontend-api-red-20260707.txt` | 前端 API 契约 RED：缺 `fetchModuleSnapshotFilterOptions` |
| EV-S8-FE-E2E-RED | `../../../front-end/tests/evidence/stage8-frontend-playwright-red-20260707.txt` | 前端 Stage8 E2E RED：旧筛选、旧列顺序、旧重试口径失败 |
| EV-S8-FE-API | `../../../front-end/tests/evidence/stage8-frontend-api-green-20260707.txt` | Stage8 前端 API 契约：3 passed |
| EV-S8-FE-E2E | `../../../front-end/tests/evidence/stage8-frontend-playwright-green-with-screenshots-20260707.txt` | Stage8 目标 Playwright：8 passed |
| EV-S8-FE-TYPE | `../../../front-end/tests/evidence/stage8-frontend-typecheck-green-20260707.txt` | 前端 TypeScript / Vue typecheck 通过 |
| EV-S8-FE-UNIT | `../../../front-end/tests/evidence/stage8-frontend-unit-full-20260707.txt` | 前端全量 Vitest：6 files / 12 tests passed |
| EV-S8-FE-FULL-E2E | `../../../front-end/tests/evidence/stage8-frontend-playwright-full-green-20260707.txt` | 前端全量 Playwright：51 passed，1 skipped（既有 `.local` 真服务回归） |
| EV-S8-FE-BUILD | `../../../front-end/tests/evidence/stage8-frontend-build-green-20260707.txt` | 前端生产构建通过，保留既有 Rollup warning |
| EV-S8-JENKINS | `../../../jenkins/tests/evidence/jenkins-stage8-phase7-static-20260707.txt` | Jenkins/Docker 静态回归：41 passed |
| EV-S8-SHOT-MODULES | `../../../front-end/tests/evidence/screenshots/stage8-modules-filters-desktop-20260707.png` | `/modules` 桌面筛选、列顺序截图 |
| EV-S8-SHOT-CASE | `../../../front-end/tests/evidence/screenshots/stage8-case-details-retry-20260707.png` | 用例详情失败重试提示截图 |
| EV-S8-SHOT-JENKINS | `../../../front-end/tests/evidence/screenshots/stage8-jenkins-tasks-filters-20260707.png` | Jenkins 任务弹窗筛选截图 |
| EV-S8-SHOT-MOBILE | `../../../front-end/tests/evidence/screenshots/stage8-modules-mobile-20260707.png` | `/modules` 移动端卡片截图 |

## 3. AC 追溯矩阵

| AC 编号 | 功能测试用例 | 后端 / Jenkins 证据 | 前端证据 | 状态 |
| --- | --- | --- | --- | --- |
| AC-S8-1.1 | TC-S8-1.1-001 | 不涉及后端新增行为 | EV-S8-FE-E2E、EV-S8-SHOT-MODULES | 通过 |
| AC-S8-1.2 | TC-S8-1.2-001 | EV-S8-BE-TARGET | EV-S8-FE-E2E、EV-S8-SHOT-MODULES | 通过 |
| AC-S8-1.3 | TC-S8-1.3-001、TC-S8-1.3-002 | EV-S8-BE-TARGET | EV-S8-FE-API、EV-S8-FE-E2E | 通过 |
| AC-S8-1.4 | TC-S8-1.4-001、TC-S8-1.4-002 | EV-S8-BE-TARGET | EV-S8-FE-E2E | 通过 |
| AC-S8-1.5 | TC-S8-1.5-001 | 不涉及后端新增行为 | EV-S8-FE-E2E | 通过 |
| AC-S8-2.1 | TC-S8-2.1-001 | 不涉及后端新增行为 | EV-S8-FE-E2E、EV-S8-SHOT-MODULES | 通过 |
| AC-S8-2.2 | TC-S8-2.2-001 | 复用 P3 用例详情接口，EV-S8-BE-FULL 回归 | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-2.3 | TC-S8-2.3-001 | 不涉及后端新增行为 | EV-S8-FE-E2E、EV-S8-SHOT-MOBILE | 通过 |
| AC-S8-3.1 | TC-S8-3.1-001、TC-S8-3.2-002、TC-S8-3.2-003 | EV-S8-BE-TARGET | 不涉及页面直接操作 | 通过 |
| AC-S8-3.2 | TC-S8-3.2-001、TC-S8-3.2-002、TC-S8-3.2-003 | EV-S8-BE-TARGET、EV-S8-JENKINS | 不涉及页面直接操作 | 通过 |
| AC-S8-3.3 | TC-S8-3.3-001 | EV-S8-BE-TARGET、EV-S8-BE-FULL | EV-S8-FE-E2E | 通过 |
| AC-S8-3.4 | TC-S8-3.4-001 | EV-S8-BE-FULL | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-3.5 | TC-S8-3.5-001 | EV-S8-BE-FULL | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-4.1 | TC-S8-4.1-001 | EV-S8-BE-TARGET | EV-S8-FE-E2E、EV-S8-SHOT-JENKINS | 通过 |
| AC-S8-4.2 | TC-S8-4.2-001 | EV-S8-BE-TARGET | EV-S8-FE-E2E、EV-S8-SHOT-JENKINS | 通过 |
| AC-S8-4.3 | TC-S8-4.3-001、TC-S8-4.3-002 | EV-S8-BE-TARGET | EV-S8-FE-E2E、EV-S8-SHOT-JENKINS | 通过 |
| AC-S8-4.4 | TC-S8-4.4-001 | EV-S8-BE-FULL | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-4.5 | TC-S8-4.5-001 | 不涉及后端新增行为 | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-5.1 | TC-S8-5.1-001 | EV-S8-BE-FULL | 不涉及本阶段新增页面 | 通过 |
| AC-S8-5.2 | TC-S8-5.2-001 | EV-S8-BE-FULL | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-5.3 | TC-S8-5.3-001 | EV-S8-BE-FULL | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-5.4 | TC-S8-5.4-001、TC-S8-5.5-002 | EV-S8-BE-FULL | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-5.5 | TC-S8-5.5-001、TC-S8-5.5-002 | EV-S8-BE-FULL | EV-S8-FE-FULL-E2E | 通过 |
| AC-S8-6.1 | TC-S8-6.1-001 | EV-S8-BE-TARGET | EV-S8-FE-E2E、EV-S8-SHOT-MODULES | 通过 |
| AC-S8-6.2 | TC-S8-6.2-001、TC-S8-6.2-002 | EV-S8-BE-TARGET | EV-S8-FE-E2E、EV-S8-SHOT-CASE | 通过 |
| AC-S8-6.3 | TC-S8-6.3-001、TC-S8-6.3-002 | EV-S8-BE-TARGET | EV-S8-FE-E2E、EV-S8-SHOT-MODULES | 通过 |

## 4. UI 区域语义拆解追溯

| 区域 | 映射 | 证据 |
| --- | --- | --- |
| R1 `/modules` 页面主体 | `front-end/src/views/ModulesView.vue` | EV-S8-FE-E2E、EV-S8-SHOT-MODULES、EV-S8-SHOT-MOBILE |
| R2 设计标注层 | 不进入 DOM、不进入 Playwright 断言 | UI 映射文档：`../../UI/Stage8-模块通过率筛选与Jenkins趋势接入/环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-UI区域语义拆解与实现范围映射.md` |
| R3 用例详情弹窗 | `front-end/src/components/metrics/CaseDetailsDialog.vue` | EV-S8-FE-E2E、EV-S8-SHOT-CASE |
| R4 Jenkins 任务弹窗 | `front-end/src/components/metrics/JenkinsTasksDialog.vue` | EV-S8-FE-E2E、EV-S8-SHOT-JENKINS |

## 5. 缺口结论

- Stage8 主路径 AC-S8-1.1 至 AC-S8-6.3 均有功能测试用例和自动化证据。
- 方案 B 仅作为 UI 过程候选归档，不进入 Vue DOM 或 Playwright 断言。
- 前端仍只调用 DRF 相对 API；Jenkins / Allure URL 仅展示后端返回链接。
- 本地 Jenkins Daily Job 初始化已与后端 binding 命名对齐，避免 Daily discovery 扫描不存在的本地 Job。
- Phase 8 复审 Critical / Important / Minor 均为无；真实 Jenkins Script Console 执行未在本阶段自动化内覆盖，需人工联调时执行本地脚本确认。
