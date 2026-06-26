# jenkins/AGENTS.md

本目录是 Jenkins Pipeline 和 Groovy 脚本目录。进入 `jenkins/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 模块职责

- Jenkins 参数定义。
- Jenkins stage 编排。
- Windows/Linux agent 兼容。
- 调用 `api-test/tools/ci_runner.py`。
- 归档 `runtime/ci-runs/<run_id>/` 产物。
- 发布或归档 Allure 报告。

## 技术约定

- Groovy 负责 Jenkins 参数、环境变量和 stage 编排。
- pytest 执行、失败 node id 收集、重试和 summary 输出必须由 `api-test/tools/ci_runner.py` 完成。
- Pipeline 必须使用 `isUnix()` 分支兼容 Linux `sh` 和 Windows `bat`。
- 脚本使用 Jenkins workspace 相对路径，不写死 `D:\AI\...` 等本机路径。
- Jenkins 脚本源文件必须放在 `jenkins/` 并纳入 git 管理。


