# 环境与模块通过率页面-Jenkins执行闭环二次验收修复-功能测试用例

## 1. 报告入口

| 编号 | 优先级 | 场景 | 步骤 | 预期 |
| --- | --- | --- | --- | --- |
| TC-01 | P0 | 新完成任务查看报告 | 完成 Jenkins build，打开任务弹窗并点击查看报告 | 新页 URL 为具体 build 的 `/allure/` |
| TC-02 | P0 | 历史 artifact URL 兼容 | 任务库中保留旧 artifact URL，查询任务列表 | API 返回按 build URL 规范化后的 `/allure/` |
| TC-03 | P1 | 无 build number | 查询尚在队列且无报告的任务 | 查看报告不可用 |

## 2. 取消任务状态

| 编号 | 优先级 | 场景 | 步骤 | 预期 |
| --- | --- | --- | --- | --- |
| TC-04 | P0 | 已完成任务 | 打开任务弹窗定位 success/test_failed/failed/canceled 任务 | 取消按钮 disabled，背景和文字为灰色，光标 not-allowed |
| TC-05 | P0 | 运行中任务 | 打开 running 任务 | 有权限用户按钮可点击且保持正常视觉 |
| TC-06 | P1 | 移动视口 | 以 390px 宽度打开任务卡片 | 禁用态与桌面一致，无文字溢出 |

## 3. Jenkins 并发

| 编号 | 优先级 | 场景 | 步骤 | 预期 |
| --- | --- | --- | --- | --- |
| TC-07 | P0 | controller 容量 | 启动 Compose Jenkins 并查询 API | numExecutors=40 |
| TC-08 | P0 | 同一 Job 并发 | 连续触发同一 Job 两次不同 RUN_ID | 两个 build 同时 running，不因 Job 并发属性排队 |
| TC-09 | P0 | 不同模块并发 | 同时触发两个模块重试 | 两个任务可同时执行 |
| TC-10 | P1 | 运行隔离 | 比较并发 build 环境和产物路径 | venv 按 executor 隔离，cache/Allure 按 RUN_ID 隔离 |

## 4. pytest 控制台

| 编号 | 优先级 | 场景 | 步骤 | 预期 |
| --- | --- | --- | --- | --- |
| TC-11 | P0 | 实时输出 | 启动包含多个用例的 Job，在结束前轮询 progressive log | 可看到 pytest session、collected 和逐用例结果 |
| TC-12 | P0 | artifact 日志 | 构建完成后读取 `console.log` | 与实时输出包含相同 pytest 关键行 |
| TC-13 | P1 | pytest 超时 | 模拟子进程超时 | 已输出内容被保留，并追加 timeout 诊断 |

## 5. 模块用例同步

| 编号 | 优先级 | 场景 | 步骤 | 预期 |
| --- | --- | --- | --- | --- |
| TC-14 | P0 | 混合状态模块重试 | 运行含 passed/failed/skipped 的模块并同步 | 三个状态接口分别返回对应 node id，合计等于 total_count |
| TC-15 | P0 | 全通过模块重试 | 运行全通过模块并同步 | passed 有数据，failed/skipped 为空，不出现三者全空 |
| TC-16 | P0 | summary 缺少明细 | 模拟旧 summary 无 `case_results` | 旧当前用例明细保持不变，不被归档清空 |
| TC-17 | P1 | error 状态 | 运行 setup/call error 用例 | API failed 列表可见，execution_status=error |
| TC-18 | P1 | 重复同步 | 同一终态任务重复刷新 | 不重复归档或创建当前用例，结果稳定 |

## 6. 回归与安全

| 编号 | 优先级 | 场景 | 步骤 | 预期 |
| --- | --- | --- | --- | --- |
| TC-19 | P0 | 同模块执行锁 | 同环境同模块已有 active task 时再次触发 | 仍返回模块锁错误 |
| TC-20 | P0 | 不同模块 | 两个模块分别触发 | 不互相锁定 |
| TC-21 | P1 | 敏感信息 | 检查 summary、console、文档和提交 diff | 不含 token、Cookie、密码或 `.env` 值 |
