# jenkins/AGENTS.md

本目录是 Jenkins Pipeline、Groovy 脚本和 Job 模板目录。进入 `jenkins/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 架构定位

- Jenkins 是平台严格执行主干，所有测试执行、模块重试、失败重试和报告生成都必须通过 Jenkins。
- Jenkins 负责参数接收、环境准备、stage 编排、调用 `api-test/tools/ci_runner.py`、归档产物和暴露执行状态。
- Jenkins 不负责 DRF 数据入库逻辑、Vue 页面逻辑或 pytest 重试规则实现。

## 固定 loop 中的位置

- `jenkins/` 属于非循环基础设施阶段，不要求每个需求重复产出。
- 当需求影响执行链路、Job 参数、归档策略、并发策略或报告发布方式时，必须先有需求说明、测试用例和架构影响说明，再修改 Jenkins 脚本。
- 修改 Pipeline 前应补充或更新脚本测试、样例参数和回归说明。

## 模块职责

- Jenkins 参数定义和 Job 模板维护。
- Windows/Linux agent 兼容。
- 调用 `api-test/tools/ci_runner.py` 执行 daily full suite、module rerun、failed rerun 等模式。
- 归档 `runtime/ci-runs/<run_id>/` 产物。
- 发布或归档 Allure 报告。
- 保留 Jenkins job/build 链接、任务状态和 console log，供 DRF 同步。

## 技术约定

- Groovy 只负责 Jenkins 参数、环境变量和 stage 编排。
- pytest 执行、失败 node id 收集、重试和 summary 输出必须由 `api-test/tools/ci_runner.py` 完成。
- Pipeline 必须使用 `isUnix()` 分支兼容 Linux `sh` 和 Windows `bat`。
- 脚本使用 Jenkins workspace 相对路径，不写死本机绝对路径。
- Jenkins 脚本源文件必须放在 `jenkins/` 并纳入 git 管理。
- 凭据必须通过 Jenkins Credentials 或环境变量注入，不写入 Groovy、README 或示例参数。

## 测试和验证

- Jenkins 脚本变更应至少覆盖参数校验、执行模式选择、Windows/Linux 命令分支和归档路径。
- 能用本地脚本测试的逻辑应放到可测试文件中，避免把复杂逻辑全部塞进 Jenkinsfile。
- 修改归档契约时，必须同步更新 `api-test/` 执行器契约和 `back-end/` 同步逻辑说明。

## 禁止事项

- 不在 Jenkinsfile 或 Groovy 脚本中提交真实账号、密码、token、cookie、Jenkins API Token、生产 URL 或敏感地址。
- 不在 Jenkins 中复制 pytest node id 收集、失败重试或 Allure summary 解析核心逻辑。
- 不把运行产物、console log、Allure HTML 或临时 workspace 文件提交到 git。
