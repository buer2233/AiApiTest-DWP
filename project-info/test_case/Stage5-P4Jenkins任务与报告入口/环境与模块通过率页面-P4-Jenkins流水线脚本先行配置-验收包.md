# 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 验收包

## 1. 需求概览

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 |
| 需求分级 | M |
| 关联模块 | `jenkins` / `api-test` / `docker`；`back-end`、`front-end` 本阶段不开发执行对接 |
| 需求冻结日期 | 2026-07-05 |
| 本包生成日期 | 2026-07-05 |
| 需求说明 | `project-info/demand/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-需求说明.md` |
| 功能测试用例 | `project-info/test_case/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-功能测试用例.md` |
| Jenkins Job 交互说明 | `project-info/UI/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-JenkinsJob参数交互说明.md` |
| RTM | `project-info/test_case/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-可追溯矩阵.md` |

## 2. 逐条验收结论（对照需求 §12 验收口径）

| AC 编号 | 验收点 | 自测结论 | 证据 | 备注 |
| --- | --- | --- | --- | --- |
| `AC-JENKINS-1.1` | 每个模块每日全量 Job 支持凌晨 2 点自动执行 | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `python -m pytest jenkins/tests/test_pipeline_static.py -q`：`15 passed`；`jenkins/scripts/daily-full-module-pipeline.groovy` | 静态测试确认 `cron('0 2 * * *')` 和 `JENKINS_MODULE_CASE_PATH`；真实定时需在 Jenkins 上验证 |
| `AC-JENKINS-1.2` | 每日全量手工触发后产物完整 | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `python -m pytest jenkins/tests -q`：`23 passed` | 共享脚本负责 `ci_runner`、venv、归档和 Allure 校验 |
| `AC-JENKINS-1.3` | 每日全量归档 runtime 并可查看 Allure | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `python -m pytest jenkins/tests -q`：`23 passed` | Allure 插件发布为 Jenkins 实例能力 |
| `AC-JENKINS-1.4` | 每日全量后续同步会更新日期和执行时间 | ✅文档通过 | 需求 §5/§8、`jenkins/README.md`、RTM | 下一阶段平台同步时验证入库 |
| `AC-JENKINS-2.1` | 失败重试只执行传入 node id | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `python -m pytest jenkins/tests/test_pipeline_static.py -q`：`15 passed`；`python -m pytest api-test/tests/test_ci_runner.py -q`：`13 passed` | 固定 `RETRY_MODE=selected`，不使用 `all-failed` |
| `AC-JENKINS-2.2` | 失败重试未传 node id 明确失败 | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `jenkins/scripts/api-test-pipeline.groovy` 中 `error(emptyNodeIdsMessage)`；静态测试 `15 passed` | Jenkins 上空参数构建需主人验收 |
| `AC-JENKINS-2.3` | 失败重试产物完整 | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `python -m pytest jenkins/tests -q`：`23 passed` | 与每日全量复用同一归档契约 |
| `AC-JENKINS-2.4` | 失败重试后续同步不更新日期和执行时间 | ✅文档通过 | 需求 §5/§8、`jenkins/README.md`、RTM | 下一阶段平台同步时验证入库 |
| `AC-JENKINS-3.1` | 模块重试执行当前模块全部用例 | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `python -m pytest jenkins/tests/test_pipeline_static.py -q`：`15 passed`；`python -m pytest api-test/tests/test_ci_runner.py -q`：`13 passed` | 固定 `RETRY_MODE=module` |
| `AC-JENKINS-3.2` | 模块重试产物完整 | ⚠️自动化契约通过，Jenkins 实例待主人验收 | `python -m pytest jenkins/tests -q`：`23 passed` | 与每日全量复用同一归档契约 |
| `AC-JENKINS-3.3` | 模块重试后续同步会更新日期和执行时间 | ✅文档通过 | 需求 §5/§8、`jenkins/README.md`、RTM | 下一阶段平台同步时验证入库 |

## 3. 测试证据

### RED 证据

- 命令：`python -m pytest jenkins/tests/test_pipeline_static.py -q`
- 结果：`6 failed, 8 passed`
- 失败原因：新增契约测试找不到 `jenkins/Jenkinsfile.daily-full-module`、`jenkins/Jenkinsfile.failed-rerun`、`jenkins/Jenkinsfile.module-rerun` 及三条业务 Groovy 脚本，符合 TDD RED 预期。

### GREEN / 回归证据

| 命令 | 结果 | 说明 |
| --- | --- | --- |
| `python -m pytest jenkins/tests/test_pipeline_static.py -q` | `15 passed in 0.15s` | Jenkins Pipeline 静态契约测试 |
| `python -m pytest jenkins/tests -q` | `23 passed in 0.15s` | Jenkins 目录静态回归 |
| `python -m pytest api-test/tests/test_ci_runner.py -q` | `13 passed in 0.21s` | `ci_runner` 执行器契约回归 |

### 覆盖率说明

本阶段不修改 DRF 后端或 Vue 前端，不适用后端 pytest-django 覆盖率与前端 Playwright 截图门禁。Jenkins 交付以静态契约测试、`api-test` runner 单测和主人 Jenkins 实例人工验收为证据。

## 4. 一致性报告（RTM 摘要）

- RTM 漂移检查清单结论：自动化与文档项无漂移；真实 Jenkins 构建验收待主人执行。
- 可追溯矩阵：`环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-可追溯矩阵.md`

## 5. 实现摘要

- **Jenkins**：
  - 新增 `jenkins/Jenkinsfile.daily-full-module`
  - 新增 `jenkins/Jenkinsfile.failed-rerun`
  - 新增 `jenkins/Jenkinsfile.module-rerun`
  - 新增 `jenkins/scripts/daily-full-module-pipeline.groovy`
  - 新增 `jenkins/scripts/failed-rerun-pipeline.groovy`
  - 新增 `jenkins/scripts/module-rerun-pipeline.groovy`
  - 扩展 `jenkins/scripts/api-test-pipeline.groovy`，支持固定业务模式、可选 `MODULE_NAME`、可选 `PYTEST_NODE_IDS`、失败重试空 node id 校验、Job cron 触发配置。
- **测试**：
  - 扩展 `jenkins/tests/test_pipeline_static.py`，覆盖三条业务脚本、固定模式、cron、失败重试 node id 校验、共享执行器、跨平台、归档和 Allure 契约。
- **文档**：
  - 更新 `jenkins/README.md`，补充三类 Jenkins Job 创建方式、参数、触发方式、日期/执行时间语义和人工验收步骤。
- **前后端**：
  - 本阶段未修改 `back-end/` 和 `front-end/`，执行对接留到下一阶段。

## 6. 独立对抗审查

| 审查项 | 结论 | 证据 |
| --- | --- | --- |
| Jenkins 脚本独立审查 | 发现 2 个 P1 阻塞、1 个 P2 测试过拟合、1 个 P3 文档状态问题；均已处理或降为人工验收待执行 | P1-1：每日全量 `CASE_PATH` 改为 per-job `JENKINS_MODULE_CASE_PATH` 默认并缺失失败；P1-2：三个业务 Jenkinsfile 支持 `LOCAL_WORKSPACE_REPO=true` 时跳过初始 checkout；P2：补充静态测试覆盖；P3：验收包已生成并回填证据 |

## 7. 待主人确认项（熔断遗留）

| 编号 | 事项 | agent 的处理 | 需主人确认 |
| --- | --- | --- | --- |
| UAT-1 | Jenkins 实例上创建三类 Job 并执行真实构建 | 已交付脚本、README 和人工验收步骤 | 主人在 Jenkins 上按 README 执行验收 |
| UAT-2 | 每日全量真实 `0 2 * * *` 定时触发 | 静态测试已验证 cron 契约和 `JENKINS_MODULE_CASE_PATH` 默认值契约 | 主人在 Jenkins 上确认 Job 环境变量、定时配置与触发记录 |

## 8. 已知限制 / 后续项

- 本阶段不做 DRF 触发 Jenkins、Jenkins 任务记录表、执行锁、取消任务接口或结果同步接口。
- 本阶段不做 Vue Jenkins 任务弹窗、失败重试按钮启用、模块重试按钮启用或报告入口展示。
- Jenkins/Allure 外链不叠加平台 Cookie 验证；只有平台 DRF API 需要 Cookie 验证。
- `.env.example` 和 Docker 文档未改动，因为本阶段未新增环境变量、端口、挂载路径或工具链要求。

---

## 验收结论（主人签字）

- [ ] 全部 AC 达成（Jenkins 实例人工验收后勾选）
- [x] 自动化测试证据充分可信
- [x] RTM 无自动化/文档漂移
- [ ] 待确认项已逐条裁决

**验收人（主人）**：`__________`　**日期**：`__________`　**结论**：`通过 / 打回（附原因）`
