# 环境与模块通过率页面-P4-Jenkins流水线脚本先行配置 功能测试用例

## 1. 概览

| 项 | 内容 |
| --- | --- |
| 需求来源 | `project-info/demand/Stage5-P4Jenkins任务与报告入口/环境与模块通过率页面-P4-Jenkins流水线脚本先行配置-需求说明.md` v1.0 |
| 需求分级 | M |
| 覆盖范围 | Jenkins 每日全量模块执行、失败重试、模块重试、共享执行链路、Allure/产物归档、容器化兼容和后续同步语义 |
| 不覆盖范围 | DRF 触发 Jenkins、Vue 按钮启用、任务记录表、执行锁、取消任务、结果同步入库 |
| 更新时间 | 2026-07-05 |

## 2. 测试数据与公共前置

| 数据项 | 示例值 | 说明 |
| --- | --- | --- |
| 默认模块路径 | `test_case/test_gbif_case` | 示例模块路径，不绑定真实业务常量 |
| 每日全量模块路径环境变量 | `JENKINS_MODULE_CASE_PATH=test_case/test_gbif_case` | 每个每日全量 Job 必须配置自己的模块路径默认值 |
| 模块名 | `GBIF 示例模块` | Jenkins 展示用文本 |
| 单条失败 node id | `test_case/test_gbif_case/test_demo.py::test_should_retry` | 失败重试示例值 |
| 多条失败 node id | 使用换行或英文逗号分隔 | 失败重试脚本必须支持两种输入格式 |
| 运行目录 | `api-test/runtime/ci-runs/<RUN_ID>/` | Jenkins 归档根目录 |

公共前置：

1. Jenkins Job 使用仓库中的 Jenkinsfile 入口加载对应 Pipeline 脚本。
2. Jenkins agent 可访问仓库 workspace，且 `api-test` 依赖可安装。
3. Allure CLI 或 `api-test` 现有报告生成能力可用。
4. 不在测试数据中写入真实 Jenkins URL、账号、Token、Cookie 或生产地址。

## 3. 功能测试用例

### TC-JENKINS-F-001 每日全量 Job 支持凌晨 2 点定时触发

- **关联 AC**：`AC-JENKINS-1.1`
- **优先级**：P0
- **测试目标**：验证每日全量脚本自带或指导 Jenkins Job 配置 `0 2 * * *` cron。
- **前置条件**：已创建某模块每日全量 Pipeline Job。
- **测试步骤**：
  1. 打开每日全量 Job 配置。
  2. 检查 Job 加载 `jenkins/Jenkinsfile.daily-full-module`。
  3. 检查 Job 环境变量 `JENKINS_MODULE_CASE_PATH` 指向当前模块路径。
  4. 检查 Job 定时触发配置为 `0 2 * * *`。
  5. 确认 `CASE_PATH` 默认值来自当前 Job 的 `JENKINS_MODULE_CASE_PATH`。
- **预期结果**：
  - Job 具备每天 02:00 自动触发能力。
  - 每个模块通过独立 Job 与独立 `CASE_PATH` 区分。
  - 未配置 `JENKINS_MODULE_CASE_PATH` 且未手工填写 `CASE_PATH` 时构建明确失败。
  - Job 配置不依赖本机绝对路径或真实凭据。
- **备注**：本地静态测试验证 Jenkinsfile/Pipeline 中存在 cron 契约；真实定时由主人在 Jenkins 上验收。

### TC-JENKINS-F-002 每日全量手工触发执行当前模块全部用例

- **关联 AC**：`AC-JENKINS-1.2`
- **优先级**：P0
- **测试目标**：验证每日全量脚本向 `ci_runner` 传递 `RETRY_MODE=none` 和 `CASE_PATH`。
- **前置条件**：每日全量 Job 已配置 `JENKINS_MODULE_CASE_PATH` 或手工填写 `CASE_PATH`。
- **测试步骤**：
  1. 在 Jenkins 中手工触发每日全量 Job。
  2. 查看 console log 中传入的环境变量与执行命令。
  3. 等待构建完成。
  4. 检查运行目录内容。
- **预期结果**：
  - Pipeline 使用 `tools.ci_runner --from-jenkins-env`。
  - `RETRY_MODE` 固定为 `none`。
  - 运行目录包含 `summary.json`、`failed_nodeids.json`、`console.log`、`allure-results`、`allure-report`。
  - Jenkins 不在 Groovy 中复制 pytest 用例选择逻辑。

### TC-JENKINS-F-003 每日全量产物归档与 Allure 发布

- **关联 AC**：`AC-JENKINS-1.3`
- **优先级**：P0
- **测试目标**：验证每日全量运行目录被 Jenkins 归档，并尝试发布 Allure。
- **前置条件**：每日全量 Job 已完成一次构建。
- **测试步骤**：
  1. 打开 Jenkins 构建详情。
  2. 查看 archived artifacts。
  3. 检查 `api-test/runtime/ci-runs/<RUN_ID>/` 下所有产物是否可下载。
  4. 如果 Jenkins 安装 Allure 插件，检查 Allure 报告入口。
- **预期结果**：
  - Jenkins 归档完整运行目录。
  - Allure 插件存在时发布 `allure-results`。
  - Allure 插件不存在时构建不中断，console log 提示使用 runtime artifact 查看报告。

### TC-JENKINS-ST-001 每日全量后续同步语义为更新日期和执行时间

- **关联 AC**：`AC-JENKINS-1.4`
- **优先级**：P1
- **测试目标**：验证需求、测试与 README 明确每日全量后续同步会更新模块“日期”和“执行时间”。
- **前置条件**：无需真实后端同步。
- **测试步骤**：
  1. 检查需求说明、测试用例、RTM 和 README 的每日全量同步语义。
  2. 检查脚本命名和说明是否标记为 daily full。
- **预期结果**：
  - 每日全量被归类为会更新模块“日期”和“执行时间”的执行类型。
  - 本阶段不出现实际入库逻辑，避免越界实现。

### TC-JENKINS-F-004 失败重试执行传入的单条 node id

- **关联 AC**：`AC-JENKINS-2.1`
- **优先级**：P0
- **测试目标**：验证失败重试脚本使用 `RETRY_MODE=selected`，只执行传入 node id。
- **前置条件**：失败重试 Job 已创建。
- **测试步骤**：
  1. 打开失败重试 Job 的 Build with Parameters。
  2. 输入 `CASE_PATH` 和单条 `PYTEST_NODE_IDS`。
  3. 手工触发构建。
  4. 查看 console log、summary 和 pytest 输出。
- **预期结果**：
  - Pipeline 固定传入 `RETRY_MODE=selected`。
  - pytest 只收到目标 node id。
  - 运行产物按本次 `RUN_ID` 写入。

### TC-JENKINS-F-005 失败重试支持多条 node id 输入

- **关联 AC**：`AC-JENKINS-2.1`
- **优先级**：P0
- **测试目标**：验证勾选多个失败用例和“一键失败重试”都可传入同一 `PYTEST_NODE_IDS` 字段。
- **前置条件**：失败重试 Job 已创建。
- **测试步骤**：
  1. 使用换行分隔输入两条 node id 并触发构建。
  2. 使用英文逗号分隔输入两条 node id 并触发构建。
  3. 分别检查 pytest 执行范围。
- **预期结果**：
  - 两种输入形式都由 `ci_runner` 解析。
  - Groovy 不区分“勾选失败重试”和“一键失败重试”。
  - 一键失败重试仅体现为传入当前模块全部失败 node id 列表。

### TC-JENKINS-ERR-001 失败重试缺少 node id 时明确失败

- **关联 AC**：`AC-JENKINS-2.2`
- **优先级**：P0
- **测试目标**：验证失败重试脚本不会在未传 node id 时误跑整个模块。
- **前置条件**：失败重试 Job 已创建。
- **测试步骤**：
  1. 保持 `PYTEST_NODE_IDS` 为空。
  2. 手工触发失败重试 Job。
  3. 查看 Jenkins 构建结果和 console log。
- **预期结果**：
  - 构建失败或中止。
  - console log 明确提示失败重试必须提供 pytest node id。
  - 不执行当前模块全部用例。

### TC-JENKINS-F-006 失败重试产物归档与 Allure 发布

- **关联 AC**：`AC-JENKINS-2.3`
- **优先级**：P0
- **测试目标**：验证失败重试也生成并归档完整运行产物。
- **前置条件**：失败重试 Job 已使用有效 node id 构建完成。
- **测试步骤**：
  1. 打开 Jenkins 构建 artifact。
  2. 检查运行目录中的 summary、failed node ids、console log 和 Allure 产物。
  3. 检查 Allure 插件发布或降级提示。
- **预期结果**：
  - 失败重试与其他脚本使用相同归档契约。
  - 产物路径稳定，便于后续后端同步。

### TC-JENKINS-ST-002 失败重试后续同步语义不更新日期和执行时间

- **关联 AC**：`AC-JENKINS-2.4`
- **优先级**：P1
- **测试目标**：验证失败重试被标记为不更新模块“日期”和“执行时间”。
- **前置条件**：无需真实后端同步。
- **测试步骤**：
  1. 检查需求说明、测试用例、RTM 和 README 的失败重试同步语义。
  2. 检查失败重试脚本说明是否与 daily/module rerun 区分。
- **预期结果**：
  - 失败重试只影响后续失败用例状态、失败数和通过率同步。
  - 不更新模块“日期”和“执行时间”。

### TC-JENKINS-F-007 模块重试执行当前模块全部用例

- **关联 AC**：`AC-JENKINS-3.1`
- **优先级**：P0
- **测试目标**：验证模块重试脚本使用 `RETRY_MODE=module` 并按 `CASE_PATH` 执行。
- **前置条件**：模块重试 Job 已创建。
- **测试步骤**：
  1. 打开模块重试 Job 的 Build with Parameters。
  2. 输入当前模块 `CASE_PATH` 和 `MODULE_NAME`。
  3. 手工触发构建。
  4. 查看 console log 与 summary。
- **预期结果**：
  - Pipeline 固定传入 `RETRY_MODE=module`。
  - 执行范围为当前模块全部用例。
  - 不要求输入 `PYTEST_NODE_IDS`。

### TC-JENKINS-F-008 模块重试产物归档与 Allure 发布

- **关联 AC**：`AC-JENKINS-3.2`
- **优先级**：P0
- **测试目标**：验证模块重试运行产物完整。
- **前置条件**：模块重试 Job 已完成一次构建。
- **测试步骤**：
  1. 查看 Jenkins archived artifacts。
  2. 检查 summary、failed node ids、console log、Allure results/report。
  3. 检查 Allure 发布或降级提示。
- **预期结果**：
  - 模块重试归档契约与每日全量一致。
  - 后续平台可按相同产物结构同步。

### TC-JENKINS-ST-003 模块重试后续同步语义为更新日期和执行时间

- **关联 AC**：`AC-JENKINS-3.3`
- **优先级**：P1
- **测试目标**：验证模块重试后续同步会更新模块“日期”和“执行时间”。
- **前置条件**：无需真实后端同步。
- **测试步骤**：
  1. 检查需求说明、测试用例、RTM 和 README 的模块重试同步语义。
  2. 检查脚本命名和说明是否标记为 module rerun。
- **预期结果**：
  - 模块重试被归类为会更新模块“日期”和“执行时间”的执行类型。
  - 本阶段不出现实际入库逻辑。

## 4. 兼容性、边界和安全测试

### TC-JENKINS-E-001 三条脚本均兼容 Windows/Linux Jenkins agent

- **关联 AC**：`AC-JENKINS-1.2`、`AC-JENKINS-2.3`、`AC-JENKINS-3.2`
- **优先级**：P0
- **测试目标**：验证共享脚本保留 `isUnix()` 分支，分别使用 `sh` 和 `bat`。
- **测试步骤**：
  1. 运行 Jenkins 静态测试。
  2. 检查三条业务脚本均加载共享执行逻辑。
  3. 检查共享逻辑包含 Linux 与 Windows 命令分支。
- **预期结果**：
  - 静态测试通过。
  - 不存在只支持单一平台的执行命令。

### TC-JENKINS-E-002 本地挂载仓库可跳过 checkout

- **关联 AC**：`AC-JENKINS-1.2`、`AC-JENKINS-2.1`、`AC-JENKINS-3.1`
- **优先级**：P1
- **测试目标**：验证 `LOCAL_WORKSPACE_REPO=true` 仍可跳过 `checkout scm`。
- **测试步骤**：
  1. 检查共享 Pipeline 中 `LOCAL_WORKSPACE_REPO` 分支。
  2. 检查三条 Jenkinsfile 入口均加载共享逻辑。
- **预期结果**：
  - 本地 Docker Jenkins 挂载仓库时不会强制 scm checkout。
  - 真实 Jenkins Job 仍可 checkout scm。

### TC-JENKINS-ERR-002 Allure HTML 未生成时构建明确失败

- **关联 AC**：`AC-JENKINS-1.3`、`AC-JENKINS-2.3`、`AC-JENKINS-3.2`
- **优先级**：P0
- **测试目标**：验证 Allure HTML 生成失败不会被静默归档为空报告。
- **测试步骤**：
  1. 运行 Jenkins 静态测试，检查 Allure summary 校验逻辑。
  2. 人工破坏 Allure 生成环境后触发任一 Job（Jenkins 验收时可选）。
- **预期结果**：
  - summary 中 `allure_report_status != generated` 时 Pipeline 失败。
  - console log 明确输出 Allure HTML 未生成的原因。

### TC-JENKINS-SEC-001 仓库不提交真实凭据和运行产物

- **关联 AC**：全部 AC 的安全前置
- **优先级**：P0
- **测试目标**：验证 Groovy、Jenkinsfile、README、`.env.example` 不包含真实账号、Token、Cookie、生产 URL 或 Allure HTML 产物。
- **测试步骤**：
  1. 检查 git diff。
  2. 检查新增/修改文件内容。
  3. 确认未提交 `api-test/runtime/`、Jenkins workspace、Allure HTML 或 console log 运行产物。
- **预期结果**：
  - 仅提交脚本、测试、文档和可公开模板。
  - 敏感信息仍由 Jenkins Credentials、私有环境变量或本地 `.env` 管理。

## 5. 覆盖矩阵

| AC 编号 | 覆盖用例 |
| --- | --- |
| `AC-JENKINS-1.1` | `TC-JENKINS-F-001` |
| `AC-JENKINS-1.2` | `TC-JENKINS-F-002`、`TC-JENKINS-E-001`、`TC-JENKINS-E-002` |
| `AC-JENKINS-1.3` | `TC-JENKINS-F-003`、`TC-JENKINS-ERR-002` |
| `AC-JENKINS-1.4` | `TC-JENKINS-ST-001` |
| `AC-JENKINS-2.1` | `TC-JENKINS-F-004`、`TC-JENKINS-F-005`、`TC-JENKINS-E-002` |
| `AC-JENKINS-2.2` | `TC-JENKINS-ERR-001` |
| `AC-JENKINS-2.3` | `TC-JENKINS-F-006`、`TC-JENKINS-E-001`、`TC-JENKINS-ERR-002` |
| `AC-JENKINS-2.4` | `TC-JENKINS-ST-002` |
| `AC-JENKINS-3.1` | `TC-JENKINS-F-007`、`TC-JENKINS-E-002` |
| `AC-JENKINS-3.2` | `TC-JENKINS-F-008`、`TC-JENKINS-E-001`、`TC-JENKINS-ERR-002` |
| `AC-JENKINS-3.3` | `TC-JENKINS-ST-003` |

## 6. 覆盖校验结论

- 正常场景：已覆盖三条脚本的人工触发、定时触发、执行模式和产物归档。
- 异常场景：已覆盖失败重试缺少 node id、Allure 生成失败、安全凭据泄露风险。
- 边界值：已覆盖单条/多条 node id、换行/逗号输入、Windows/Linux agent、本地挂载仓库。
- 状态流转：本阶段无平台任务状态机；已覆盖三类执行结果对后续“日期”和“执行时间”的同步语义。
- 权限边界：本阶段权限由 Jenkins 自身控制；平台 Cookie 和角色权限留到下一阶段。
