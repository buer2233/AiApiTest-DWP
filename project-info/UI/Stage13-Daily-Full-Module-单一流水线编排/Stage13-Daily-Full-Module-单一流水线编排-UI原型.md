# Stage13-Daily-Full-Module-单一流水线编排 UI 原型

## 1. 资料状态

| 项 | 内容 |
| --- | --- |
| 需求状态 | 已冻结，依据需求说明 v1.8（2026-07-19） |
| 本阶段状态 | 主人已于 2026-07-20 选择 C01；该候选作为正式前端视觉基准，进入 Vue TDD 实施 |
| 覆盖页面 | 已登录受保护路由 `/environments`：环境通过率与管理员环境目录管理 |
| 非范围 | Daily 模块子任务 UI、Worker UI、模块选择器、Jenkins 凭据与真实环境地址 |
| 输入来源 | `project-info/demand/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-需求说明.md` 的 §3、§7、§8、§11、AC2.1-AC3.8；功能测试用例完成后须按同名 Stage13 用例补做覆盖校准 |
| 原型产物 | 5 张同范围桌面候选图；仅模拟 admin 视角的初始正常态，弹窗和异常态以本说明定义为准 |

本页的单一工作目标是：让成员快速确认某一启用测试环境的通过率和模块快照；让管理员安全地维护环境目录，并明确看见 MySQL 与 YAML 的同步状态、冲突和后续动作。页面不展示 Daily 的模块子任务，Daily 相关信息仅保留为既有父任务和父级报告入口的导航语义，不能借此需求扩展模块执行控制台。

## 2. 设计基线与校准

### 2.1 DESIGN-claude.md 对齐

| 维度 | 原型约束 | 前端落地要求 |
| --- | --- | --- |
| 画布与表面 | 主画布 `#faf9f5`；数据区和筛选区使用 `#f5f0e8` / `#efe9de`；仅同步状态摘要可用 `#181715` 深色面 | 页面区块不悬浮成卡片堆；同类表格保持 1px `#e6dfd8` 分隔 |
| 色彩语义 | 主操作为珊瑚 `#cc785c`，按下为 `#a9583e`；成功 `#5db872`、警告 `#d4a017`、错误 `#c64545`；禁止用珊瑚表达成功或失败 | 不把暖珊瑚滥用于状态标签；状态必须同时显示文本与颜色 |
| 字体 | 页面名使用 Copernicus/Tiempos Headline/serif 的 28px；正文为 StyreneB/Inter/sans-serif 14px；表格 key/URL 使用 JetBrains Mono 13px | 不使用营销式超大标题；紧凑管理面保持字距 0 |
| 间距与圆角 | 4/8/12/16/24/32px 间距；输入和按钮高 40px；表格行 56px；圆角最大 8px | 表格、工具栏和弹窗保持稳定尺寸；禁止胶囊化文字操作按钮 |
| 组件方式 | 主按钮为“新建环境”；次操作为“同步测试环境数据”；行内编辑、停用采用带文字的可辨识命令；无文字工具操作使用 Lucide 图标并配悬浮提示 | 新建、编辑和同步统一走可轮询的同步请求；不把敏感 Git 或 Jenkins 细节作为可编辑字段 |
| 响应式 | 桌面在 1280px 以上展示左右分栏；768-1279px 折叠为纵向；小于 768px 将管理表转为环境摘要列表或可横滑表格 | 不能挤压 URL、描述和操作；文本换行或截断都要保留完整值的可访问提示 |

`ui-ux-pro-max` 的检索结论仅采纳“数据密集仪表盘、可筛选表格、移动端表格不得溢出、错误须可读出且有恢复路径”的交互原则；其推荐的深蓝/绿色品牌方案与项目 `DESIGN-claude.md` 冲突，明确不采用。

### 2.2 共同信息架构

```text
/environments（受保护）
├─ 环境快照：环境选择、通过率、统计、模块快照入口
└─ 仅 admin 的环境目录
   ├─ 筛选与同步状态
   ├─ 环境管理表
   ├─ 新建 / 编辑环境弹窗
   └─ YAML 导入、冲突详情和重试抽屉
```

## 3. 候选图生成记录

### 3.1 工具可用性与替代记录

已按 `imagegen` 技能尝试调用内置 `image_gen`，运行环境返回 `tools.image_gen is not a function`，没有可用的内置图像生成接口。根据 `project-info/UI/AGENTS.md`，此原因、替代方案与风险必须留档：本批候选图改为以相同的高保真 UI 规范在受控浏览器中渲染为 PNG，文件名维持既定 `-imagegen.png` 归档格式以符合阶段检索规则，但内容并非由 `imagegen` 模型生成。风险是视觉素材的非确定性探索较少；功能范围、布局、密度和状态语义不受影响。请主人在选择候选时一并确认此替代视觉产物可作为 Figma 正式稿的输入；未确认前不得进入 Figma。

### 3.2 共同生成约束

所有候选均为 1440x1000 桌面 admin 初始态，使用脱敏示例 `https://test.example.invalid`，不含真实地址、token、密码、营销 hero、模块子任务或模块子任务按钮。统一展示：环境选择、通过率、环境统计、环境 key / 名称 / URL / 描述 / 启停 / 目录同步状态、`新建环境` 与 `同步测试环境数据` 两项主要操作。中文文案为原型示意，最终实现以产品文案和可访问标签为准。

| 编号与路径 | imagegen 提示词（可复用） | 有意义差异 | 适用性、风险与 DESIGN-claude 贴合度 |
| --- | --- | --- | --- |
| C01 [候选图](Stage13-Daily-Full-Module-单一流水线编排-candidate-01-imagegen.png) | `ui-mockup；1440x1000；企业测试环境通过率与 admin 目录；暖白 #faf9f5、深墨 #141413、珊瑚 #cc785c；上方一行环境快照 KPI，下方全宽环境表，右上新建与 YAML 同步；紧凑表格、无营销页、无模块子任务、无真实地址。` | **全宽台账**：快照条带在上，管理表占主视觉，筛选和操作贴近表格。 | 最适合高频批量管理与扫描。风险是首屏管理感更强、通过率趋势弱。贴合度高。 |
| C02 [候选图](Stage13-Daily-Full-Module-单一流水线编排-candidate-02-imagegen.png) | `同共同约束；左侧窄栏放环境快照、通过率和同步状态，右侧为管理表与操作；克制的深色同步状态面。` | **双栏工作台**：快照固定为左栏，表格为右侧主区。 | 最适合需持续对照通过率和目录状态的运维。风险是中等屏幕更早折叠。贴合度高。 |
| C03 [候选图](Stage13-Daily-Full-Module-单一流水线编排-candidate-03-imagegen.png) | `同共同约束；上方横向摘要与活跃环境切换器，下方将每个环境做为一张紧凑可展开的管理行；同步状态展示为明确时间线。` | **环境行优先**：从传统列式表转为可展开的环境台账行，同步状态可读性最高。 | 最适合环境数量较少、需要查看描述和同步审计的场景。风险是大量环境时密度下降。贴合度中高。 |
| C04 [候选图](Stage13-Daily-Full-Module-单一流水线编排-candidate-04-imagegen.png) | `同共同约束；目录同步控制作为顶部深色操作条，下面是高密度表格；冲突行使用错误色和“先导入 YAML”恢复动作。` | **同步优先**：将目录状态、待同步和冲突处置前置为一条操作带。 | 最适合频繁人工编辑 YAML、需要处理冲突的管理员。风险是 member 视图需彻底隐藏该带。贴合度高。 |
| C05 [候选图](Stage13-Daily-Full-Module-单一流水线编排-candidate-05-imagegen.png) | `同共同约束；上方为环境选择和模块快照，下方管理表采用右侧检查器栏；选中环境的目录详情、同步状态和管理操作在检查器中完成。` | **检查器路径**：表格负责筛选、选择与比较，右侧检查器负责单环境编辑和同步详情。 | 最适合较长 URL/描述和单条处理。风险是批量扫描时需移动视线。贴合度中高。 |

### 3.3 正式视觉基准

主人已选择 [C01 候选图](Stage13-Daily-Full-Module-单一流水线编排-candidate-01-imagegen.png) 作为本阶段正式视觉基准。前端采用其“顶部环境快照条带 + 下方全宽环境台账”的信息结构：R1 保持紧凑的概览与选择，R2 是页面主视觉；不改用 C02-C05 的固定双栏、环境行、同步优先带或检查器布局。

该 PNG 是受控浏览器渲染的高保真替代产物，主人本次选择同时确认它可以替代当前不可用的 `imagegen` 原始产物作为前端实现输入。它仍然只定义初始 admin 正常态，R3/R4、member 权限态以及加载、空、错误、冲突和响应式状态继续严格依据本文件的区域映射与状态规格实现。

### 3.4 人工校准结论

- 五个候选严格使用同一数据字段、权限边界和同步状态；差异只在信息密度、管理表组织、同步状态呈现和操作路径。
- 所有候选将同步状态文本化（`已同步`、`待同步`、`冲突`），不会仅以颜色表达状态。
- 候选只示意 admin 正常态；member 视图、编辑弹窗、导入/冲突抽屉和加载/空/错误状态不与主页面同屏，按 §4 和 §6 单独实现。
- C01 已由主人选择；本阶段直接以其作为 Vue 正式实现的视觉基准，不额外创建或导出 Figma 稿。

## 4. 区域语义拆解

| 区域 | 图片位置与类型 | 是否进入前端 | 前端落点 | 触发条件 | 禁止项 |
| --- | --- | --- | --- | --- |
| R1 环境快照主体 | 候选图顶部或左侧，产品页面 | 是 | 路由 `/environments`，`EnvironmentsView` / `EnvironmentSnapshotPanel` | 已登录的 member 或 admin 初始进入 | 不出现管理表的 admin 操作、同步诊断或编辑表单；不展示 Daily 模块子任务 |
| R2 环境管理表 | 候选图主区域，产品页面 | 是，仅 admin | `EnvironmentsView` / `EnvironmentCatalogTable` | admin 初始进入或环境切换完成 | member DOM 不渲染此区；不得将 R3/R4 的弹窗和抽屉常驻同屏 |
| R3 新增 / 编辑环境 | 不在候选正常态中常驻，弹窗 | 是，仅 admin | `EnvironmentEditorDialog` | 点击“新建环境”或表格行“编辑”；编辑时 key 只读 | 不与 YAML 导入/冲突抽屉并列；不能提供修改 `env_key` 或直接编辑 SHA 的控件 |
| R4 YAML 导入、冲突和重试 | 不在候选正常态中常驻，弹窗/抽屉 | 是，仅 admin | `EnvironmentCatalogSyncDialog` / `EnvironmentCatalogSyncDrawer` | 点击“同步测试环境数据”、点击同步状态或重试；轮询同步请求 | 不与 R3 同时打开；不展示 Git 凭据、真实 Jenkins token、私有 URL、模块子任务 |

候选图中如有用于解释布局的非产品性标号、辅助线或说明，均视为 `设计标注层`，不进入产品 DOM、Playwright 截图或断言。本批 PNG 不添加红框、箭头或说明性悬浮文本。

## 5. Vue 范围冻结映射

| UI 区域 | Vue route | 组件 / 弹窗 | 用户动作 | Playwright 验收点 |
| --- | --- | --- | --- | --- |
| R1 | `/environments` | `EnvironmentsView`、`EnvironmentSnapshotPanel`、`EnvironmentSelector`、`ModuleSnapshotLink` | 选择启用环境；进入模块快照 | 可切换已启用环境；显示通过率、统计、模块快照入口；没有模块子任务列表 |
| R2 | `/environments` | `EnvironmentCatalogSection`、`EnvironmentCatalogTable`、`CatalogSyncStatus` | 按名称/key/状态筛选；点击行内编辑、停用/恢复、同步状态 | admin 可见且可操作；member 看不到管理区域且不会请求 admin 写接口 |
| R3 | 同 route，受控弹窗 | `EnvironmentEditorDialog` | 点击新建/编辑，提交或取消 | 创建、更新、字段错误、提交中、成功后 `202` 同步状态均可见；编辑 key 只读 |
| R4 | 同 route，受控弹窗/抽屉 | `EnvironmentCatalogSyncDialog`、`EnvironmentCatalogSyncDrawer` | 发起 YAML 导入、查看状态、重试失败、处理冲突 | `pending/queued/running/synced/failed/conflict` 文本明确；冲突只给“先导入 YAML”或“重新提交”恢复路径 |

### 5.1 C01 组件边界与数据流

| 组件 / 组合式函数 | 单一职责 | 输入 / 输出 |
| --- | --- | --- |
| `EnvironmentsView` | 作为受保护路由的组合面，放置 R1 与仅 admin 的 R2-R4 容器。 | 从既有环境快照逻辑取得 R1；读取 `authStore.isAdmin`，仅为 admin 挂载 `EnvironmentCatalogSection`。 |
| `EnvironmentSnapshotPanel` | 展示和切换启用环境、最新通过率、统计和模块快照入口。 | 接收 R1 环境与汇总数据；向上发出环境切换。 |
| `EnvironmentCatalogSection` | 编排 C01 的管理工具栏、状态摘要、筛选、表格和受控弹窗。 | 使用 `useEnvironmentCatalog`；向子组件传入只读数据，接收筛选、编辑、停用、导入和重试事件。 |
| `EnvironmentCatalogTable` | 只渲染可扫描的全宽环境台账及行级管理操作。 | 接收筛选后的环境、目录状态和加载态；发出 `edit`、`toggle-active` 与 `show-sync`。 |
| `EnvironmentEditorDialog` | 维护新增或编辑表单；编辑时显示不可编辑的 `env_key`。 | 通过 `v-model` 控制可见性；接收编辑目标并发出 `submit`。 |
| `EnvironmentCatalogSyncDialog` / `EnvironmentCatalogSyncDrawer` | 发起 YAML 导入，展示异步同步状态、脱敏诊断、失败重试或冲突恢复路径。 | 接收当前同步尝试与加载态；发出 `import`、`retry`、`close`。 |
| `useEnvironmentCatalog` | 将目录读取、CRUD、同步轮询与错误恢复集中为可测试状态逻辑。 | 返回只读的列表、目录状态和当前尝试，以及显式加载、提交、导入、重试动作。 |

数据按“API / composable -> 容器 -> 展示组件”的单向路径流动；表格、弹窗和抽屉只能通过明确事件向容器请求写入，任何子组件不得直接修改传入的环境或同步对象。

## 6. 数据、接口与状态

### 6.1 API 字段映射

| 组件 | API | 读取 / 写入字段 | 状态与反馈 |
| --- | --- | --- | --- |
| 环境选择和快照 | `GET /api/v1/test-environments?is_active=true` 与既有快照接口 | `id`、`env_key`、`env_name`、`base_url`、`url_desc`、`is_active`、环境通过率、统计、模块快照链接 | 初始 skeleton；空态引导联系管理员；读取失败显示可重试错误块 |
| 管理表 | `GET /api/v1/test-environments` | 同上及目录状态 `yaml_blob_sha`、`status`、`last_synced_at`、`last_error_code`、`last_error_summary` | 与 R1 独立加载；URL 默认截断、悬浮/辅助文本查看完整值；脱敏错误可展开 |
| 新增 | `POST /api/v1/test-environments` | `env_key`、`url_name`、`base_url`、`url_desc`；响应环境与 `sync_attempt` | `202` 后显示 `pending`，轮询同步请求；`400/403/409` 就地提示 |
| 编辑/停用/恢复 | `PATCH /api/v1/test-environments/{id}`、`DELETE /api/v1/test-environments/{id}` | 编辑仅 `url_name`、`base_url`、`url_desc`、`is_active`；删除为逻辑停用 | `202` 后刷新行与状态；停用前确认，保留历史说明 |
| YAML 导入与重试 | `POST /api/v1/test-environments/sync-from-yaml`、`GET /api/v1/environment-catalog-sync-attempts/{id}`、`POST /api/v1/environment-catalog-sync-attempts/{id}/retry` | `direction`、`status`、`expected_yaml_blob_sha`、`observed_yaml_blob_sha`、`queue_id`、`build_number`、`jenkins_build_url`、`commit_sha`、`error_code`、`error_summary` | `202` 后轮询；只展示脱敏诊断和允许的 Jenkins 链接；冲突不允许直接覆盖 |

### 6.2 状态规格

| 场景 | R1 | R2 | R3 | R4 |
| --- | --- | --- | --- | --- |
| 加载 | 固定高度 skeleton，避免 KPI 位移 | 表头和 5 行骨架，操作禁用 | 提交按钮显示加载，其他字段不可编辑 | 明示 `pending/queued/running`，每次轮询有可见更新时间 |
| 空数据 | 未有启用环境：说明环境不可选，member 无操作入口 | admin 表为空时提供“新建环境”；member 不渲染 | 无 | 未有历史请求：显示当前无同步记录 |
| 校验 / 错误 | 接口错误块含“重试” | 行级错误不抹去已加载数据 | 字段下方给出错误，`role=alert`；保留用户输入 | 失败显示脱敏错误、重试条件；冲突显示 SHA 不一致及两条恢复路径 |
| 权限 | member 仅可选启用环境和查看快照 | admin 才渲染；403 后隐藏/刷新权限状态，绝不保留可操作控件 | admin 外不可打开 | admin 外不可打开；403 不泄露同步审计 |
| 响应式 | 1280px+ 并列；768px 起纵向 | 小屏用摘要列表或横向滚动容器，操作收至行菜单 | 480px 以下全屏抽屉，底部固定保存区 | 480px 以下全屏抽屉，长 SHA/URL 可换行且可复制 |

## 7. 测试用例覆盖校准

已依据 `../../test_case/Stage13-Daily-Full-Module-单一流水线编排/Stage13-Daily-Full-Module-单一流水线编排-测试用例.md` 与同名 RTM 完成校准：27 条测试用例覆盖 AC1.1 至 AC4.2 共 18 条验收标准。

| 测试覆盖重点 | UI 映射结论 |
| --- | --- |
| AC2.1、AC2.2：Daily 仅有父任务和唯一 Allure | R1 只保留既有环境快照、模块快照入口与父级报告导航语义；不增加模块子任务、模块级 Allure 或 Daily 触发按钮。 |
| AC3.2、AC3.5、AC3.6：CRUD、异步状态、失败与冲突恢复 | R2 显示最近同步状态和脱敏错误；R3 覆盖表单校验和提交中；R4 覆盖 `pending/queued/running/synced/failed/conflict`、重试与两条冲突恢复路径。 |
| AC3.4、AC3.7：YAML 导入和成员权限 | R4 仅 admin 可进入；member 不渲染 R2-R4 且不会调用写接口。 |
| TC-S13-F3-014：加载、空、错误、响应式 | §6.2 已冻结 R1-R4 的加载、空、校验/错误、权限与 375/768/1024/1440px 响应式要求。 |

校准结论：测试用例没有引入新的 UI 区域、字段或权限边界；R1-R4 映射和已选择的 C01 可作为前端 TDD 输入。

## 8. 前端交付前门禁

- C01 已由主人选择，并已确认浏览器渲染候选图可替代当前不可用的 `imagegen` 产物；前端可进入 TDD 实施。
- 前端正式实现须以 C01 为视觉基准，补齐 R3/R4、member 权限态、加载/空/错误/冲突态和 375/768/1024/1440px frame；不得把复合状态画到 `/environments` 初始屏。
- 前端开发须引用本文件的 R1-R4 映射、API 字段和状态表，并在功能测试用例完成后执行覆盖校准。API 未实现或候选未选择前，不得启动 Vue 编码。

## 9. 变更记录

| 日期 | 版本 | 变更 |
| --- | --- | --- |
| 2026-07-19 | 0.1 | 基于冻结 Stage13 规格建立 5 张 UI 候选、R1-R4 语义拆解、Vue 范围映射和状态设计；等待主人选择，未进入 Figma。 |
| 2026-07-19 | 0.2 | 完成功能测试用例覆盖校准：27 条用例、18 条 AC，未新增 UI 范围。 | 进入前端 TDD 前置门禁。 |
| 2026-07-20 | 1.0 | 主人选择 C01 全宽环境台账，并确认受控浏览器渲染候选可作为正式前端视觉输入；解除前端实施门禁。 |
