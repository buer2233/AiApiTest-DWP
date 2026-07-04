# 初始版本收尾-Stage2-MySQL与环境变量配置收尾-可追溯矩阵

> 当前状态：已完成回归验证，等待主人最终验收。

## 追溯矩阵

| AC 编号 | 需求功能 | 测试用例编号 | UI 元素 / 页面 | API 契约 | 实现位置（文件:符号） | 验收状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `AC1.1` | F1 后端正式数据库切换到 MySQL | TC-F-001 | 无 | 无业务 API 变更 | `back-end/config/settings/base.py:load_env_file`、`back-end/config/settings/base.py:build_database_config`、`back-end/tests/test_environment_settings.py` | 通过 |
| `AC1.2` | F1 后端正式数据库切换到 MySQL | TC-F-002、TC-F-003、TC-ERR-002 | 无 | 无业务 API 变更 | `docker-compose.yml`、`back-end/config/settings/base.py`、MySQL 迁移/导入命令证据 | 通过 |
| `AC1.3` | F1 后端正式数据库切换到 MySQL | TC-F-004 | 无 | 无业务 API 变更 | `back-end/accounts/management/commands/init_admin.py`、`.env.example` 初始化管理员变量、`project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-init_admin证据-20260704.txt` | 通过 |
| `AC1.4` | F1 后端正式数据库切换到 MySQL | TC-F-005 | 无 | 无业务 API 变更 | `back-end/config/settings/test.py`、`back-end/tests/test_environment_settings.py` | 通过 |
| `AC2.1` | F2 前端与 Playwright 配置从根 `.env` 派生 | TC-F-006、TC-E-001 | 无 | 无业务 API 变更 | `front-end/config/env.ts`、`front-end/vite.config.ts`、`front-end/tests/config-env.test.ts` | 通过 |
| `AC2.2` | F2 前端与 Playwright 配置从根 `.env` 派生 | TC-F-006 | 无 | 无业务 API 变更 | `front-end/config/env.ts`、`front-end/vite.config.ts` | 通过 |
| `AC2.3` | F2 前端与 Playwright 配置从根 `.env` 派生 | TC-F-007、TC-E-001、TC-ERR-001 | 无 | 无业务 API 变更 | `front-end/config/env.ts`、`front-end/playwright.config.ts`、`front-end/e2e/p1-auth.spec.ts` | 通过 |
| `AC2.4` | F2 前端与 Playwright 配置从根 `.env` 派生 | TC-F-006 | 无 | 无业务 API 变更 | `front-end/config/env.ts`、`front-end/src/api/env.ts`、`front-end/src/api/client.ts`、`front-end/tests/api-env.test.ts` | 通过 |
| `AC3.1` | F3 `.env.example` 与流程文档标准化 | TC-F-008、TC-F-009、TC-ERR-002 | 无 | 无业务 API 变更 | `.env.example`、`docker-compose.yml`、`docker/DEPLOYMENT.md`、`project-info/quick-start-all-services.md`、`scripts/deploy-docker.*` | 通过 |
| `AC3.2` | F3 `.env.example` 与流程文档标准化 | TC-F-008、TC-F-009 | 无 | 无业务 API 变更 | `jenkins/tests/test_docker_deployment_static.py`、`jenkins/tests/test_pipeline_static.py` | 通过 |
| `AC3.3` | F3 `.env.example` 与流程文档标准化 | TC-F-010 | 无 | 无业务 API 变更 | `AGENTS.md`、`project-info/AGENTS.md` | 通过 |
| `AC3.4` | F3 `.env.example` 与流程文档标准化 | TC-F-010、TC-ERR-002 | 无 | 无业务 API 变更 | `docker/DEPLOYMENT.md`、`project-info/quick-start-all-services.md`、`scripts/deploy-docker.*` | 通过 |

## 漂移检查清单（一致性自动门禁）

- [x] 无遗漏需求：每个需求 AC 都至少有一条测试用例覆盖
- [x] 无凭空用例：每条测试用例都能追溯到某个 AC
- [x] 无遗漏界面：本需求无新增 UI 页面
- [x] 无契约漂移：本需求不改变业务 API 契约
- [x] 无未实现需求：每个 AC 都有明确实现位置
- [x] 无孤儿代码：实现中没有对应不上任何 AC 的功能
- [x] 全部达成：所有 AC 验收状态为“通过”

## 漂移处置记录

| 发现的漂移 | 类型 | 处置（回写需求 / 补用例 / 补实现 / 上报主人） | 状态 |
| --- | --- | --- | --- |
| 需求仍有 Q1/Q2/Q3 待确认 | 需求冻结门禁 | 主人已裁决：迁移数据但保留 SQLite；Docker 已启动；Jenkins 本轮改、`api-test` 暂不动 | 已关闭 |
| 前端 unit 测试误收集 E2E | 测试范围漂移 | 在 `front-end/vite.config.ts` 中限定 Vitest include/exclude，并补充证据 | 已关闭 |
| 独立审查发现 Jenkins env 未注入、venv 覆盖无效、MySQL root 密码优先级、AC1.3 缺证据和前端 timeout 未接线 | 独立审查门禁 | 补 RED 测试后修复 `docker-compose.yml`、Jenkins pipeline、后端数据库配置、前端 API env，并新增 `init_admin` 证据 | 已关闭 |
