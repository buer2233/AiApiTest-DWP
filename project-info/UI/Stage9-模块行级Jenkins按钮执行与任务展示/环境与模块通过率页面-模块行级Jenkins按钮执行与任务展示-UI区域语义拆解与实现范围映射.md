# 环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示 UI 区域语义拆解与实现范围映射

## 区域语义拆解

| 区域 | 截图内容 | 前端处理方式 | 说明 |
| --- | --- | --- | --- |
| R1 | 模块通过率页面主体 | 当前页面直接展示 | `/modules` 的筛选、表格、分页继续保留。 |
| R2 | 一键失败重试按钮 | 当前页面直接展示 | 落点 `ReadOnlyActionButtons.vue`，点击后由 `ModulesView.vue` 调用失败重试接口。 |
| R3 | 模块重试按钮 | 当前页面直接展示 + 确认弹窗 | 落点 `ReadOnlyActionButtons.vue` 和 `ModulesView.vue` 的 Element Plus 确认弹窗。 |
| R4 | Jenkins 任务按钮 | 当前页面直接展示 + 弹窗 | 落点 `JenkinsTasksDialog.vue`。 |
| R5 | 红框标注 | 仅设计说明不实现 | 不进入产品 DOM、截图验收和 Playwright 断言。 |
| R6 | Jenkins 外部任务页 / Allure 报告页 | 新页打开 | 不 iframe 嵌入 Vue，不直连 Jenkins API。 |

## 前端实现范围映射

| UI 区域编号 | 用户路径 | Vue route | 组件落点 | 用户动作 | 初始是否可见 | Playwright 断言 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | 打开模块通过率页 | `/modules` | `ModulesView.vue` | 进入页面 | 是 | 表格展示后置能力列和三个按钮。 |
| R2 | 点击一键失败重试 | `/modules` | `ReadOnlyActionButtons.vue` -> `ModulesView.vue` | 点击按钮 | 是 | 无确认弹窗，调用失败重试 API，提示“开始执行失败重试”。 |
| R3 | 点击模块重试 | `/modules` | `ReadOnlyActionButtons.vue` -> `ModulesView.vue` | 点击按钮 | 是 | 出现固定确认文案，确认后调用模块重试 API。 |
| R4 | 点击 Jenkins 任务 | `/modules` | `JenkinsTasksDialog.vue` | 点击按钮 | 弹窗初始不可见 | 弹窗展示任务类型、状态、日期筛选、外链和空态/分页。 |
| R5 | 查看标注层 | 无 | 无 | 无 | 否 | 红框、箭头、说明文字不得出现在 DOM。 |
| R6 | 查看外链 | 外部系统 | 普通链接 | 点击查看报告 / 查看 Jenkins 任务 | 否 | 链接 `target=_blank` 且 href 来自后端响应。 |

## 组件边界

- `ModulesView.vue`：模块页状态编排、触发失败重试/模块重试、接收弹窗事件后刷新模块列表。
- `ReadOnlyActionButtons.vue`：只负责按钮展示、loading、disabled reason 和 emit，不直接调用 API。
- `JenkinsTasksDialog.vue`：负责当前模块任务列表、筛选、取消、单任务同步轮询和事件上报。
- `metrics.ts`：只封装 DRF API，不拼 Jenkins URL。

## 视觉说明

- 延续现有管理后台紧凑表格风格，不新增营销式区块。
- 按钮保留现有 8px 圆角和紧凑尺寸，避免后置能力列横向溢出。
- 红框为需求标注，不作为产品视觉资产。
