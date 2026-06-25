# Jenkins Groovy Pipeline

## 阶段范围

Stage 4 实现 Jenkins Groovy Pipeline，使 Jenkins 可以通过参数触发 `api-test/tools/ci_runner.py`，完成接口用例执行、失败用例重试、Allure 结果生成、运行产物归档和 Allure 插件发布。

本阶段只负责 Jenkins 参数、环境变量、stage 编排和跨平台命令分支。pytest 命令构造、失败 node id 读取、重试次数、summary 输出和 Allure HTML 生成仍由 `api-test/tools/ci_runner.py` 负责。

## Jenkins 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CASE_PATH` | `test_case/test_gbif_case` | pytest 模块或用例目录，相对 `api-test/` |
| `PYTEST_NODE_IDS` | 空 | 多个 pytest node id，支持换行或英文逗号分隔 |
| `RETRY_MODE` | `none` | 可选值：`none`、`selected`、`all-failed`、`module` |
| `RETRY_COUNT` | `0` | 传给 `pytest-rerunfailures` 的重试次数 |
| `CLEAN_ALLURE` | `true` | 是否传递清理 Allure 结果目录的语义 |
| `OPEN_REPORT` | `false` | 是否打开 Allure HTML 报告，CI 环境建议保持 false |

Pipeline 会把这些参数写入同名环境变量，并设置：

```text
RUN_ID=<Jenkins BUILD_TAG 或 BUILD_NUMBER>
CI_RUNNER_ENV=jenkins
```

`ci_runner` 支持通过以下命令读取 Jenkins 环境变量：

```powershell
cd api-test
python -m tools.ci_runner --from-jenkins-env
```

## Pipeline 脚本

脚本文件：

```text
jenkins/Jenkinsfile
jenkins/scripts/api-test-pipeline.groovy
```

`Jenkinsfile` 只加载可复用脚本：

```groovy
def pipelineScript = load 'jenkins/scripts/api-test-pipeline.groovy'
pipelineScript.call()
```

`api-test-pipeline.groovy` 使用 `isUnix()` 在 Linux/macOS agent 上执行 `sh`，在 Windows agent 上执行 `bat`。所有路径都使用 Jenkins workspace 相对路径，不写死本机绝对路径。

## Pipeline 阶段

| 阶段 | 作用 |
|------|------|
| `Checkout` | 拉取当前仓库 |
| `Prepare Python` | 输出 Python 版本，确认 agent 可执行 Python |
| `Install API Test Requirements` | 安装 `api-test/requirements.txt` |
| `Run API Tests` | 调用 `python -m tools.ci_runner --from-jenkins-env` |
| `Generate Allure Report` | 输出本次 `summary.json`，Allure HTML 由 `ci_runner` 在执行后生成 |
| `Archive Runtime Artifacts` | 归档 `api-test/runtime/ci-runs/<run_id>/**` |
| `Publish Allure` | 调用 Jenkins Allure 插件发布 `allure-results`；插件缺失时仍保留归档产物 |

`Run API Tests` 把 pytest 断言失败视为测试结果，不把 Jenkins stage 标记为失败。
`api-test/tools/ci_runner.py` 在 Jenkins 环境下保持进程退出码为 `0`，同时在 `summary.json` 中保留 pytest 原始 `return_code`、`status=failed` 和失败 node id。
这样 Jenkins job 能继续显示为一次有效构建，失败用例由 Allure 报告和运行摘要表达；只有参数错误、执行器异常或后续 Allure HTML 未生成这类基础设施问题才会让 Pipeline 失败。

## 运行产物

每次 Jenkins 构建的运行产物位于：

```text
api-test/runtime/ci-runs/<run_id>/
├── console.log
├── failed_nodeids.json
├── summary.json
├── allure-results/
└── allure-report/
```

## 本地测试命令与结果

### RED

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_ci_runner.py -v
```

结果：`2 failed, 8 passed`，失败原因是 `parse_jenkins_node_ids` 和 `build_run_request_from_jenkins_env` 尚不存在。

```powershell
cd D:\AI\AiApiTest-DWP\jenkins
python -m pytest tests/test_pipeline_static.py -v
```

结果：`3 failed`，失败原因是 `jenkins/Jenkinsfile` 和 `jenkins/scripts/api-test-pipeline.groovy` 尚不存在。

补强 RED：

```powershell
cd D:\AI\AiApiTest-DWP\jenkins
python -m pytest tests/test_pipeline_static.py::test_pipeline_preserves_artifacts_when_pytest_fails -v
```

结果：`1 failed`，失败原因是 Pipeline 仍会把 pytest 用例失败传播为 Jenkins stage 失败。

### GREEN

```powershell
cd D:\AI\AiApiTest-DWP\api-test
python -m pytest tests/test_ci_runner.py -v
```

结果：`10 passed`。

```powershell
cd D:\AI\AiApiTest-DWP\jenkins
python -m pytest tests/test_pipeline_static.py -v
```

结果：`4 passed`。

Jenkins 环境变量模式烟测：

```powershell
cd D:\AI\AiApiTest-DWP\api-test
$env:CASE_PATH='test_case/test_gbif_case'
$env:PYTEST_NODE_IDS=''
$env:RETRY_MODE='module'
$env:RETRY_COUNT='0'
$env:CLEAN_ALLURE='true'
$env:OPEN_REPORT='false'
$env:RUN_ID='stage4-jenkins-env-smoke'
python -m tools.ci_runner --from-jenkins-env
```

结果：exit code 0，Allure HTML 生成到 `api-test/runtime/ci-runs/stage4-jenkins-env-smoke/allure-report`。

## 验证限制

当前本地环境未连接真实 Jenkins job，本阶段完成的是 Jenkinsfile/Groovy 静态结构验证和 `ci_runner` Jenkins 参数兼容验证。真实 Jenkins 验收时需要确认：

- Jenkins agent 已安装 Python 和 Allure CLI。
- Jenkins job 使用仓库根目录作为 workspace。
- Jenkins 安装 Allure 插件时可在构建页展示报告。
- 如果 Allure 插件未安装，构建产物中仍可下载 `allure-report/` 和 `allure-results/`。

## 已知问题与后续建议

- `Generate Allure Report` 阶段当前打印 `summary.json`，实际 Allure HTML 生成在 `ci_runner` 中完成，避免 Groovy 重复实现报告逻辑。
- Stage 7 后端 Jenkins API 需要与本阶段参数名保持一致。
- 如果后续 Jenkins 多分支 job 的 `BUILD_TAG` 包含特殊路径字符，需要再补 run id 规范化策略。
