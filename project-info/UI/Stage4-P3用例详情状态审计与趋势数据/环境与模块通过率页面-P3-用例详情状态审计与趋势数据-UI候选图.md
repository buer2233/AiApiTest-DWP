# 环境与模块通过率页面-P3-用例详情状态审计与趋势数据 UI 候选图说明

## 1. 输入来源

| 类型 | 路径 / 来源 | 状态 |
| --- | --- | --- |
| 冻结需求 | `project-info/demand/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-需求说明.md` | 已冻结 |
| 功能测试用例 | `project-info/test_case/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-功能测试用例.md` | 已完成 |
| RTM 初稿 | `project-info/test_case/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-可追溯矩阵.md` | 已回填 UI 区域 |
| 视觉基线 | `DESIGN-claude.md` | 强制遵守 |
| UI 目录规则 | `project-info/UI/AGENTS.md` | 强制遵守 |

## 2. 设计约束

- P3 不新增独立页面，所有新增交互落在 `/modules` 当前路由内。
- 新增 UI 只包含：模块通过率详情入口、用例详情弹窗、状态修改确认弹窗、7/30 天趋势弹窗、权限态、加载/空/错误态、移动端适配。
- P3 不实现 Jenkins 任务弹窗、Allure 报告入口、失败重试执行、模块重试执行；相关按钮只能禁用或展示后续提示，不触发网络写请求。
- 视觉遵守 warm cream canvas `#faf9f5`、coral primary `#cc785c`、dark product surface `#181715`、hairline `#e6dfd8`、状态色 success/warning/error。
- 管理后台必须保持高密度、可扫描、工作台式布局；不得做营销页、夸张大卡片、装饰性插画或大面积渐变。
- 候选图如果包含说明箭头、标注或多状态拼图，必须在后续 UI 原型说明中拆为设计标注层，不进入前端 DOM。

## 3. 候选差异目标

| 候选 | 差异目标 | 适合验证的问题 |
| --- | --- | --- |
| 01 | 桌面高密度表格 + 右侧错误详情抽屉式区域 | 用例字段多时是否仍可快速扫描 |
| 02 | 桌面分栏弹窗：左表格、右状态审计/状态修改上下文 | 管理人员改状态时是否少跳转、少遮挡 |
| 03 | 趋势优先方案：上方轻量 SVG 折线，下方同源趋势表格 | 7/30 天趋势可读性和表格兜底 |
| 04 | 移动端近全屏弹窗 + 用例卡片列表 | 390px 宽度下无横向溢出和触控可用性 |
| 05 | 权限与异常态拼图：member 只读、空态、错误态、禁用重试 | 权限收敛和边界反馈是否完整 |

## 4. 统一 imagegen 提示词前缀

```text
Use case: ui-mockup
Asset type: enterprise web admin prototype candidate
Primary request: Create a high-fidelity UI prototype image for the AiApiTest-DWP enterprise automated testing platform, P3 case details, status audit, and trend data on the existing /modules page.
Style/medium: polished enterprise dashboard UI mockup, warm editorial Claude-like design language, dense but calm management console.
Color palette: warm cream canvas #faf9f5, soft cream cards #efe9de, coral primary #cc785c, coral active #a9583e, warm ink #141413, muted #6c6a64, hairline #e6dfd8, dark product surface #181715, success #5db872, warning #d4a017, error #c64545.
Typography: serif display used sparingly for major section titles, Inter-like humanist sans for dense UI labels and tables, JetBrains Mono style for node ids and stack snippets.
Core content: modules page table, case details dialog, failed/passed/skipped filters, case name/node id/error type filters, case result table, error summary/detail, admin-only status update confirmation with reason field, trend dialog with 7-day or 30-day SVG line chart and data table.
Constraints: no marketing hero, no decorative illustration, no real credentials, no real production URL, no Jenkins execution UI, no Allure report UI, no retry execution flow, no raw token/cookie/password text. Use Chinese UI labels. Do not use emoji. Keep controls compact and accessible.
Avoid: blue SaaS default theme, purple gradients, nested cards, rounded oversized cards, decorative blobs, large hero typography, placeholder lorem ipsum, unreadable tiny text, overlapping UI, text outside containers.
```

## 5. 候选图提示词

### Candidate 01：桌面高密度详情弹窗

```text
Build candidate 01 based on the unified prefix.
Composition: desktop 1440x960 screenshot of /modules page with a centered wide case details dialog open. Background shows the modules table dimmed but recognizable. Dialog header includes "示例模块1 / 模拟测试环境 / 用例详情" and a compact status summary.
Main layout: top filter bar with segmented status control "失败 / 通过 / 跳过", inputs "用例名", "来源 node id", "错误类型", buttons "查询" and "重置". Below, dense table with checkbox, 用例名, 来源, 简述, 错误类型, 断言, 执行状态, 错误摘要, 确认结果, 操作. Right side within dialog shows a narrow error detail preview panel for admin, using dark product surface and redacted stack text.
Show failed as default selected, one row with "AssertionError", one skipped and one passed row only as faint filter count chips, not mixed into failed results.
Interaction hints: disabled "失败重试" button with tooltip "后续阶段实现"; admin row action "修改状态".
```

### Candidate 02：管理人员状态修改上下文

```text
Build candidate 02 based on the unified prefix.
Composition: desktop 1440x960 screenshot showing case details dialog with a secondary status update confirmation modal layered above it.
Main focus: admin selects a failed case and opens "修改用例状态". Confirmation modal contains current status badge "失败", target status radio group "通过 / 跳过" with current status disabled, reason textarea labeled "修改原因", audit preview row "将写入 case_status_audit", primary coral button "保存修改", secondary button "取消".
Background details dialog remains visible but subdued, table row selected. Include after-submit preview chips showing module summary will refresh: failed 4 -> 3, skipped 2 -> 3, pass rate 96.00% -> 97.00%.
Error state snippet: reason field helper says "1-512 字，必填".
```

### Candidate 03：趋势弹窗优先

```text
Build candidate 03 based on the unified prefix.
Composition: desktop 1440x960 screenshot of /modules page with a trend dialog open after clicking "7天趋势"; include a clear tab or segmented switch for "近 7 天 / 近 30 天".
Main layout: top summary row with module name, package name, environment, latest pass rate. Middle shows a lightweight SVG-style line chart on cream surface with visible points, date labels, percentage axis, direct value labels on hover-style highlighted point. Bottom shows table with 日期, 运行类型, 总数, 失败, 跳过, 通过率, 执行时间.
Accessibility: include small text summary "近 7 天通过率由 94.00% 升至 97.00%" and show table as source of truth. No external chart library branding.
Actions: close button, retry button only for reloading trend data if load fails, not execution retry.
```

### Candidate 04：移动端详情弹窗

```text
Build candidate 04 based on the unified prefix.
Composition: mobile 390x844 responsive screenshot. Show /modules route with a near full-screen bottom-sheet style case details dialog open.
Layout: sticky dialog header with module name and close icon. Status segmented control wraps safely: "失败 / 通过 / 跳过". Filters collapse into a single "筛选" row. Case results become vertical cards, each card shows status badge, case name, node id in monospace, error type, assertion summary, error summary, confirmation result. Admin action is a compact "修改状态" button; member-only controls are absent.
Touch: all buttons at least 40px high, no horizontal overflow, long node id wraps or truncates with tooltip hint. Disabled retry action appears as text button disabled with reason.
```

### Candidate 05：权限、空态与错误态拼图

```text
Build candidate 05 based on the unified prefix.
Composition: desktop 1440x960 split into four clearly labeled product state panels, but labels must look like prototype frame names, not product UI text.
Panels:
1. Admin failed cases state with "查看详情" and "修改状态" visible.
2. Member read-only state with error detail action hidden and no status update controls.
3. Empty skipped state showing "暂无跳过用例" with reset/query controls still available.
4. Trend load failure state showing concise error and "重新加载" button.
Use subtle frame labels outside product surfaces to indicate candidate states; these labels are design annotations and must be excluded from frontend DOM later.
Emphasize permission clarity, disabled retry/Jenkins buttons with no side effects, and no exposure of sensitive stack details.
```

## 6. 生成与归档记录

| 候选 | 图片路径 | 生成状态 | 人工校准结论 |
| --- | --- | --- | --- |
| 01 | `project-info/UI/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-candidate-01-imagegen.png` | 已生成 | 可作为桌面用例详情弹窗主参考；右侧深色错误详情面板贴合设计基线，但候选图中的部分示例接口路径和真实业务字段不得直接进入实现。 |
| 02 | `project-info/UI/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-candidate-02-imagegen.png` | 已生成 | 可作为管理人员状态修改确认弹窗参考；统计刷新预览符合 AC5.9，但页面把“模块列表”画得偏独立模块详情，前端仍必须落在 `/modules` 弹窗内。 |
| 03 | `project-info/UI/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-candidate-03-imagegen.png` | 已生成 | 可作为趋势弹窗主参考；折线 + 表格 + 文本摘要完整覆盖 AC8，但实现时不得新增图表库。 |
| 04 | `project-info/UI/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-candidate-04-imagegen.png` | 已生成 | 可作为移动端近全屏弹窗参考；卡片化用例列表适合 390px 宽度，需在实现时隐藏“新建模块”等 P3 无关动作。 |
| 05 | `project-info/UI/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-candidate-05-imagegen.png` | 已生成 | 仅作为权限、空态、错误态局部参考；候选图出现“执行列表/趋势看板”等非 P3 当前 `/modules` DOM，必须列为设计标注层或废弃不实现。 |

## 7. 候选对比与推荐基准

| 候选 | 优点 | 风险 | 推荐用法 |
| --- | --- | --- | --- |
| 01 | 详情字段密度高，错误摘要/详情并列，适合后续测试定位 | 信息量较大，移动端不能直接复刻；局部文本不是冻结 API 字段 | 桌面用例详情弹窗主基准 |
| 02 | 状态修改路径清晰，原因必填、审计预览、统计刷新反馈完整 | 背景列表偏“模块列表”而非当前 P2 `/modules`；不能新增独立模块详情页 | 状态修改弹窗和成功反馈基准 |
| 03 | 趋势折线、表格、摘要同时出现，可测性强 | 图中有“返回列表”等不属于弹窗必要动作 | 趋势弹窗主基准 |
| 04 | 移动端无横向溢出，长 node id 卡片化处理合理 | 顶部“新建模块”不属于 P3 需求；需要继承 P2 移动端导航而非新增动作 | 移动端详情弹窗基准 |
| 05 | 权限态、空态、错误态覆盖直观 | 页面域漂移到执行列表/趋势看板，不能直接实现 | 仅提取状态表达，不作为页面结构 |

**自动推进基准**：按自主开发流水线，本阶段不等待 Figma 落稿；前端实现采用 `01 + 02 + 03 + 04` 的组合基准，`05` 仅作权限/空/错态参考。正式前端 DOM 以同目录 `...-UI原型.md` 的区域语义拆解和前端实现映射为准。

## 8. 独立审查处置

独立审查报告路径：`project-info/UI/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-UI候选图独立审查.md`。

| 审查发现 | 处置 |
| --- | --- |
| AC8.4 无历史趋势空态未被 5 张候选图覆盖，候选 05-4 是加载失败态而不是 `series=[]` 空态 | 已补充 `环境与模块通过率页面-P3-用例详情状态审计与趋势数据-trend-empty-state-imagegen.png`，正式原型新增 R12 趋势空态区域。 |
| 候选 01 容易把 P3 用例详情列表弹窗误实现成单条用例详情页 | 正式原型 R2 和 §6 明确：P3 是用例详情列表弹窗，必须包含状态筛选、组合筛选、分页和多行表格；单条详情页式信息架构不得实现。 |
| 候选 05 页面域漂移到执行列表/趋势看板 | 正式原型 R9/R10 明确：候选标题、说明文字、执行列表和趋势看板不进入 `/modules` 前端 DOM。 |

## 9. 补充图归档

| 补充图 | 图片路径 | 覆盖点 | 人工校准结论 |
| --- | --- | --- | --- |
| 趋势空态 | `project-info/UI/Stage4-P3用例详情状态审计与趋势数据/环境与模块通过率页面-P3-用例详情状态审计与趋势数据-trend-empty-state-imagegen.png` | AC8.4、TC-P3-F8-004 | 可作为 `series=[]` 空态视觉参考；保留“暂无趋势数据”“无历史记录”“切换 30 天”语义。图中“数据每 5 分钟自动更新”不是冻结需求，不进入前端 DOM。 |
