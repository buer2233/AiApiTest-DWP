# 环境配置精简与默认值代码化-Stage15-可追溯矩阵

## 1. 追溯基线

- 冻结需求：`project-info/demand/Stage15-环境配置精简与默认值代码化/环境配置精简与默认值代码化-Stage15-需求说明.md`
- 功能测试：`project-info/test_case/Stage15-环境配置精简与默认值代码化/环境配置精简与默认值代码化-Stage15-功能测试用例.md`
- UI：`project-info/UI/Stage15-环境配置精简与默认值代码化/环境配置精简与默认值代码化-Stage15-UI适用性说明.md`（N/A）

## 2. AC 覆盖矩阵

| AC 编号 | 测试用例 | 计划实现位置 | 验收状态 |
| --- | --- | --- | --- |
| AC1.1 | S15-CONTRACT-001、S15-CONTRACT-002 | `.env.example`、`jenkins/scripts/platform_bootstrap/env_contract.py` | 本地通过：模板 12 个公共键及私有区标记契约 |
| AC1.2 | S15-CONTRACT-002 | 私有 `.env`、`env_contract.py` | 本地通过：公共注释/分组/顺序一致，私有 16 键不进入模板 |
| AC1.3 | S15-CONTRACT-003 | Compose、DRF、前端、Bootstrap、deploy helper | 本地通过：公共键生产消费者与退休键读取扫描 |
| AC1.4 | S15-CONTRACT-004、S15-CONTRACT-005、S15-HELPER-002 | `base.py`、`front-end/config/env.ts`、`addressing.py`、Summary/helper | 本地通过：地址派生、Vite/Playwright 明文入口测试 |
| AC2.1 | S15-CONTRACT-006、S15-JENKINS-002、S15-JENKINS-003、S15-BACKEND-001、S15-BACKEND-002、S15-BACKEND-005 | DRF settings、Jenkins Init/Pipeline、前端配置、worker healthcheck | 本地通过：退休键不再覆盖固定 Job、超时、Cookie、API path 与心跳阈值 |
| AC2.2 | S15-COMPOSE-001 | `docker-compose.yml`、Compose 静态契约 | 本地通过：Compose 解析成功，无退休键插值 |
| AC2.3 | S15-JENKINS-001、S15-JENKINS-002、S15-BACKEND-001 | Init Groovy、Bootstrap helper、DRF Job binding | 本地通过：固定 Job 名及 40 executors 契约 |
| AC2.4 | S15-BACKEND-004、S15-COMPOSE-001 | `docker-compose.yml`、Django database settings | 本地通过：root 密码仅注入 MySQL，应用使用专用账号 |
| AC3.1 | S15-SECURITY-001、S15-BACKEND-003 | `.env.example`、Compose 私有注入边界、Preflight 条件校验 | 本地通过：模板无私有键，服务令牌仅注入 backend |
| AC3.2 | S15-CONTRACT-006、S15-CONTRACT-007 | `env_contract.py`、`preflight.py` | 本地通过：Docker 命令前稳定返回脱敏漂移诊断 |
| AC3.3 | S15-CONTRACT-007、S15-SECURITY-002 | 契约单元测试、Preflight 证据写入 | 本地通过：缺失/多余/重复/错序诊断不含赋值 |
| AC3.4 | S15-BACKEND-003、S15-SECURITY-002 | 私有 `.env` 机械迁移、Git ignore/diff 安全检查 | 本地通过：`.env` 被忽略，既有敏感值未进入受控 diff 或资料 |
| AC4.1 | S15-HELPER-002、S15-DOCS-001、S15-COMPOSE-001 | 根/模块规则、README、部署/快速启动文档、历史静态测试 | 本地通过：当前文档退休键扫描无残留 |
| AC4.2 | S15-JENKINS-004、S15-REGRESSION-001 | Platform Bootstrap 八阶段、三项应用服务、固定 helper | 固定 Job #33 通过：八阶段全绿、三项应用服务健康、基础服务 ID 保持 |
| AC4.3 | S15-HELPER-001、S15-DOCS-001 | deploy helper、`.env.example` 私有区标记、部署文档 | 本地通过：首次复制后停止且具备明确私有区追加位置 |

## 3. 漂移门禁

- 每个 AC 至少映射一条功能测试用例：已覆盖。
- 每条功能测试用例至少映射一个 AC：已覆盖。
- 本地实现与自动化测试已覆盖全部 AC；AC4.2 已由固定 Jenkins Job #33 和归档 artifact 闭环。
- 独立审查及同 reviewer 复审已闭环为 `0 Critical / 0 Important / 0 Minor`；真实 Job/build 证据在验收包中集中登记。
