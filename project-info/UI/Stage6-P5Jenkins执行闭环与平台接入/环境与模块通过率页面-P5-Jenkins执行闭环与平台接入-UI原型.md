# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入 UI 原型

## 1. 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入 |
| 阶段目录 | `Stage6-P5Jenkins执行闭环与平台接入` |
| 输入需求 | `project-info/demand/Stage6-P5Jenkins执行闭环与平台接入/环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-需求说明.md` |
| 输入测试 | `project-info/test_case/Stage6-P5Jenkins执行闭环与平台接入/环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-功能测试用例.md` |
| 原型状态 | v1.0，前端实现范围冻结 |

## 2. 视觉与交互基线

- 延续 P2/P3 的企业级自动化测试后台气质：高密度、可扫描、少装饰。
- 不新增营销型 hero、图形背景或独立 Jenkins 看板首屏。
- 操作按钮使用图标+短文本，危险操作“取消任务”使用明确二次确认。
- 状态色必须区分：运行中、成功、测试失败、基础设施失败、取消中、已取消，不只靠颜色表达。
- 桌面端以表格和弹窗为主；移动端以卡片、底部弹窗或全屏弹窗为主。

## 3. 页面 / 弹窗清单

| 编号 | 类型 | 名称 | 是否新增路由 | 说明 |
| --- | --- | --- | --- | --- |
| P1 | 既有页面 | 模块通过率页 `/modules` | 否 | 启用失败重试、模块重试、Jenkins 任务按钮。 |
| D1 | 弹窗 | 失败重试确认 | 否 | 模块行一键失败重试、详情勾选失败重试、详情一键失败重试共用确认结构。 |
| D2 | 弹窗 | 模块重试确认 | 否 | 展示模块名、环境、影响说明和锁提示。 |
| D3 | 弹窗 | Jenkins 任务 | 否 | 当前模块今日任务列表、取消、报告、Jenkins 外链和轮询刷新。 |
| D4 | 既有弹窗扩展 | 用例详情 | 否 | 增加失败用例勾选、失败重试和一键失败重试。 |
| S1 | 状态 | 锁冲突、提交中、成功、失败、无权限 | 否 | 用 toast、按钮 loading、表格状态和弹窗内错误呈现。 |

## 4. 区域语义拆解表

| 区域编号 | 内容 | 是否进入前端 | 前端落点 | 触发条件 | 禁止项 |
| --- | --- | --- | --- | --- | --- |
| R1 | `/modules` 模块表格 / 移动卡片 | 是 | `ModulesView.vue` | 打开模块页 | 不新增全局 Jenkins 任务路由 |
| R2 | 模块行失败重试确认 | 是 | `ModulesView.vue` 或轻量确认组件 | 点击“一键失败重试” | 不进入 Jenkins 参数页 |
| R3 | 模块行模块重试确认 | 是 | `ModulesView.vue` 或轻量确认组件 | 点击“模块重试” | 不直接执行 pytest |
| R4 | 用例详情勾选与失败重试 | 是 | `CaseDetailsDialog.vue` | 打开详情弹窗 | 非失败用例不可勾选 |
| R5 | Jenkins 任务弹窗 | 是 | `JenkinsTasksDialog.vue` | 点击“Jenkins任务” | 不 iframe 嵌入 Jenkins 页面 |
| R6 | 取消任务与取消中状态 | 是 | `JenkinsTasksDialog.vue` | 点击取消任务 | `canceling` 不提前释放锁的提示不可省略 |
| R7 | 报告和 Jenkins 外链 | 是 | 新页打开链接 | 点击查看报告 / 查看 Jenkins 任务 | 不叠加平台 Cookie 验证 |
| R8 | 锁冲突和 disabled reason | 是 | 按钮 tooltip、toast、弹窗内错误 | 后端返回 409 或 actions reason | 不用模糊文案替代固定提示 |
| R9 | Jenkins 参数页、构建详情页、Allure 外部页面 | 否 | 外部系统页面 | 点击外链后由浏览器新页展示 | 不进入 Vue DOM，不纳入 Playwright 当前页面截图断言 |
| R10 | 设计标注层、箭头、红框、说明文字 | 否 | 原型说明文档 | 不适用 | 不实现为产品 UI |

## 5. 前端实现范围映射

| 前端区域 | Route | 组件 / 文件建议 | 用户动作 | API / 数据 | 验收点 |
| --- | --- | --- | --- | --- | --- |
| 模块行操作 | `/modules` | `ReadOnlyActionButtons.vue` 改为可执行动作组件 | 点击失败重试、模块重试、Jenkins 任务 | `ModuleSnapshot.actions` | TC-P5-F7-001~004 |
| 失败重试确认 | `/modules` | `ModulesView.vue` 内确认状态或 `ExecutionConfirmDialog.vue` | 确认提交 | `POST /failed-case-retries` | TC-P5-F4-001/004/006 |
| 模块重试确认 | `/modules` | `ExecutionConfirmDialog.vue` | 确认提交 | `POST /module-reruns` | TC-P5-F5-001/002 |
| 用例详情勾选 | `/modules` | `CaseDetailsDialog.vue` | 勾选失败用例、提交重试 | `POST /failed-case-retries` | TC-P5-F4-002/007 |
| Jenkins 任务弹窗 | `/modules` | `JenkinsTasksDialog.vue` | 查看、取消、轮询 | `GET /jenkins-tasks`、`POST /cancel` | TC-P5-F6-001~006 |
| 外链跳转 | `/modules` | `JenkinsTasksDialog.vue` | 点击报告 / Jenkins | `allure_report_url`、`jenkins_build_url` | TC-P5-F6-003/004 |
| 移动端 | `/modules` | 既有模块卡片 + 新弹窗响应式 | 小屏访问 | 同桌面 API | TC-P5-F7-005 |

## 6. 模块行操作规格

- “一键失败重试”：仅在后端 `actions.failed_rerun=true` 时启用；点击后展示确认弹窗。
- “模块重试”：仅在 `actions.module_rerun=true` 时启用；确认文案说明会更新日期和执行时间。
- “Jenkins任务”：`actions.jenkins_tasks=true` 时启用；打开任务弹窗，默认查询 today。
- 禁用时必须能展示原因：无权限、无失败用例、已有执行中任务、Job 未配置。
- 提交中禁用同一行所有触发类按钮，避免重复提交；后端锁仍是最终防线。

## 7. 失败重试确认规格

- 模块行一键失败重试标题：`确认重试当前模块全部失败用例？`
- 详情勾选失败重试标题：`确认重试已勾选失败用例？`
- 详情一键失败重试标题：`确认重试当前模块全部失败用例？`
- 内容显示环境、模块名、失败用例数量、重试类型和“不会更新日期与执行时间”提示。
- 成功后显示任务编号和“可在 Jenkins 任务中查看进度”，并刷新模块任务弹窗数据。
- 锁冲突展示固定文案“已有用例重试，无法执行！”。

## 8. 模块重试确认规格

- 标题：`确认重试当前模块全部用例？`
- 内容显示环境、模块名、用例包名、当前日期/执行时间和“完成后会更新日期与执行时间”提示。
- 成功后刷新模块行、任务弹窗和趋势入口数据。
- 若已有锁，展示固定冲突文案。

## 9. 用例详情扩展规格

- 默认仍筛选失败用例。
- 仅 `display_status=failed` 且 `actions.can_retry=true` 的当前用例可勾选。
- 非失败用例、归档用例、无权限用例的勾选框禁用并有 reason。
- 勾选重试按钮在没有选中项时禁用。
- 弹窗内“一键失败重试”不受当前筛选输入影响，始终请求当前模块全部当前失败用例。

## 10. Jenkins 任务弹窗规格

- 标题：`{module_name} / 今日 Jenkins 任务`。
- 筛选：默认 today；本阶段可保留日期和状态筛选，不新增全局路由。
- 列：任务编号、任务类型、Job 名、环境 URL、状态、触发人、开始时间、结束时间、操作。
- 状态标签：
  - `queued`：排队中
  - `running`：执行中
  - `success`：通过
  - `test_failed`：用例失败
  - `failed`：执行失败
  - `canceling`：取消中
  - `canceled`：已取消
- 操作：
  - 取消任务：仅 `queued/running` 且有权限时可用。
  - 查看报告：有 `allure_report_url` 时可用。
  - 查看 Jenkins 任务：有 `jenkins_build_url` 时可用。
- 轮询：弹窗打开且存在 `queued/running/canceling` 时每 5 秒刷新；关闭弹窗停止。

## 11. 覆盖校准

| AC / 用例 | UI 覆盖点 | 状态 |
| --- | --- | --- |
| AC-P5-4.1 | R2 模块行一键失败重试确认 | 已覆盖 |
| AC-P5-4.2 | R4 详情勾选失败重试 | 已覆盖 |
| AC-P5-4.3 | R4 详情一键失败重试范围说明 | 已覆盖 |
| AC-P5-4.4 | R8 无失败用例 disabled reason | 已覆盖 |
| AC-P5-4.6 | R2 确认文案说明日期/执行时间不更新 | 已覆盖 |
| AC-P5-5.1 | R3 模块重试确认 | 已覆盖 |
| AC-P5-5.2 | R3 确认文案说明日期/执行时间更新 | 已覆盖 |
| AC-P5-5.4 | R8 锁冲突固定文案 | 已覆盖 |
| AC-P5-6.1 | R5 Jenkins 任务弹窗 | 已覆盖 |
| AC-P5-6.2 | R6 取消任务和 canceling 状态 | 已覆盖 |
| AC-P5-6.3 | R7 查看报告外链 | 已覆盖 |
| AC-P5-6.4 | R7 查看 Jenkins 任务外链 | 已覆盖 |
| AC-P5-6.5 | R5 5 秒轮询与关闭停止 | 已覆盖 |
| AC-P5-7.1~7.5 | R1/R8/R5 按钮状态、反馈、移动端 | 已覆盖 |

## 12. 前端开发冻结说明

- 不新增 `/jenkins-tasks` 路由。
- 不把 Jenkins 参数页、Allure 报告页、Jenkins 构建详情嵌入当前 Vue DOM。
- 不让前端直接调用 Jenkins。
- 不在前端硬编码 Jenkins/Allure base URL。
- 失败重试、模块重试和取消任务都必须经 DRF API。
- 外链打开由后端返回可信链接，前端只负责新页打开。
