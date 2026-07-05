# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-功能测试用例

## 概览

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入 |
| 需求来源 | `project-info/demand/Stage6-P5Jenkins执行闭环与平台接入/环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-需求说明.md` |
| 需求分级 | M |
| 测试范围 | Jenkins Job 映射、任务记录、执行锁、失败重试、模块重试、Daily 同步、任务弹窗、取消、报告外链、按钮状态、P1-P4 回归 |
| 层次标注 | `[接口]`=后端 pytest；`[UI]`=Playwright；`[单元]`=Vitest；`[静态]`=静态配置测试；`[回归]`=前序阶段回归 |
| 更新时间 | 2026-07-05 |

> 本阶段所有 Jenkins 外部调用必须 mock 或使用本地 Jenkins 验收配置，不能在测试中提交真实账号、API Token、Cookie 或不可迁移 URL。

## 1. Jenkins Job 映射与配置

### TC-P5-F1-001 Job 绑定存在时按绑定触发 Jenkins `[接口]`
- **关联 AC**：AC-P5-1.1
- **优先级**：P0
- **前置条件**：环境、模块、`failed_rerun` Job binding 已启用；模块存在失败用例。
- **步骤**：管理人员调用 `POST /api/v1/module-snapshots/{id}/failed-case-retries`，`retry_scope=all_failed`。
- **预期结果**：返回 202；Jenkins client 收到绑定的 `job_full_name`；创建 `jenkins_task` 和 active lock。

### TC-P5-F1-002 Job 绑定缺失返回配置错误 `[接口]`
- **关联 AC**：AC-P5-1.2
- **优先级**：P0
- **步骤**：删除或禁用当前模块的 `module_rerun` binding 后触发模块重试。
- **预期结果**：返回 422 `jenkins_job_not_configured`；不调用 Jenkins；不创建任务和锁。

### TC-P5-F1-003 `.env.example` 只包含非敏感 Jenkins 接入变量 `[静态]`
- **关联 AC**：AC-P5-1.3
- **优先级**：P0
- **步骤**：扫描 `.env.example`。
- **预期结果**：包含 `JENKINS_API_BASE_URL`、Job 名、轮询和超时配置；不包含 `JENKINS_USERNAME`、`JENKINS_API_TOKEN`、Cookie、真实生产地址。

## 2. 任务记录、状态同步与锁

### TC-P5-F2-001 触发后创建 queued 任务 `[接口]`
- **关联 AC**：AC-P5-2.1
- **优先级**：P0
- **步骤**：mock Jenkins 触发返回 queue id；调用失败重试。
- **预期结果**：`jenkins_task.status=queued`，记录 queue URL、任务类型、触发人、Job 名和关联 run。

### TC-P5-F2-002 queue 分配 build 后进入 running `[接口]`
- **关联 AC**：AC-P5-2.2
- **优先级**：P0
- **步骤**：对 queued 任务执行同步，mock Jenkins queue 返回 build number。
- **预期结果**：任务进入 `running`，写入 build number 和 Jenkins build URL。

### TC-P5-F2-003 summary passed 同步为 success `[接口]`
- **关联 AC**：AC-P5-2.3
- **优先级**：P0
- **步骤**：mock build 完成、`summary.json.status=passed`。
- **预期结果**：任务进入 `success`；保存 summary；释放执行锁。

### TC-P5-F2-004 summary failed 同步为 test_failed `[接口]`
- **关联 AC**：AC-P5-2.4
- **优先级**：P0
- **步骤**：mock Jenkins build result 为 SUCCESS，但 `summary.json.status=failed` 且有 failed node id。
- **预期结果**：平台任务为 `test_failed`，保存 `failed_nodeids_json`，不误判为基础设施失败。

### TC-P5-F2-005 artifact 缺失同步为 failed `[接口]`
- **关联 AC**：AC-P5-2.5
- **优先级**：P1
- **步骤**：mock build 完成但 artifact 缺少 `summary.json`。
- **预期结果**：任务进入 `failed`，`error_summary` 说明缺失 summary；释放锁。

### TC-P5-F2-006 取消确认后进入 canceled 并释放锁 `[接口]`
- **关联 AC**：AC-P5-2.6
- **优先级**：P0
- **步骤**：任务处于 `canceling` 且 active lock 存在；同步到 Jenkins 已取消。
- **预期结果**：任务变为 `canceled`；lock 变为 `released`，`active_lock_key=null`。

### TC-P5-F2-007 canceling 状态不提前释放锁 `[接口]`
- **关联 AC**：AC-P5-2.6、AC-P5-5.4
- **优先级**：P0
- **步骤**：取消接口返回 `canceling` 后立即触发模块重试。
- **预期结果**：触发被 `409 module_execution_locked` 拒绝。

## 3. Daily 全量同步

### TC-P5-F3-001 发现 Daily cron build 创建 daily_full 任务 `[接口]`
- **关联 AC**：AC-P5-3.1
- **优先级**：P0
- **步骤**：调用批量同步，mock Daily Job 当天有新 build。
- **预期结果**：创建或更新 `daily_full` 任务，`trigger_source=jenkins_cron`。

### TC-P5-F3-002 Daily 同步刷新环境和模块统计 `[接口] [UI]`
- **关联 AC**：AC-P5-3.2
- **优先级**：P0
- **步骤**：同步 Daily summary 后打开环境页和模块页。
- **预期结果**：页面展示最新总数、失败数、通过率和状态。

### TC-P5-F3-003 Daily 更新日期和执行时间 `[接口] [UI]`
- **关联 AC**：AC-P5-3.3
- **优先级**：P0
- **步骤**：Daily 同步完成后查看模块行。
- **预期结果**：`completed_at`、`duration_seconds` 更新为本次完整执行值。

### TC-P5-F3-004 Daily 新结果归档旧当前用例 `[接口]`
- **关联 AC**：AC-P5-3.4
- **优先级**：P1
- **步骤**：已有当前用例结果，再同步 Daily 完整结果。
- **预期结果**：旧结果 `is_current=false`，新结果成为当前展示数据。

## 4. 失败重试

### TC-P5-F4-001 模块行一键失败重试传入全部失败 node id `[接口] [UI]`
- **关联 AC**：AC-P5-4.1
- **优先级**：P0
- **步骤**：点击模块行“一键失败重试”并确认。
- **预期结果**：请求 `retry_scope=all_failed`；后端传给 Jenkins 的 `PYTEST_NODE_IDS` 为当前模块全部当前失败 node id。

### TC-P5-F4-002 详情勾选失败重试只传入勾选 node id `[接口] [UI]`
- **关联 AC**：AC-P5-4.2
- **优先级**：P0
- **步骤**：在详情弹窗勾选 2 条失败用例后点击失败重试。
- **预期结果**：请求 `retry_scope=selected_failed`，只传勾选 ID；Jenkins 只收到对应 node id。

### TC-P5-F4-003 详情一键失败重试不受当前筛选影响 `[UI]`
- **关联 AC**：AC-P5-4.3
- **优先级**：P1
- **步骤**：详情弹窗切换筛选后点击“一键失败重试”。
- **预期结果**：仍重试当前模块全部当前失败用例。

### TC-P5-F4-004 无失败用例不触发 Jenkins `[接口] [UI]`
- **关联 AC**：AC-P5-4.4
- **优先级**：P0
- **步骤**：通过率 100% 模块点击失败重试。
- **预期结果**：后端返回 422 `no_failed_cases`；前端提示“通过率 100% 无需失败重试”。

### TC-P5-F4-005 失败重试同步后更新失败数和通过率 `[接口] [UI]`
- **关联 AC**：AC-P5-4.5
- **优先级**：P0
- **步骤**：失败重试 summary passed 后同步。
- **预期结果**：对应失败用例变为 passed；模块失败数下降，通过率上升。

### TC-P5-F4-006 失败重试不更新日期和执行时间 `[接口] [UI]`
- **关联 AC**：AC-P5-4.6
- **优先级**：P0
- **步骤**：记录重试前模块日期和执行时间，完成失败重试后再查看。
- **预期结果**：日期和执行时间保持不变。

### TC-P5-F4-007 非失败或跨模块勾选返回 422 `[接口]`
- **关联 AC**：AC-P5-4.2
- **优先级**：P0
- **步骤**：提交通过用例、归档用例或其它模块用例 ID。
- **预期结果**：返回 422 `invalid_case_selection`，不创建 Jenkins 任务。

## 5. 模块重试

### TC-P5-F5-001 模块重试触发 module_rerun `[接口] [UI]`
- **关联 AC**：AC-P5-5.1
- **优先级**：P0
- **步骤**：管理人员点击模块行“模块重试”并确认。
- **预期结果**：创建 `module_rerun` 任务；Jenkins 参数包含模块 `CASE_PATH`。

### TC-P5-F5-002 模块重试同步后更新日期和执行时间 `[接口] [UI]`
- **关联 AC**：AC-P5-5.2
- **优先级**：P0
- **步骤**：模块重试完成并同步。
- **预期结果**：模块统计、日期和执行时间更新。

### TC-P5-F5-003 模块重试新结果成为当前展示数据 `[接口]`
- **关联 AC**：AC-P5-5.3
- **优先级**：P1
- **步骤**：模块重试产生新的失败列表。
- **预期结果**：旧当前结果归档，新结果成为当前 cases 默认失败列表。

### TC-P5-F5-004 运行中失败重试阻止模块重试 `[接口] [UI]`
- **关联 AC**：AC-P5-5.4
- **优先级**：P0
- **步骤**：同模块已有 active lock 时点击模块重试。
- **预期结果**：返回并展示“已有用例重试，无法执行！”。

## 6. Jenkins 任务弹窗与取消

### TC-P5-F6-001 当前模块今日任务分页展示 `[接口] [UI]`
- **关联 AC**：AC-P5-6.1
- **优先级**：P0
- **步骤**：点击模块行“Jenkins任务”。
- **预期结果**：弹窗展示今日任务、状态、触发人、Jenkins 链接和报告链接；无任务展示空态。

### TC-P5-F6-002 queued/running 可取消并进入 canceling `[接口] [UI]`
- **关联 AC**：AC-P5-6.2
- **优先级**：P0
- **步骤**：点击 running 任务取消。
- **预期结果**：后端调用 Jenkins 取消接口；任务返回 `canceling`；弹窗刷新。

### TC-P5-F6-003 查看报告新页打开可信链接 `[UI]`
- **关联 AC**：AC-P5-6.3
- **优先级**：P1
- **步骤**：点击“查看报告”。
- **预期结果**：使用 `target=_blank` 打开后端返回的 Allure 链接；无链接时禁用。

### TC-P5-F6-004 查看 Jenkins 任务新页打开可信链接 `[UI]`
- **关联 AC**：AC-P5-6.4
- **优先级**：P1
- **步骤**：点击“查看 Jenkins 任务”。
- **预期结果**：新页打开 Jenkins build URL；不叠加平台 Cookie 校验页面。

### TC-P5-F6-005 弹窗打开时运行中任务轮询刷新 `[UI]`
- **关联 AC**：AC-P5-6.5
- **优先级**：P1
- **步骤**：打开任务弹窗，mock running 任务 5 秒后变为 success。
- **预期结果**：弹窗自动刷新；关闭弹窗后停止轮询。

### TC-P5-F6-006 普通成员不能取消他人任务 `[接口] [UI]`
- **关联 AC**：AC-P5-6.2
- **优先级**：P0
- **步骤**：member 尝试取消他人任务。
- **预期结果**：403 `forbidden`；前端不展示或禁用取消按钮。

## 7. 按钮状态与前端反馈

### TC-P5-F7-001 actions 控制按钮启用 `[接口] [UI]`
- **关联 AC**：AC-P5-7.1
- **优先级**：P0
- **步骤**：模块列表返回不同 actions。
- **预期结果**：按钮启用状态与后端一致。

### TC-P5-F7-002 disabled reason 可见 `[UI]`
- **关联 AC**：AC-P5-7.2
- **优先级**：P1
- **步骤**：后端返回无权限、锁定、无失败用例等 reason。
- **预期结果**：禁用按钮有 tooltip 或提示文本说明原因。

### TC-P5-F7-003 请求中禁止重复提交 `[UI]`
- **关联 AC**：AC-P5-7.3
- **优先级**：P0
- **步骤**：连续双击失败重试确认按钮。
- **预期结果**：只发送一次 POST；按钮 loading。

### TC-P5-F7-004 锁冲突固定文案 `[接口] [UI]`
- **关联 AC**：AC-P5-7.4
- **优先级**：P0
- **步骤**：触发锁冲突。
- **预期结果**：后端 message 和前端提示均为“已有用例重试，无法执行！”。

### TC-P5-F7-005 移动端操作区域不溢出 `[UI]`
- **关联 AC**：AC-P5-7.5
- **优先级**：P1
- **步骤**：390px 视口访问模块页、详情弹窗和任务弹窗。
- **预期结果**：按钮不重叠、不横向溢出，关键操作可触达。

## 8. 回归与门禁

### TC-P5-REG-001 P1 权限回归 `[回归]`
- **优先级**：P0
- **预期结果**：登录、邀请码、admin/member 路由权限不回退。

### TC-P5-REG-002 P2 模块页筛选分页回归 `[回归]`
- **优先级**：P0
- **预期结果**：环境、模块筛选、分页、URL query 同步保持不变。

### TC-P5-REG-003 P3 用例详情、状态审计、趋势回归 `[回归]`
- **优先级**：P0
- **预期结果**：状态修改、审计、趋势弹窗仍通过。

### TC-P5-REG-004 P4 Jenkins 静态契约回归 `[回归]`
- **优先级**：P0
- **预期结果**：三条 Jenkins Pipeline 静态测试和 `api-test` runner 测试通过。

## 9. 覆盖矩阵

| AC 编号 | 测试用例 |
| --- | --- |
| AC-P5-1.1 | TC-P5-F1-001 |
| AC-P5-1.2 | TC-P5-F1-002 |
| AC-P5-1.3 | TC-P5-F1-003 |
| AC-P5-2.1 | TC-P5-F2-001 |
| AC-P5-2.2 | TC-P5-F2-002 |
| AC-P5-2.3 | TC-P5-F2-003 |
| AC-P5-2.4 | TC-P5-F2-004 |
| AC-P5-2.5 | TC-P5-F2-005 |
| AC-P5-2.6 | TC-P5-F2-006、TC-P5-F2-007 |
| AC-P5-3.1 | TC-P5-F3-001 |
| AC-P5-3.2 | TC-P5-F3-002 |
| AC-P5-3.3 | TC-P5-F3-003 |
| AC-P5-3.4 | TC-P5-F3-004 |
| AC-P5-4.1 | TC-P5-F4-001 |
| AC-P5-4.2 | TC-P5-F4-002、TC-P5-F4-007 |
| AC-P5-4.3 | TC-P5-F4-003 |
| AC-P5-4.4 | TC-P5-F4-004 |
| AC-P5-4.5 | TC-P5-F4-005 |
| AC-P5-4.6 | TC-P5-F4-006 |
| AC-P5-5.1 | TC-P5-F5-001 |
| AC-P5-5.2 | TC-P5-F5-002 |
| AC-P5-5.3 | TC-P5-F5-003 |
| AC-P5-5.4 | TC-P5-F5-004 |
| AC-P5-6.1 | TC-P5-F6-001 |
| AC-P5-6.2 | TC-P5-F6-002、TC-P5-F6-006 |
| AC-P5-6.3 | TC-P5-F6-003 |
| AC-P5-6.4 | TC-P5-F6-004 |
| AC-P5-6.5 | TC-P5-F6-005 |
| AC-P5-7.1 | TC-P5-F7-001 |
| AC-P5-7.2 | TC-P5-F7-002 |
| AC-P5-7.3 | TC-P5-F7-003 |
| AC-P5-7.4 | TC-P5-F7-004 |
| AC-P5-7.5 | TC-P5-F7-005 |
