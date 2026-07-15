# ISSUE-Stage13-Daily-Full-Module-单一流水线编排

## 状态

待处理。

## 现象

Jenkins 当前显示 `AiApiTest-DWP-Daily-Full-Module-test_gbif_case` 和 `AiApiTest-DWP-Daily-Full-Module-test_gbif_case_module2` 两个分模块 Daily Job。

## 期望

仅保留一个 `AiApiTest-DWP-Daily-Full-Module` Pipeline。该 Pipeline 每天定时发起当前系统全部模块用例执行，并以最多 10 个 Job 并发执行；模块拆分、调度、聚合、失败与 Allure 归档必须保持在同一个 Daily Pipeline 契约内。

## 影响与处理边界

该事项会变更 Jenkins Job 创建策略、Daily 执行编排和并发协议，需单独进入完整需求 loop 后实施。本次仅登记，不删除现有 Jenkins Job、不修改 Daily Pipeline。
