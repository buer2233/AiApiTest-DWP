# 环境与模块通过率页面-Jenkins依赖复用与趋势图修复-可追溯矩阵

| AC | 测试 | 实现 | 验收证据 | 状态 |
| --- | --- | --- | --- | --- |
| AC-01 | TC-01~TC-04 | `docker/jenkins/Dockerfile`、`jenkins/scripts/api-test-pipeline.groovy`、Jenkins 静态测试 | Jenkins/Docker 50 passed；镜像 `sha256:e482cf...`；仅工具镜像标志启用继承；真实 Module-Rerun #27 console 跳过依赖且未执行 pip install | 通过 |
| AC-02 | TC-05~TC-11 | `back-end/metrics/views.py`、`back-end/tests/test_metrics_trend_api.py` | 后端 168 passed、覆盖率 90%；本地时区跨日测试通过；真实 7/30 天日期唯一且最后一天为 `module_rerun` | 通过 |
| AC-03 | TC-12~TC-17 | `ModuleTrendDialog.vue`、Stage11 Vitest、真实 Playwright | 前端 8 files / 18 tests passed；真实 E2E 1 passed；Chromium 可识别逐点角色；移动标签高度/不重叠和无水平溢出通过 | 通过 |
| 回归安全 | TC-18~TC-20 | Stage4 日期断言收紧为表格单元格；部署与说明文档同步 | 受影响 Playwright 23 passed；生产构建通过；Compose config 通过；api-test 执行器契约 62 passed | 通过 |
