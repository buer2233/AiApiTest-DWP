# 环境与模块通过率页面-Jenkins执行闭环二次验收修复-UI区域语义拆解与实现范围映射

## 1. 原型范围

本阶段不新增页面与布局，沿用 Stage9 Jenkins 任务弹窗高保真原型，仅补充已完成任务的禁用视觉和报告链接行为。不存在复合图片或设计标注层进入 DOM 的情况。

## 2. 区域语义拆解

| 区域 | 语义 | 处理方式 |
| --- | --- | --- |
| R1 | 模块列表“Jenkins 任务”入口 | 当前 `/modules` 页面直接展示 |
| R2 | Jenkins 任务弹窗桌面表格 | 弹窗展示 |
| R3 | Jenkins 任务弹窗移动卡片 | 响应式状态展示 |
| R4 | 已完成任务取消按钮 | disabled 灰色状态，不触发请求 |
| R5 | 查看报告 | 新窗口进入具体 Jenkins build `/allure/` |
| R6 | Jenkins console/Allure 页面 | Jenkins 外部页面，不在 Vue DOM 内实现 |

## 3. 前端实现范围映射

| UI 区域 | 用户路径 | Vue route | 组件落点 | 初始可见 | Playwright 断言 |
| --- | --- | --- | --- | --- | --- |
| R1 | 登录后模块页 | `/modules` | `ModulesView.vue` | 是 | Jenkins 任务入口可见 |
| R2 | 点击 Jenkins 任务 | `/modules` | `JenkinsTasksDialog.vue` 桌面表格 | 否 | 弹窗出现且任务行可见 |
| R3 | 移动视口点击入口 | `/modules` | `JenkinsTasksDialog.vue` 移动卡片 | 否 | 390px 下卡片可见且无溢出 |
| R4 | 查看已完成任务 | `/modules` | `.secondary-button:disabled` | 条件可见 | `disabled=true`，计算样式为灰色且 cursor=not-allowed |
| R5 | 点击查看报告 | `/modules` -> Jenkins | `<a target="_blank">` | 条件可见 | popup URL 以 `/<build>/allure/` 结尾 |

## 4. 视觉状态

- 正常次按钮：暖白背景、正文色文字、hairline 边框。
- 禁用次按钮：`surface-soft` 灰色背景、`muted` 灰色文字、弱化边框，不使用品牌主色。
- 禁用态仍保持 38px 稳定高度和 8px 圆角，不因状态切换导致布局位移。
