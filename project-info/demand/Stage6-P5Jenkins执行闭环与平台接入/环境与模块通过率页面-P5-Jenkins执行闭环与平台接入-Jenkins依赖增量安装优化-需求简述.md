# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins依赖增量安装优化-需求简述

## 0. 需求分级与流程裁剪

- 定级：S 档。
- 定级原因：本需求仅优化既有 Jenkins `api-test` 共享 Pipeline 的依赖安装步骤，不新增页面、不新增数据表、不变更 DRF API、不变更 `api-test` 执行协议和 Allure 报告协议。
- 裁剪说明：无新增 UI 原型；保留需求澄清冻结、架构影响评估、API 契约冻结、容器化兼容检查、功能测试用例、TDD 实现、静态回归和验证证据。

## 1. 背景

`jenkins/scripts/api-test-pipeline.groovy` 原安装阶段每次执行 `pip install -r requirements.txt`，即使虚拟环境中依赖已经满足，也会重复解析和下载依赖，增加 Jenkins Job 执行耗时。

## 2. 目标

- Jenkins 每次构建仍复用 `api-test` 目录下的 Python 虚拟环境。
- 安装阶段先查询当前虚拟环境已安装依赖。
- 将已安装依赖与 `api-test/requirements.txt` 对比。
- 仅安装缺失或固定版本不一致的依赖规格。
- 如果全部依赖已经满足，安装阶段输出跳过提示并进入下一阶段。

## 3. 范围

- 新增 `api-test/tools/install_missing_requirements.py`。
- 修改 `jenkins/scripts/api-test-pipeline.groovy` 的 `Install API Test Requirements` 阶段，Windows/Linux 分支均调用增量安装脚本。
- 补充 api-test 单元测试和 Jenkins 静态结构测试。

## 4. 不做事项

- 不新增 Python 依赖，避免依赖安装脚本在依赖尚未安装时无法运行。
- 不处理复杂 PEP 508 范围版本、extras、URL 依赖和复合 marker；当前 `requirements.txt` 为固定版本锁定，仅需支持当前格式。
- 不修改 Jenkins Job 参数、报告保留策略、Allure 发布逻辑和 DRF API。

## 5. 需求澄清冻结

- [已澄清] 依赖比较范围：以 `api-test/requirements.txt` 为准。
- [已澄清] 安装策略：只安装缺失或 `==` 固定版本不一致的依赖。
- [已澄清] 全部满足时：跳过 pip install 并继续后续 stage。
- 冻结人：主人（对话确认）。
- 冻结日期：2026-07-06。

## 6. 架构影响评估

- DRF：无影响。
- Vue：无影响。
- Jenkins：影响共享 Pipeline 的依赖安装阶段，保持 stage 名称和后续执行链路不变。
- api-test：新增工具脚本和单元测试，不改变 `tools.ci_runner` 执行协议。
- Docker：无新增镜像依赖；脚本使用标准库和当前 Python 解释器内的 pip。
- 数据模型/权限/报告协议：无影响。

## 7. API 契约冻结

本需求不新增或修改 DRF API，API 契约无变化。

## 8. 容器化兼容检查

- 不新增本机绝对路径。
- 不写入真实账号、密码、token、Cookie 或生产地址。
- Jenkins 仍通过 `JENKINS_API_TEST_DIR` 和 `JENKINS_PYTHON_VENV_DIR` 控制路径。
- 脚本通过 `sys.executable -m pip` 查询和安装，兼容 Linux/Windows agent 的虚拟环境。

## 9. 验收口径

- `api-test/tests/test_install_missing_requirements.py` 覆盖缺失依赖、版本不一致、Windows marker、包名归一化、pip list 异常和非法 JSON。
- Jenkins 静态测试确认 Windows/Linux 分支都先创建/复用 venv，再调用 `tools.install_missing_requirements`。
- Jenkins 安装阶段不再出现 `pip install -r requirements.txt` 全量安装命令。
