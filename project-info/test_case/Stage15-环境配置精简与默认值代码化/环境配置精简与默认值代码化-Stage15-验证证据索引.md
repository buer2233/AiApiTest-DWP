# 环境配置精简与默认值代码化-Stage15-验证证据索引

## 1. 本地自动化证据

| 验证域 | 命令摘要 | 结果 |
| --- | --- | --- |
| Stage15 配置/地址目标测试 | `pytest` 配置契约、Preflight 与地址派生测试 | 最终增量 `35 passed` |
| Jenkins 全量 | `python -m pytest jenkins/tests -q`（禁用外部插件自动加载） | `342 passed, 1 skipped` |
| 后端全量与覆盖率 | `back-end/` 执行 `python -m pytest` | `324 passed`，总覆盖率 `90%` |
| 前端单元测试 | `front-end/` 执行 `npm run test:unit` | `25 passed` |
| 前端类型检查 | `front-end/` 执行 `npm run typecheck` | 通过 |
| 前端生产构建 | `front-end/` 执行 `npm run build` | 通过；仅保留既有第三方注释与 chunk size warning |
| Compose 静态解析 | `docker compose --env-file .env -f docker-compose.yml config --quiet` | 通过，未启动服务 |
| IPv6 Compose 静态解析 | 临时进程变量使用 IPv6 bind host 执行同一 `config --quiet` | 通过，未修改 `.env`、未启动服务 |
| Helper 语法 | PowerShell AST、Bash CRLF 归一化后 `bash -n` | 通过，未执行 helper |
| Git 格式检查 | `git diff --check` | 通过 |
| 配置安全 | `.env` ignore、模板私有键、退休键生产读取和当前文档扫描 | 通过；未输出配置值 |

## 2. TDD 证据摘要

| 行为 | RED | GREEN |
| --- | --- | --- |
| Stage15 初始配置收敛 | 目标契约测试共 18 项在旧实现下暴露键集合、地址和固定值覆盖缺口 | `18 passed` |
| 后端固定配置消费者 | 7 项目标行为因旧 env 读取失败 | 目标测试 `69 passed`；后端全量 `323 passed` |
| Jenkins 历史契约迁移 | 初始 `50 failed, 267 passed, 1 skipped` | `318 passed, 1 skipped` |
| 首次模板私有区标记 | 新测试因 `.env.example` 缺少标记失败 | 模板/私有公共投影测试通过 |
| worker 心跳阈值代码化 | 2 项测试证明旧容器 env 仍可覆盖阈值 | 移除 Compose 注入与 env 读取后 3 项目标测试通过 |
| 独立审查修复 | 17 项有效 RED 覆盖 host/IPv6、Summary、Preflight、错序和文档漂移 | 目标测试 `85 passed`；全量结果见 §1 |
| 复审追加配置安全缺口 | 私有单边错序、模板重复键、整文件读取和读取异常覆盖均有可执行复现 | 配置契约与 Preflight `35 passed` |
| 固定 Job #31 RED | `config --no-interpolate` 将 typed `host_ip` 占位符误判为 IP | 移除不兼容调用，保留实际渲染 `config --quiet` |
| 固定 Job #32 RED | api-runner 无私有 `.env` 的安全边界与 Stage3 三次截图预算不足 | 合成契约 + 宿主附加验证；单用例超时 60 秒 |

## 3. Jenkins 验收证据

固定入口：`scripts/trigger-platform-bootstrap.ps1`，Job 固定为 `AiApiTest-DWP-Platform-Bootstrap`。

| 证据 | 状态 |
| --- | --- |
| Job/build | `AiApiTest-DWP-Platform-Bootstrap #33`，`SUCCESS`，`BuildAll=false`、`RunFullTests=true`，约 18.8 分钟 |
| 失败到成功链路 | #31 Preflight RED；#32 Tests RED；修复并复审后 #33 八阶段全绿 |
| Build Summary | `platform-bootstrap-summary.json`、`platform-bootstrap-summary.md`、`platform-bootstrap-addresses.json`；Summary `success=true` |
| 测试 artifact | `tests.json`、`backend-junit.xml`、`frontend-unit-junit.xml`、`tooling-junit.xml`、`frontend-build.log` |
| Allure / Playwright artifact | `allure-report.zip`、`allure-summary.json`、Playwright `index.html` |
| 八阶段、三项应用服务与基础服务 ID 边界 | 八阶段全 `SUCCESS`；部署 backend/frontend/jenkins-sync-worker；MySQL/Jenkins ID 保持不变 |

## 4. 独立审查证据

| 阶段 | 状态 |
| --- | --- |
| 独立对抗审查 | 首轮完成：`0 Critical / 3 Important / 1 Minor` |
| 独立代码 review | 首轮完成：`0 Critical / 4 Important / 2 Minor` |
| 主 agent 修复与回归 | 已修复合并后的 6 项 Important 与 3 项 Minor；全量回归通过 |
| 复审追加问题 | 3 项 Important 与 1 项 Minor 均修复；配置契约与 Preflight `35 passed` |
| 真实 Job 追加问题 | #31 兼容性与 #32 测试边界/稳定性均按 RED/GREEN 修复并复审 |
| 同 reviewer 最终复审 | 已完成：`0 Critical / 0 Important / 0 Minor` |

> 原始 pytest、Vitest、build、Jenkins console log 和截图不提交 Git；本文件仅保存可追溯摘要与 artifact 索引。
