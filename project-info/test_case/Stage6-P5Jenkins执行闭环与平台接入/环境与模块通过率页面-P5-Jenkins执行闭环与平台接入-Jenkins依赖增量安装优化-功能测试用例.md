# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins依赖增量安装优化-功能测试用例

## 1. 测试范围

验证 Jenkins `api-test` 共享 Pipeline 的依赖安装阶段从全量安装改为增量安装，并确保新增脚本在当前 `requirements.txt` 格式下行为稳定。

## 2. 功能测试用例

| 编号 | 优先级 | 场景 | 前置条件 | 操作步骤 | 预期结果 |
| --- | --- | --- | --- | --- | --- |
| IR-001 | P0 | 缺失依赖识别 | requirements 中存在 `requests==2.32.5`，当前环境未安装 requests | 调用 `collect_missing_requirements` | 返回 `requests==2.32.5` |
| IR-002 | P0 | 固定版本不一致识别 | requirements 中存在 `requests==2.32.5`，当前已安装 `requests==2.31.0` | 调用 `collect_missing_requirements` | 返回 `requests==2.32.5` |
| IR-003 | P0 | 全部满足时跳过安装 | requirements 中依赖均已安装且版本一致 | 调用 `install_missing_requirements` | 不调用 `pip install`，返回空列表 |
| IR-004 | P0 | 仅安装缺失项 | pytest 已满足，requests 缺失 | 调用 `install_missing_requirements` | 只执行 `python -m pip install requests==2.32.5` |
| IR-005 | P1 | Windows marker 在 Linux 跳过 | requirements 包含 `pyreadline3==3.5.6; platform_system == "Windows"`，当前平台为 Linux | 调用 `collect_missing_requirements` | 不返回 pyreadline3 |
| IR-006 | P1 | Windows marker 在 Windows 生效 | requirements 包含 `pyreadline3==3.5.6; platform_system == "Windows"`，当前平台为 Windows | 调用 `collect_missing_requirements` | 返回 pyreadline3 安装规格 |
| IR-007 | P1 | 包名归一化 | `pip list` 返回 `Requests_Test`、`Py.YAML` | 调用 `get_installed_packages` | 返回键名归一化为 `requests-test`、`py-yaml` |
| IR-008 | P1 | pip list 失败 | `python -m pip list --format=json` 返回非 0 | 调用 `get_installed_packages` | 抛出包含 `Failed to query installed Python packages` 的 RuntimeError |
| IR-009 | P1 | pip list 非法 JSON | `pip list` 输出不是 JSON | 调用 `get_installed_packages` | 抛出包含 `pip list returned invalid JSON` 的 RuntimeError |
| IR-010 | P0 | Jenkins Linux/Windows 分支均使用增量脚本 | 读取 `api-test-pipeline.groovy` | 检查 `Install API Test Requirements` stage | Linux/Windows 两条命令均先 `python -m venv`，再调用 `tools.install_missing_requirements` |
| IR-011 | P0 | Jenkins 不再全量安装 | 读取 `api-test-pipeline.groovy` | 检查安装 stage | 不存在 `pip install -r requirements.txt` 或其它 `-m pip install` 全量安装命令 |

## 3. 回归测试

- `python -m pytest api-test/tests/test_install_missing_requirements.py api-test/tests/test_requirements.py -q`
- `python -m pytest jenkins/tests/test_pipeline_static.py jenkins/tests/test_docker_deployment_static.py -q`

## 4. 证据文件

- `api-test/tests/evidence/api-test-stage6-p5-incremental-requirements-green-20260706.txt`
- `jenkins/tests/evidence/jenkins-stage6-p5-incremental-requirements-static-green-20260706.txt`
