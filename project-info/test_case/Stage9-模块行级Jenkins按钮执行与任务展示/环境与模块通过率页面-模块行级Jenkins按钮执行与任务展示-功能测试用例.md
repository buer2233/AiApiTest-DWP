# 环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示 功能测试用例

## 概览

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示 |
| 需求来源 | `project-info/demand/Stage9-模块行级Jenkins按钮执行与任务展示/环境与模块通过率页面-模块行级Jenkins按钮执行与任务展示-需求说明.md` |
| 测试范围 | 模块行一键失败重试、模块重试、Jenkins 任务弹窗、Jenkins 同步和页面刷新 |

## 1. 后端接口测试

### TC-S9-BE-001 Daily 批量同步向 Jenkins service 传入 active daily job names
- **关联 AC**：AC-S9-4.1
- **优先级**：P0
- **步骤**：创建 active daily job binding，mock `discover_jenkins_builds`，调用 `POST /api/v1/jenkins-tasks/sync`，请求体 `discover_daily=true`。
- **预期**：返回 200；mock 收到 `job_full_names=[binding.job_full_name]`；同步计数正确。

### TC-S9-BE-002 单任务同步终态后更新模块快照
- **关联 AC**：AC-S9-2.2、AC-S9-4.2
- **优先级**：P0
- **步骤**：创建 running module_rerun task，mock `fetch_jenkins_task_result` 返回 summary passed。
- **预期**：任务进入 success；模块统计、日期和执行时间更新；锁释放。

### TC-S9-BE-003 失败重试同步不更新日期和执行时间
- **关联 AC**：AC-S9-1.2
- **优先级**：P0
- **步骤**：记录模块日期和执行时间；创建 failed_rerun task；mock summary 后同步。
- **预期**：失败数和通过率刷新；日期和执行时间保持同步前值。

## 2. 前端单元测试

### TC-S9-FE-001 Jenkins API 封装包含单任务同步接口
- **关联 AC**：AC-S9-4.2
- **优先级**：P0
- **步骤**：调用前端 API `syncJenkinsTask(taskId)`。
- **预期**：只请求 `/jenkins-tasks/{taskId}/sync`，不拼接 Jenkins URL。

### TC-S9-FE-002 Jenkins 任务弹窗轮询会同步 active 任务并通知父组件刷新
- **关联 AC**：AC-S9-3.2
- **优先级**：P0
- **步骤**：弹窗加载到 running 任务；触发同步流程。
- **预期**：调用 DRF sync；任务状态变更后 emit `taskUpdated`；父级可刷新模块列表。

## 3. 前端 E2E 测试

### TC-S9-E2E-001 一键失败重试直接触发并提示
- **关联 AC**：AC-S9-1.1
- **优先级**：P0
- **步骤**：进入 `/modules`，点击“一键失败重试”。
- **预期**：前端调用 `POST /failed-case-retries`，提示“开始执行失败重试”。

### TC-S9-E2E-002 模块重试确认后触发
- **关联 AC**：AC-S9-2.1
- **优先级**：P0
- **步骤**：点击“模块重试”，确认弹窗。
- **预期**：确认文案正确；确认后调用 `POST /module-reruns`。

### TC-S9-E2E-003 Jenkins 任务弹窗展示并轮询刷新
- **关联 AC**：AC-S9-3.1、AC-S9-3.2、AC-S9-3.3
- **优先级**：P0
- **步骤**：点击“Jenkins 任务”，mock 初始 running、同步后 success。
- **预期**：弹窗展示任务类型/状态/外链；轮询后状态更新；父页面刷新模块列表。

## 4. 回归

- 运行 P5/Stage8 相关后端测试，保证历史 Jenkins 契约不回退。
- 运行 P5/Stage8 相关 Playwright 用例，保证按钮文案、确认文案、弹窗字段和外链不回退。
