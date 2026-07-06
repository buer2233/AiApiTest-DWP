# 环境与模块通过率页面-P5-Jenkins执行闭环与平台接入-Jenkins报告本地保留与Allure插件接入-需求简述

## 0. 需求分级与流程裁剪

- **定级结论**：S 档。
- **定级理由**：本次修复既有 Jenkins/api-test 报告落盘、保留和 Jenkins 内展示问题，不新增数据表、不新增页面、不变更 DRF API 和前端路由。
- **裁剪说明**：不新增 UI 原型；沿用 P5 已冻结的 Jenkins 报告入口和 artifact 同步设计。保留需求澄清冻结、架构影响评估、API 契约冻结、容器化兼容检查、TDD、回归证据和本地 Jenkins 验证。

## 1. 背景

主人反馈 `AiApiTest-DWP-Daily-Full-Module #9` 执行成功后，当前宿主机仓库 `api-test` 下没有 Allure 测试报告。排查确认 #9 的报告已生成，但 Job 在容器临时目录 `/tmp/...` 执行；同时当前 Jenkins 容器 `/workspace/AiApiTest-DWP` 挂载的是旧工作区，不是当前 `workspace001` 仓库。因此报告没有落在当前仓库的 `api-test/runtime/ci-runs/<run_id>/`。

## 2. 目标

- 每次 Jenkins Job 执行后，报告必须生成在实际执行仓库的 `api-test/runtime/ci-runs/<run_id>/`。
- 本地 Compose Jenkins 应通过 `PROJECT_WORKSPACE` 挂载当前仓库，并通过本地 Job 配置脚本直接在该挂载路径执行，避免写入容器临时目录。
- 默认不删除本地报告数据；仅自动删除超过 30 天的 `runtime/ci-runs` 历史 run 目录。
- 当前 run 和 30 天内报告必须保留。
- Jenkins 构建记录和 artifact 默认保留 30 天，与本地 runtime 清理策略一致。
- Jenkins 内 Allure 报告展示通过 Allure Jenkins 插件接入；插件缺失时仍保留 artifact 兜底。
- Jenkins 工具链镜像必须提供 `python` 命令入口、允许 Jenkins 用户创建 `/workspace/*@tmp` 控制目录，并自动注册 Allure Commandline 全局工具。
- Allure 插件发布报告时不得把 pytest 失败用例改写为 Jenkins 基础设施失败或不稳定；失败用例状态以 `summary.json` 和 Allure 报告表达。

## 3. 范围

- 修改 `api-test/tools/ci_runner.py`，新增 `CI_RUN_RETENTION_DAYS` 和过期 run 清理能力。
- 修改 `jenkins/scripts/api-test-pipeline.groovy`，配置 Jenkins build/artifact 30 天保留，并传递 `CI_RUN_RETENTION_DAYS`。
- 修改 `docker/jenkins/Dockerfile`，在工具链镜像中预装 `allure-jenkins-plugin`。
- 新增 `jenkins/scripts/configure-allure-commandline.groovy`，用于工具链镜像初始化 Jenkins Allure Commandline。
- 修改 `.env.example`、`docker-compose.yml`、`jenkins/README.md`、`docker/DEPLOYMENT.md`，明确当前仓库挂载、报告目录、保留策略和 Allure 插件启用方式。
- 留存当前 Jenkins 实例 #9 的根因证据。

## 4. 不做事项

- 不提交 `.env`、Jenkins 凭据、真实 token、Cookie 或运行报告。
- 不把 `api-test/runtime/` 运行产物纳入 git。
- 不改 DRF/Vue 报告入口契约。
- 不自动删除 Jenkins 数据卷或 MySQL 数据卷。

## 5. 需求澄清冻结

- [已澄清] 当前 #9 报告实际已生成，但生成路径不是当前宿主机仓库。
- [已澄清] 默认只清理超过 30 天的历史报告，30 天内和当前运行报告必须保留。
- [已澄清] Allure 可接入 Jenkins 内展示，使用 Jenkins Allure 插件；插件缺失时仍归档 runtime artifact。
- [已澄清] 子代理 `Subagent log not found` 审计报告不提交 git。

## 6. 验收口径

- `ci_runner` 单元测试证明默认保留 30 天、可通过 `CI_RUN_RETENTION_DAYS` 覆盖，且只删除超过保留期的历史 run 目录。
- Jenkins 静态测试证明 Pipeline 配置 Jenkins build/artifact 保留策略，并把 `CI_RUN_RETENTION_DAYS` 传给 `ci_runner`。
- Docker 静态测试证明 Compose 注入 `CI_RUN_RETENTION_DAYS`，`.env.example` 文档化该变量，工具链镜像安装 `allure-jenkins-plugin`。
- Docker 静态测试证明工具链镜像安装 `python-is-python3`、初始化 `/workspace` 权限，并把 Allure CLI 注册脚本放入 Jenkins ref init 目录。
- Jenkins 静态测试证明 `Publish Allure` 阶段使用 `resultPolicy: 'LEAVE_AS_IS'`，避免测试失败改变 Jenkins 构建结果。
- 真实 Jenkins 验证中，Job 不再使用 `/tmp/...` 临时目录作为长期执行路径；若当前容器挂载仍指向旧工作区，必须明确提示需要修正本地 `.env` 的 `PROJECT_WORKSPACE` 并重建 Jenkins 容器挂载。

## 7. 架构影响评估

- **Jenkins**：新增 build/artifact 保留策略和 Allure 插件镜像能力，执行协议不变。
- **api-test**：新增 runtime 历史目录清理，不改变 `summary.json`、`failed_nodeids.json`、`allure-results`、`allure-report` 结构。
- **DRF / Vue**：无接口和页面变更。
- **Docker**：工具链镜像构建会额外访问 Debian 软件源、Allure 下载地址和 Jenkins 插件更新中心；默认官方镜像仍可启动，但不能在 Jenkins 内展示 Allure 插件页面。
- **安全**：不提交真实 `.env`、报告产物或本机绝对路径。

## 8. API 契约冻结

本次不涉及 DRF API 契约变更。P5 已有 Jenkins 任务报告字段、artifact URL 和 Allure URL 同步方式保持不变。

## 9. 容器化兼容检查

- `PROJECT_WORKSPACE` 由本地 `.env` 注入，必须指向当前仓库根目录；`.env.example` 只提供占位默认值。
- `AIAPITEST_LOCAL_WORKSPACE` 使用 Compose 服务内路径，默认 `/workspace/AiApiTest-DWP`。
- `CI_RUN_RETENTION_DAYS` 可通过 `.env` 或 Jenkins 私有环境变量覆盖，默认 30。
- 不新增宿主机固定端口。
- 不新增不可迁移本机绝对路径。
