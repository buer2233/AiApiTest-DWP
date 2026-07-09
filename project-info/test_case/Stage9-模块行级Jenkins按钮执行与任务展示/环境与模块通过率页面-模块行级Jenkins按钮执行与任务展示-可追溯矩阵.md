# 环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示 可追溯矩阵

| AC 编号 | 需求点 | 测试用例 | 实现位置 | 验证结果 |
| --- | --- | --- | --- | --- |
| AC-S9-1.1 | 一键失败重试创建 `failed_rerun` Jenkins task | TC-S9-E2E-001；既有 P5/Stage8 回归 | `front-end/src/views/ModulesView.vue`、`front-end/src/api/metrics.ts`、`back-end/metrics/views.py` | Stage8 Playwright 相关用例通过 |
| AC-S9-1.2 | 失败重试同步后刷新失败数/通过率且不改日期/执行时间 | TC-S9-BE-003；P5 回归 | `back-end/metrics/views.py::apply_failed_rerun_summary` | P5 Jenkins 接口测试通过 |
| AC-S9-2.1 | 模块重试确认后创建 `module_rerun` Jenkins task | TC-S9-E2E-002；P5/Stage8 回归 | `front-end/src/views/ModulesView.vue`、`back-end/metrics/views.py::ModuleRerunCreateView` | Stage8 Playwright 相关用例通过 |
| AC-S9-2.2 | 模块重试同步后刷新统计、日期、执行时间、用例和趋势 | TC-S9-BE-002；P5 回归 | `back-end/metrics/views.py::apply_module_summary` | P5 Jenkins 接口测试通过 |
| AC-S9-3.1 | Jenkins 任务弹窗按历史字段展示 | TC-S9-E2E-003；Stage8 回归 | `front-end/src/components/metrics/JenkinsTasksDialog.vue` | Stage8 Playwright 任务弹窗用例通过 |
| AC-S9-3.2 | 任务弹窗轮询时触发 DRF 同步并刷新模块列表 | TC-S9-FE-002；TC-S9-E2E-003 | `front-end/src/components/metrics/JenkinsTasksDialog.vue`、`front-end/src/api/metrics.ts` | Stage6 Playwright 目标用例通过 |
| AC-S9-3.3 | Jenkins/Allure 外链新页打开 | TC-S9-E2E-003；Stage8 回归 | `front-end/src/components/metrics/JenkinsTasksDialog.vue` | Stage8 Playwright 任务弹窗用例通过 |
| AC-S9-4.1 | Daily 批量同步传入 active daily job names | TC-S9-BE-001 | `back-end/metrics/views.py::JenkinsTaskBulkSyncView` | 新增 pytest 通过 |
| AC-S9-4.2 | 单任务同步返回最新 task | TC-S9-FE-001；P5 后端回归 | `front-end/src/api/metrics.ts::syncJenkinsTask`、`back-end/metrics/views.py::JenkinsTaskSyncView` | Vitest API 契约和 P5 pytest 通过 |

## 覆盖说明

- 本阶段不新增 API URL；RTM 中实现位置均落在 P5/Stage8 已冻结接口和组件。
- 截图红框属于设计标注层，不进入 DOM，因此不纳入产品 UI 断言。
