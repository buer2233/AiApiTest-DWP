# Stage 2: api-test 迁移与充分测试

## 需求分析

本阶段目标是把当前分散在仓库根目录的接口自动化测试框架整体迁移到 `api-test/`，并验证迁移后框架仍能独立运行。

### 迁移范围

需要迁移到 `api-test/` 的内容：

- `report/`
- `test_case/`
- `test_data/`
- `utils/`
- `config.py`
- `conftest.py`
- `pytest.ini`
- `requirements.txt`
- `runpytest.py`

### 本阶段不做

- 不开发 pytest node id 失败重试执行器。
- 不开发 Jenkins Groovy Pipeline。
- 不开发 DRF 后端或 Vue 前端。
- 不引入真实账号、token、cookie 或业务系统常量。

### 验收标准

- `api-test/` 下存在完整接口自动化测试框架。
- 根目录不再保留本阶段迁移范围内的框架文件和目录。
- `runpytest.py` 默认入口不再写死某个 demo 模块，模块执行通过命令行参数控制。
- `config.py` 中的框架路径都基于 `api-test/config.py` 所在目录计算。
- 单元测试 `api-test/tests/test_runpytest_commands.py` 通过。
- 在 `api-test/` 下执行 `python runpytest.py --case-path test_case/test_gbif_case --clean` 能正常启动 pytest。
- Allure 原始结果输出到 `api-test/report/allure-results/`。
- 如果本机安装了 Allure CLI，HTML 报告输出到 `api-test/report/allure-report/<timestamp>/`；如果未安装，脚本清晰提示并保留 pytest 退出码。

## TDD 记录

| 步骤 | 命令 | 期望 | 实际 | 状态 |
|------|------|------|------|------|
| RED | `cd api-test; python -m pytest tests/test_runpytest_commands.py -v` | 因框架尚未迁移到 `api-test/` 而失败 | 5 failed，失败原因是 `api-test/report`、`api-test/config.py`、`api-test/runpytest.py` 等尚不存在 | passed |
| GREEN | `cd api-test; python -m pytest tests/test_runpytest_commands.py -v` | 迁移和修复后通过 | 5 passed | passed |
| 回归 | `cd api-test; python runpytest.py --case-path test_case/test_gbif_case --clean` | demo 模块可执行 | 14 passed, 1 skipped，Allure 报告生成成功 | passed |
| PyCharm RED | `cd api-test; python -m pytest tests/test_pycharm_migration_config.py -v` | 发现旧 PyCharm 测试工作目录配置 | 2 failed，`.idea/workspace.xml` 仍引用 `$PROJECT_DIR$/test_case/test_gbif_case` 和 `$PROJECT_DIR$/runpytest.py` | passed |
| PyCharm GREEN | `cd api-test; python -m pytest tests/test_pycharm_migration_config.py -v` | PyCharm 配置不再引用旧路径 | 2 passed | passed |
| PyCharm 等效单测 | `cd api-test/test_case/test_gbif_case; python -m pytest test_gbif_api.py::TestGbifAPI::test_species_search_by_keyword -q` | 单个用例可用新工作目录执行 | 1 passed | passed |

## 迁移记录

- 已将 `report/` 移动到 `api-test/report/`。
- 已将 `test_case/` 移动到 `api-test/test_case/`。
- 已将 `test_data/` 移动到 `api-test/test_data/`。
- 已将 `utils/` 移动到 `api-test/utils/`。
- 已将 `config.py` 移动到 `api-test/config.py`。
- 已将 `conftest.py` 移动到 `api-test/conftest.py`。
- 已将 `pytest.ini` 移动到 `api-test/pytest.ini`。
- 已将 `requirements.txt` 移动到 `api-test/requirements.txt`。
- 已将 `runpytest.py` 移动到 `api-test/runpytest.py`。
- 已新增 `api-test/tests/test_runpytest_commands.py`，覆盖迁移后的关键路径和命令构造。
- 已将 `api-test/runpytest.py` 的脚本入口改为 `main()`，不再默认写死 `test_case/test_gbif_case`。
- 已更新 `.gitignore`，忽略迁移后的 `api-test/report/allure-results/`、`api-test/report/allure-report/`、`api-test/logs/`、`api-test/runtime/`。
- 已修复 `.idea/workspace.xml` 中 PyCharm 临时测试配置的旧工作目录，把 `$PROJECT_DIR$/test_case/test_gbif_case` 改为 `$PROJECT_DIR$/api-test/test_case/test_gbif_case`。
- 已修复 PyCharm `runpytest` 配置，把脚本路径从 `$PROJECT_DIR$/runpytest.py` 改为 `$PROJECT_DIR$/api-test/runpytest.py`，工作目录改为 `$PROJECT_DIR$/api-test`。
- 已新增 `api-test/tests/test_pycharm_migration_config.py`，防止 PyCharm 配置再次引用旧根目录 `test_case` 路径。
- 已适配当前 `page_api` 目录位于 `api-test/page_api/` 的结构，测试用例通过 `from page_api...` 导入接口方法。

## 测试结果详情

### RED

```text
命令：cd D:\AI\AiApiTest-DWP\api-test; python -m pytest tests/test_runpytest_commands.py -v
结果：5 failed
原因：测试先断言迁移后的框架文件应在 api-test/ 下，执行时迁移尚未完成，因此符合 RED 预期。
```

### GREEN

```text
命令：cd D:\AI\AiApiTest-DWP\api-test; python -m pytest tests/test_runpytest_commands.py -v
结果：5 passed in 0.16s
```

### 回归

```text
命令：cd D:\AI\AiApiTest-DWP\api-test; python runpytest.py --case-path test_case/test_gbif_case --clean
结果：14 passed, 1 skipped in 7.45s
Allure HTML：D:\AI\AiApiTest-DWP\api-test\report\allure-report\20260622_175347
```

### PyCharm 手动执行修复

```text
问题：PyCharm 手动点击 api-test/test_case/test_gbif_case/test_gbif_api.py 中的测试时，仍使用旧工作目录 D:\AI\AiApiTest-DWP\test_case\test_gbif_case，导致 Cannot start a process。
根因：.idea/workspace.xml 的临时 Run Configuration 和 coverage 配置仍引用迁移前路径。
RED：cd D:\AI\AiApiTest-DWP\api-test; python -m pytest tests/test_pycharm_migration_config.py -v -> 2 failed
GREEN：cd D:\AI\AiApiTest-DWP\api-test; python -m pytest tests/test_pycharm_migration_config.py -v -> 2 passed
等效手动执行：cd D:\AI\AiApiTest-DWP\api-test\test_case\test_gbif_case; python -m pytest test_gbif_api.py::TestGbifAPI::test_species_search_by_keyword -q -> 1 passed
```

## 问题记录

- Stage 2 开始前已有未提交改动：`AGENTS.md`、`README.md`、`config.py`、`test_case/page_api/gbif/gbif_api.py`、`test_case/test_gbif_case/test_gbif_api.py`。本阶段迁移保留这些内容，不做回滚。
- Allure HTML 报告属于运行产物，路径已加入 `.gitignore`，不作为业务代码提交。
- 2026-06-23 PyCharm 手动运行报错已修复；如果 PyCharm 仍复用旧临时配置，可删除旧 Run Configuration 后重新从 `api-test/test_case/test_gbif_case/test_gbif_api.py` 右键运行。
