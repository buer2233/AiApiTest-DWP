# 环境与模块通过率页面-P2-测试数据底座与只读通过率页面-UI候选图

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P2-测试数据底座与只读通过率页面 |
| 阶段 | Stage3-P2测试数据底座与只读通过率页面 |
| 本次范围 | 仅完成 UI 阶段：5 张候选图、候选差异说明、区域语义拆解输入 |
| 输入需求 | `project-info/demand/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-需求说明.md` |
| 输入测试用例 | `project-info/test_case/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-功能测试用例.md` |
| 输入 RTM | `project-info/test_case/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-可追溯矩阵.md` |
| 设计基线 | 根目录 `DESIGN-claude.md` |
| 生成方式 | Codex `/imagegen` 内置图片生成 |
| 生成日期 | 2026-07-04 |
| 当前状态 | 已确认融合方案并完成前端落地 |

## 设计约束

- 严格继承 `DESIGN-claude.md`：warm cream canvas `#faf9f5`、coral primary `#cc785c`、ink `#141413`、hairline `#e6dfd8`、surface-card `#efe9de`、dark product surface `#181715`。
- 管理后台设计以“安静、紧凑、可扫描”为核心，不做营销 hero、不做装饰性插画、不使用渐变光球。
- 功能范围只覆盖 P2 冻结内容：`/environments` 环境通过率页、`/modules` 模块通过率页、加载态、空态、错误态、后端分页筛选、生成环境报告占位提示。
- 不实现 P3-P5 能力：用例详情、趋势弹窗、失败重试、模块重试、Jenkins 任务、真实 AI 报告均不得作为可用操作出现。
- 通过率状态色必须使用 success/warning/error 语义色，coral 只做品牌主操作。
- 示例数据使用需求冻结数据和脱敏测试数据，不展示真实账号、密码、token、Cookie 或敏感地址。

## 候选差异目标

| 编号 | 方向 | 目标差异 |
| --- | --- | --- |
| 01 | Environment Overview Command Desk | 强化 `/environments` 环境汇总、报告占位、空态/错误态的同屏可理解性 |
| 02 | Module Table Operations Ledger | 强化 `/modules` 表格、筛选、分页和公式说明，最接近当前 Vue + Element Plus 实现 |
| 03 | Low Pass-Rate Diagnostic Console | 强化低通过率筛选、风险模块优先级和 P2 只读边界 |
| 04 | Split Environment-to-Module Drill Path | 强化环境页到模块页的用户路径，展示点击后独立路由预览 |
| 05 | Responsive Pass-Rate Review | 强化桌面表格到移动卡片的响应式转换与移动验收点 |

## 生成提示词摘要

> 5 张候选图均使用同一共享约束：企业级自动化测试平台、Stage3/P2 只读通过率页面、warm cream canvas、coral primary、深色产品面、管理后台密度、无登录注册、无设计标注层、无真实敏感信息、无 P3-P5 操作。

| 编号 | 提示词重点 |
| --- | --- |
| 01 | 生成 1440x900 桌面截图；当前 route 为 `/environments`；环境下拉、后端地址、环境汇总、96.00% 通过率、生成环境报告占位、模块通过率入口、空态和错误重试。 |
| 02 | 生成 1440x900 桌面截图；当前 route 为 `/modules`；环境/模块名/包名/模块测试/通过率上限筛选、表格、禁用后置操作、分页、公式说明、加载/空/错状态。 |
| 03 | 生成 1440x900 桌面截图；当前 route 为 `/modules`；突出低于 90% 模块、最高失败数、诊断条、warning/error 语义状态、P2 只读提示。 |
| 04 | 生成 1440x900 复合产品截图；左侧为当前 `/environments`，右侧为点击后 `/modules?environment_id=1` 独立路由预览；强调不得同屏误实现。 |
| 05 | 生成 1440x900 响应式候选图；左侧桌面 `/modules` 表格，右侧移动 `/environments` 卡片化布局；强调移动端无横向溢出。 |

## 候选图归档

| 编号 | 方向 | 图片路径 | 适合场景 | 风险 |
| --- | --- | --- | --- | --- |
| 01 | Environment Overview Command Desk | `project-info/UI/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-candidate-01-imagegen.png` | 环境页首版视觉基准；清楚覆盖 AC3.1-AC3.5 | 模块页信息较少，需另补模块页落稿 |
| 02 | Module Table Operations Ledger | `project-info/UI/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-candidate-02-imagegen.png` | 最适合作为 `/modules` 前端实现基准；贴近现有 `UsersView` 表格模式 | 页面右侧说明栏会占宽，窄屏需折叠 |
| 03 | Low Pass-Rate Diagnostic Console | `project-info/UI/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-candidate-03-imagegen.png` | 最适合突出低通过率筛选和风险模块优先级 | 引入诊断条，P2 前端实现时需保持只读，不得误做真实诊断功能 |
| 04 | Split Environment-to-Module Drill Path | `project-info/UI/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-candidate-04-imagegen.png` | 最适合解释环境页点击“模块通过率”后的跳转路径 | 属复合图，必须按区域语义拆解，不得整图复刻到一个 Vue 页面 |
| 05 | Responsive Pass-Rate Review | `project-info/UI/Stage3-P2测试数据底座与只读通过率页面/环境与模块通过率页面-P2-测试数据底座与只读通过率页面-candidate-05-imagegen.png` | 最适合做响应式验收参考；桌面/移动都有明确形态 | 桌面样例包含更多模块行，正式 P2 种子数据可少于图中数量 |

## 人工校准结论

- 5 张候选图均遵守 P2 只读范围，未把登录/注册/P1 认证区域带入 Stage3。
- 候选 01、02、03、05 为单 route 页面参考；候选 04 是复合产品图，必须在 UI 原型说明中拆解区域。
- 候选 02 与当前前端代码基线最贴近：`AppLayout`、左侧菜单、`page-panel`、筛选条、表格、分页均可承接。
- 候选 03 的诊断表达最强，但前端实现时应把“诊断”限制为筛选结果强调和只读说明，不引入真实分析能力。
- 候选 05 可作为移动端验收补充，不作为单独新增页面范围。

## 融合方案记录

| 候选 | 采纳方式 |
| --- | --- |
| 候选 02 | 作为 `/modules` 桌面表格、筛选、分页主基准 |
| 候选 03 | 采纳通过率语义状态与低通过率风险提示表达，不引入真实诊断能力 |
| 候选 05 | 采纳移动端卡片布局和无横向溢出验收要求 |
| 候选 01 | 采纳 `/environments` 汇总卡、报告占位和模块入口 |
| 候选 04 | 仅用于说明环境页到模块页跳转路径，不按复合图同屏实现 |

确认时间：2026-07-04

## 后续落稿结果

- 前端已按融合方案实现 `/environments` 与 `/modules`。
- 移动端 `/modules` 已按候选 05 映射为卡片布局。
- 生成环境报告、失败重试、模块重试、趋势和 Jenkins 任务仍保持 P2 占位/禁用边界。
- 关键截图已留存于 `历史验证记录（screenshots/，原本地临时证据已清理；请查询对应历史 Jenkins 构建归档）`。
