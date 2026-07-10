# 环境与模块通过率页面-Jenkins依赖复用与趋势图修复-需求说明

## 0. 需求分级与澄清冻结

- 档位：M。
- 原因：同时影响 Jenkins 工具镜像与 Pipeline、DRF 趋势接口、Vue 趋势弹窗和 Playwright 真实验收。
- 流程：完整需求、功能测试、UI 映射、Jenkins/后端/前端 TDD、容器化检查、独立审查、Playwright、单独提交推送。
- [已澄清] 近 7/30 天按日期去重，不补造没有运行记录的日期，每天最多返回一条真实记录。
- [已澄清] 同日只要存在模块重试，就忽略当天定时执行，仅选择 `completed_at` 最晚的模块重试；完成时间相同或为空时以较大 `id` 为最后记录。
- [已澄清] 当天没有模块重试时，选择当天最后完成的其它模块历史记录。
- [已澄清] Jenkins 继续保留 executor 级 venv 隔离，不回退共享可写 venv；仅带预装标志的 Linux 工具镜像把镜像依赖作为只读基础，其它 Linux/Windows agent 保持隔离 venv，执行时检测并只补缺失项。
- 冻结依据：主人 2026-07-10 本轮问题描述。

## 1. 背景与目标

模块重跑首次落到新的 Jenkins executor 时会创建空 venv 并完整安装依赖，延长排队后的实际执行时间。趋势接口会返回同一天多条模块重试记录，前端基础 SVG 又缺少实际坐标和数值标识，无法清晰表达每日最终趋势。

目标：

1. Jenkins 工具镜像预装 api-test 依赖，executor venv 继承系统包；依赖已满足时跳过 pip install。
2. 近 7/30 天趋势按日期去重，遵守模块重试优先和同类型最后完成规则。
3. 趋势弹窗以接口真实数据绘制可读折线图，展示 0%-100% 纵轴、日期横轴和点位通过率。

## 2. 范围与不做事项

- 修改 `docker/jenkins/Dockerfile`、`jenkins/scripts/api-test-pipeline.groovy` 及静态测试和部署说明。
- 修改 `ModuleSnapshotTrendView` 和趋势 API 测试。
- 修改 `ModuleTrendDialog.vue`、前端单元测试和真实 Playwright。
- 不新增或迁移数据库表，不删除 `ModuleRunHistory` 原始记录。
- 不改变模块重试、失败重试的 pytest 选择协议、并发锁和 Allure 协议。
- 不引入大型图表依赖，沿用现有轻量 SVG 组件。

## 3. 功能要求

### AC-01 Jenkins 依赖复用

- Jenkins 工具镜像构建时安装 `api-test/requirements.txt` 中 Linux 适用依赖。
- Pipeline 仅在 Linux agent 暴露 `AIAPITEST_PREINSTALLED_REQUIREMENTS=1` 时启用 `--system-site-packages`；其它 agent 创建隔离 venv。
- 每次构建仍执行 `tools.install_missing_requirements` 检测；全部满足时输出跳过信息且不调用 pip install。
- requirements 变化或版本不一致时，只在当前 executor venv 安装缺失/不一致项。

### AC-02 每日趋势去重

- `GET /api/v1/module-snapshots/{snapshot_id}/trend?days=7|30` 每个 `run_date` 最多返回一条。
- 同日存在 `module_rerun` 时，只返回最后完成的 `module_rerun`。
- 同日不存在 `module_rerun` 时，返回当天最后完成的其它记录。
- `series` 按 `run_date` 升序，长度不超过请求天数；窗口内没有记录时返回空数组。
- 窗口结束日期按项目 `TIME_ZONE` 把快照完成时间转换为本地日期，避免 UTC/本地跨日漏数。

### AC-03 真实折线图

- 图表使用 API `series` 的 `run_date` 和 `pass_rate` 计算所有点位。
- Y 轴固定 0%、50%、100%，避免相对缩放夸大微小波动。
- X 轴展示首尾和按空间抽样的日期标签；7 天可完整展示，30 天不得文字重叠。
- 每个数据点提供日期、运行类型和通过率的可访问标签及 hover title。
- 图表和数据点分别进入浏览器无障碍角色树；单点、全等值、多点、空数据、错误态和移动端均保持稳定布局。

## 4. 数据与 API 契约

- 不修改 `ModuleRunHistory` 表和 serializer 字段。
- 请求路径、认证、`days` 校验和响应外层结构不变。
- `series` 选择规则由“窗口内全部记录”变更为“窗口内每日优选记录”。
- 每项字段继续包含 `run_date`、`run_type`、`total_count`、`failed_count`、`skipped_count`、`pass_rate`、`duration_seconds`。
- 同日优选排序键：`module_rerun` 优先；同优先级按非空 `completed_at`、再按 `id` 选择最后一条。

## 5. 架构影响评估

| 模块 | 影响 |
| --- | --- |
| Jenkins | 仅带预装标志的 Linux 工具镜像 venv 继承镜像依赖，其他 agent 保持隔离，检测脚本保持兜底 |
| Docker | 工具镜像构建上下文增加 api-test requirements 安装层 |
| DRF | 趋势查询增加每日优选，不改响应字段 |
| Vue | 趋势 SVG 计算和可访问展示增强 |
| 数据模型 | 无迁移，保留全部历史记录 |
| 权限 | 不变 |
| api-test | 安装检测工具行为不变，仅由镜像提供已安装基础 |

## 6. 容器化兼容检查

- Dockerfile 使用仓库相对路径复制 requirements，不绑定宿主机绝对路径。
- 镜像依赖更新由标准 image rebuild 完成，运行时仍可用 requirements 检测补差异。
- 非工具镜像 Linux agent 和 Windows agent 不继承未知全局包，继续按隔离 executor venv 检测安装。
- 不新增真实凭据、固定服务地址或本机专用路径。

## 7. 验收口径

- Jenkins/API/前端自动化测试全部通过。
- 重建 Jenkins 工具镜像后，真实模块重跑 console 出现 `All requirements already satisfied; skip pip install.`，不出现 `Successfully installed`。
- 真实 7 天和 30 天接口 `run_date` 均无重复；2026-07-10 仅保留最后一次模块重试。
- Playwright 验证折线图非空、点数等于接口 series 数、点位标签来自真实数据，并保留截图。
