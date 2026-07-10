# 环境与模块通过率页面-Jenkins执行闭环二次验收修复-可追溯矩阵

| AC | 测试 | 实现 | 验收证据 | 状态 |
| --- | --- | --- | --- | --- |
| AC-01 | TC-01~TC-03 | `back-end/metrics/jenkins_service.py`、`back-end/metrics/serializers.py` | 后端回归通过；Playwright 验证任务报告链接为具体 build 的 `/allure/`，无 Jenkins 会话时登录跳转的 `from` 参数准确 | 已通过 |
| AC-02 | TC-04~TC-06 | `front-end/src/components/metrics/JenkinsTasksDialog.vue`、`front-end/src/assets/main.css` | 前端 Vitest 14 项通过；Playwright 验证终态任务取消按钮为原生 disabled，计算样式为灰色禁用态 | 已通过 |
| AC-03 | TC-07~TC-10 | `docker-compose.yml`、`jenkins/scripts/configure-executors.groovy`、`jenkins/scripts/configure-local-mounted-jobs.groovy`、`jenkins/scripts/api-test-pipeline.groovy` | Jenkins 静态测试 49 项通过；真实 Jenkins 为 40 executors，同一 Module-Rerun Job 的两个不同模块构建同时处于 running | 已通过 |
| AC-04 | TC-11~TC-13 | `api-test/tools/ci_runner.py`、`api-test/tools/sensitive_data.py` | api-test 业务测试 62 项通过；Playwright 在构建仍为 `building=true` 时从 progressive log 读取到 pytest 用例过程行 | 已通过 |
| AC-05 | TC-14~TC-18 | `api-test/tools/pytest_case_reporter.py`、`back-end/metrics/views.py` | 后端回归 164 项通过；真实快照 2 查询确认 failed=1、passed=8、skipped=1、total=10 | 已通过 |
| 安全回归 | TC-19~TC-21 | RUN_ID 校验、日志与错误摘要脱敏、事务内完整明细校验与保留旧数据降级 | api-test、后端、Jenkins、前端回归通过；`git diff --check` 与敏感信息检查通过 | 已通过 |
