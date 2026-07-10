# 环境与模块通过率页面-Jenkins执行闭环二次验收修复-需求说明

## 0. 需求分级与澄清冻结

- 档位：M。
- 原因：同时影响 Vue、DRF、Jenkins、api-test 执行协议、Docker Compose 和结果同步。
- 流程：不裁剪阶段，执行完整需求、测试、UI 映射、后端/执行器/前端 TDD、独立审查和 Playwright 验收。
- [已澄清] “4 个 Pipeline”指本地 Jenkins 的 `AiApiTest-DWP-Daily-Full-Module`、`AiApiTest-DWP-Failed-Rerun`、`AiApiTest-DWP-Module-Rerun`、`AiApiTest-DWP-Pipeline`。
- [已澄清] 采用方案 A：controller 配置 40 个 executors，四个 Job 均允许并发，保证任一 Job 具备同时运行 10 个任务的容量；不引入单 Job 10 个的插件硬上限。
- [已澄清] 并发执行必须隔离 executor 级虚拟环境和 run 级 pytest cache。
- 冻结时间：2026-07-10；冻结依据：主人明确回复“按照方案A执行”。

## 1. 背景

Stage9 验收后发现报告入口、禁用反馈、Jenkins 并发容量、pytest 控制台过程日志和模块重试结果同步仍未形成完整闭环，影响任务排查和用例详情可信度。

## 2. 目标

1. “查看报告”始终进入具体 Jenkins build 的 Allure 页面：`<build_url>/allure/`。
2. 已结束任务的“取消任务”按钮保持不可点击，并显示明确灰色禁用态。
3. 四个 Jenkins Job 均允许并发，Compose Jenkins 默认提供 40 个 executors。
4. Jenkins console 在 pytest 执行期间持续输出收集、用例结果和汇总日志，同时保留 artifact `console.log`。
5. module rerun 和 daily full 完成后，用完整 node id 级结果原子替换当前用例明细，failed/passed/skipped 查询与快照统计一致。

## 3. 范围

- `api-test/tools/ci_runner.py` 及 pytest 结果采集插件。
- `jenkins/scripts/`、`docker-compose.yml`、`.env.example` 与 Jenkins 部署文档。
- `back-end/metrics/jenkins_service.py`、同步逻辑、序列化器及测试。
- `front-end/src/components/metrics/JenkinsTasksDialog.vue` 及测试/E2E。

## 4. 不做事项

- 不引入 `throttle-concurrents` 插件和单 Job 并发硬上限。
- 不新增数据库表或修改现有 API 路径。
- 不让前端直接访问 Jenkins API。
- 不改变同一模块执行锁：同环境同模块仍只允许一个平台任务；不同模块允许并发。

## 5. 功能要求

### AC-01 构建级 Allure 入口

- Jenkins 构建完成后，后端保存并返回 `<jenkins_build_url>/allure/`。
- 对数据库中历史 artifact HTML URL，序列化时应优先按 build URL 规范化，避免旧数据继续跳错。

### AC-02 取消按钮禁用态

- `actions.cancel=false` 或正在取消时，按钮必须带原生 `disabled`。
- 禁用态使用灰色背景、灰色文字、弱化边框和 `not-allowed` 光标，且 hover 不恢复可点击视觉。

### AC-03 Jenkins 并发容量

- Compose Jenkins 通过 `JENKINS_EXECUTORS` 配置 executor 数，默认 40。
- 四个 Job 不得保留 `DisableConcurrentBuildsJobProperty`。
- 每个 executor 使用独立 Python venv；每个 `RUN_ID` 使用独立 pytest cache 与 Allure 目录。

### AC-04 pytest 实时日志

- pytest stdout/stderr 合并后按产生顺序实时写入 Jenkins console，并同步追加到 run 目录 `console.log`。
- 子进程结束后 summary 解析仍使用完整输出；超时仍生成诊断日志和失败 summary。

### AC-05 完整用例同步

- pytest 执行器输出每个最终 node id 的 `execution_status`、名称、耗时和脱敏错误摘要。
- 后端仅在 `case_results` 契约存在且有效时归档旧当前结果并创建新结果；契约缺失不得清空旧明细。
- `failed` 与 `error` 映射到前端 `failed` 展示状态；`passed`、`skipped` 分别映射同名展示状态。

## 6. 数据与更新规则

- 不变更表结构。
- `TestCaseResult` 保持追加写入；全量同步时旧记录改为 `archived/is_current=false`，新记录关联本次 `source_run`。
- 替换明细和更新模块快照必须位于同一数据库事务。
- `summary_json` 增加 `case_results` 数组，历史 summary 继续兼容。

## 7. API 与执行协议契约

### 7.1 Jenkins 任务列表

- 路径不变：`GET /api/v1/module-snapshots/{snapshot_id}/jenkins-tasks`。
- `allure_report_url`：具体 build 的绝对公开 URL，格式为 `<public_base>/<job_path>/<build_number>/allure/`。
- `actions.cancel`：仅 `queued/running` 且当前用户有权限时为 `true`。

### 7.2 summary.json

```json
{
  "status": "passed|failed",
  "total_count": 3,
  "passed_count": 1,
  "failed_count": 1,
  "skipped_count": 1,
  "failed_nodeids": ["test_case/pkg/test_a.py::test_failed"],
  "case_results": [
    {
      "node_id": "test_case/pkg/test_a.py::test_passed",
      "case_name": "test_passed",
      "execution_status": "passed",
      "duration_seconds": 0.12,
      "error_type": "",
      "error_message_summary": ""
    }
  ]
}
```

- `execution_status` 允许 `passed`、`failed`、`skipped`、`error`。
- 错误摘要不得包含凭据、Cookie 或完整敏感响应体。

## 8. 错误与降级

- Jenkins summary/artifact 缺失：任务按现有规则失败，不清空当前用例明细。
- `case_results` 缺失或类型非法：保留旧明细并记录同步错误摘要；不得部分替换。
- pytest 超时：实时输出已产生日志，进程终止后写入 timeout 诊断。

## 9. 架构影响评估

| 模块 | 影响 |
| --- | --- |
| DRF | 报告 URL 规范化、完整用例结果同步 |
| Vue | Jenkins 弹窗禁用视觉和 E2E |
| Jenkins | executor 数、Job 并发属性、并发工作目录隔离 |
| api-test | 实时输出和 node id 级 summary 协议 |
| Docker | Compose 注入 `JENKINS_EXECUTORS`，重启 Jenkins 生效 |
| 数据模型 | 不迁移表，仅更新追加写入规则 |
| 权限 | 不变 |
| 报告协议 | 从 artifact HTML 入口切换为 Jenkins build Allure 插件入口 |

## 10. 容器化兼容检查

- 新配置通过 `.env`/`.env.example` 注入，不写死宿主机端口或凭据。
- Jenkins init Groovy 只读取 `JENKINS_EXECUTORS`，默认值可迁移。
- executor venv、run cache 使用 Jenkins 环境变量和 workspace 相对路径。
- 不把 `.env`、Jenkins home、runtime 或报告产物写入镜像。

## 11. 验收口径

- 后端、api-test、Jenkins 静态测试和前端 Vitest 全部通过。
- 真实 Jenkins 同一 Job 至少两个构建可同时处于 running，controller executors=40。
- 真实 console 在 pytest 结束前可看到用例过程行。
- Playwright 验证报告链接、灰色取消按钮和模块重试后 failed/passed/skipped 明细。
