# 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 Jenkins Job 参数交互说明

## 1. UI 阶段裁剪说明

| 项 | 内容 |
| --- | --- |
| 输入来源 | 冻结需求：`project-info/demand/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-需求说明.md` v1.0 |
| 测试用例 | `project-info/test_case/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-功能测试用例.md` |
| 本阶段 UI 形态 | Jenkins Job 参数界面与人工验收交互说明 |
| 不生成候选图原因 | 主人已明确本阶段不开发平台前端/后端实际 Jenkins 执行对接；高保真 Vue 页面图会误导实现范围，因此按需求 §8 裁剪为 Jenkins Job 参数界面说明 |
| 前端实现范围 | 本阶段无 Vue route、组件、弹窗、Playwright 页面截图；下一阶段接入平台后再补充前端 UI 原型 |

## 2. 区域语义拆解

本阶段没有复合 UI 原型图，不存在图片区域拆解。为避免后续误实现，仍冻结以下语义映射：

| 区域编号 | 交互区域 | 区域类型 | 是否进入前端 | 前端落点 | 触发条件 | 禁止项 |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Jenkins 每日全量 Job 参数页 | Jenkins 外部系统页面 | 否 | 不进入 Vue DOM | 主人在 Jenkins 中打开 Job | 不在本阶段新增平台模块行按钮或任务弹窗 |
| R2 | Jenkins 失败重试 Job 参数页 | Jenkins 外部系统页面 | 否 | 不进入 Vue DOM | 主人在 Jenkins 中手工触发 | 不在本阶段启用前端“失败重试”或“一键失败重试” |
| R3 | Jenkins 模块重试 Job 参数页 | Jenkins 外部系统页面 | 否 | 不进入 Vue DOM | 主人在 Jenkins 中手工触发 | 不在本阶段启用前端“模块重试” |
| R4 | Jenkins 构建详情 / artifact / Allure 报告 | Jenkins/Allure 外链页面 | 否 | 不进入 Vue DOM | Jenkins 构建完成后访问 | 不叠加平台 Cookie 验证，不在本阶段做代理页面 |
| R5 | 后续平台任务弹窗与按钮 | 后续阶段平台页面 | 否 | 下一阶段另行设计 | 后续 DRF/Vue 接入后 | 不得在当前阶段提前实现 |

## 3. 前端实现范围映射

| 用户动作 | 当前阶段处理 | 后续阶段 Vue 映射 | 当前阶段测试依据 |
| --- | --- | --- | --- |
| 每日凌晨 2 点执行模块全量 | Jenkins Job cron 自动触发 | 后续仅展示同步后的任务和报告 | `TC-JENKINS-F-001` |
| 手工触发每日全量 | Jenkins Build Now / Build with Parameters | 后续不一定开放前端入口 | `TC-JENKINS-F-002` |
| 勾选失败用例后失败重试 | 当前阶段由 Jenkins 参数 `PYTEST_NODE_IDS` 模拟 | 后续失败用例弹窗按钮调用同一个后端接口 | `TC-JENKINS-F-004`、`TC-JENKINS-F-005` |
| 一键失败重试 | 当前阶段由 Jenkins 参数传入当前模块全部失败 node id 模拟 | 后续仅作为快速选择全部失败用例，不是另一条链路 | `TC-JENKINS-F-005` |
| 模块重试 | 当前阶段由 Jenkins 参数 `CASE_PATH` 模拟 | 后续模块行按钮调用模块重试接口 | `TC-JENKINS-F-007` |
| 查看 Jenkins / Allure | 当前阶段直接在 Jenkins 中查看 | 后续平台只保存并打开链接 | `TC-JENKINS-F-003`、`TC-JENKINS-F-006`、`TC-JENKINS-F-008` |

## 4. Jenkins Job 参数界面规格

### 4.1 每日全量模块执行 Job

| 项 | 规格 |
| --- | --- |
| Jenkinsfile | `jenkins/Jenkinsfile.daily-full-module` |
| Pipeline 脚本 | `jenkins/scripts/daily-full-module-pipeline.groovy` |
| 触发方式 | `0 2 * * *` 定时触发，也支持人工 Build Now |
| 执行模式 | 固定 `RETRY_MODE=none` |
| 后续同步语义 | 更新模块“日期”和“执行时间” |
| 模块路径默认值 | 每个模块 Job 必须设置 `JENKINS_MODULE_CASE_PATH`，作为 cron 触发时的 `CASE_PATH` 默认值 |

参数：

| 参数 | 控件类型 | 必填 | 默认值 | 校验 / 说明 |
| --- | --- | --- | --- | --- |
| `CASE_PATH` | 单行文本 | 是 | 当前 Job 的 `JENKINS_MODULE_CASE_PATH` | 当前模块 pytest 路径，不写本机绝对路径；缺失时构建明确失败 |
| `MODULE_NAME` | 单行文本 | 否 | 空 | Jenkins 展示用模块名，不影响 pytest 选择 |
| `RETRY_COUNT` | 单行文本 | 否 | `0` | pytest rerun 次数 |
| `CLEAN_ALLURE` | 布尔选择 | 否 | `true` | 是否清理历史 Allure 结果 |
| `OPEN_REPORT` | 布尔选择 | 否 | `false` | CI 中保持 `false` |

关键反馈：

- Console log 应显示进入每日全量脚本和 `RETRY_MODE=none`。
- Artifact 应包含 `api-test/runtime/ci-runs/<RUN_ID>/` 完整运行目录。
- Allure 插件存在时显示 Allure 报告入口；插件不存在时使用 artifact 中的 HTML 报告。

### 4.2 失败重试 Job

| 项 | 规格 |
| --- | --- |
| Jenkinsfile | `jenkins/Jenkinsfile.failed-rerun` |
| Pipeline 脚本 | `jenkins/scripts/failed-rerun-pipeline.groovy` |
| 触发方式 | 人工触发；后续由 DRF 触发 |
| 执行模式 | 固定 `RETRY_MODE=selected` |
| 后续同步语义 | 不更新模块“日期”和“执行时间” |

参数：

| 参数 | 控件类型 | 必填 | 默认值 | 校验 / 说明 |
| --- | --- | --- | --- | --- |
| `CASE_PATH` | 单行文本 | 是 | `test_case/test_gbif_case` | 当前模块路径，用于上下文和报告命名 |
| `PYTEST_NODE_IDS` | 多行文本 | 是 | 空 | 支持换行或英文逗号；为空必须失败，不允许误跑全模块 |
| `RETRY_COUNT` | 单行文本 | 否 | `0` | pytest rerun 次数 |
| `CLEAN_ALLURE` | 布尔选择 | 否 | `true` | 是否清理历史 Allure 结果 |
| `OPEN_REPORT` | 布尔选择 | 否 | `false` | CI 中保持 `false` |

关键反馈：

- `PYTEST_NODE_IDS` 为空时，构建应明确失败并提示必须提供失败用例 node id。
- 勾选失败用例与“一键失败重试”在 Jenkins 层没有区别，都是 `PYTEST_NODE_IDS` 列表。
- 不使用 `RETRY_MODE=all-failed`，避免依赖 Jenkins workspace 中的 `.pytest_cache` 推断平台失败用例。

### 4.3 模块重试 Job

| 项 | 规格 |
| --- | --- |
| Jenkinsfile | `jenkins/Jenkinsfile.module-rerun` |
| Pipeline 脚本 | `jenkins/scripts/module-rerun-pipeline.groovy` |
| 触发方式 | 人工触发；后续由 DRF 触发 |
| 执行模式 | 固定 `RETRY_MODE=module` |
| 后续同步语义 | 更新模块“日期”和“执行时间” |

参数：

| 参数 | 控件类型 | 必填 | 默认值 | 校验 / 说明 |
| --- | --- | --- | --- | --- |
| `CASE_PATH` | 单行文本 | 是 | `test_case/test_gbif_case` | 当前模块 pytest 路径 |
| `MODULE_NAME` | 单行文本 | 否 | 空 | Jenkins 展示用模块名 |
| `RETRY_COUNT` | 单行文本 | 否 | `0` | pytest rerun 次数 |
| `CLEAN_ALLURE` | 布尔选择 | 否 | `true` | 是否清理历史 Allure 结果 |
| `OPEN_REPORT` | 布尔选择 | 否 | `false` | CI 中保持 `false` |

关键反馈：

- Console log 应显示进入模块重试脚本和 `RETRY_MODE=module`。
- 不要求输入 `PYTEST_NODE_IDS`。
- Artifact 与 Allure 反馈同每日全量一致。

## 5. 人工验收路径

1. 在 Jenkins 中为每日全量创建一个模块 Job，加载 `jenkins/Jenkinsfile.daily-full-module`。
2. 配置该模块 Job 的 `JENKINS_MODULE_CASE_PATH` 和 `0 2 * * *` 定时触发。
3. 手工执行每日全量 Job，检查 console log、artifact 和 Allure。
4. 创建失败重试 Job，加载 `jenkins/Jenkinsfile.failed-rerun`。
5. 先空提交 `PYTEST_NODE_IDS`，确认构建明确失败。
6. 再传入一条或多条 node id，确认只运行目标用例并生成产物。
7. 创建模块重试 Job，加载 `jenkins/Jenkinsfile.module-rerun`。
8. 输入 `CASE_PATH` 手工执行，确认运行当前模块全部用例并生成产物。

## 6. 覆盖校准

| 检查项 | 结论 |
| --- | --- |
| 正常场景 | 已覆盖每日全量、失败重试、模块重试三类 Job 的参数输入和构建反馈 |
| 异常场景 | 已覆盖失败重试空 node id、Allure 生成失败和插件缺失降级 |
| 边界值 | 已覆盖单条/多条 node id、换行/逗号分隔、Windows/Linux agent、本地挂载仓库 |
| 权限态 | 当前阶段由 Jenkins 自身账号和 Job 权限控制；平台权限后置 |
| 非当前页面区域 | 已明确 Jenkins 页面不进入 Vue DOM，后续平台页面不得在本阶段提前实现 |
