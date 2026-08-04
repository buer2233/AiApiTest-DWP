# 环境配置精简与默认值代码化-Stage15-功能测试用例

## 1. 测试范围

- 依据：`project-info/demand/Stage15-环境配置精简与默认值代码化/环境配置精简与默认值代码化-Stage15-需求说明.md` v1.0-frozen。
- 需求分级：L；覆盖根环境契约、DRF、Vue/Vite/Playwright、Docker Compose、Jenkins Init/Pipeline、Platform Bootstrap helper、文档与安全边界。
- UI：N/A；本需求不新增页面、路由、组件或 DOM，不执行视觉原型验收。
- API：N/A；不改变 DRF 业务 API 契约，仅回归既有健康接口、Jenkins 编排和环境目录内部接口。
- 测试数据：所有凭据使用不可用占位值；禁止读取、记录或断言本地 `.env` 的实际值。

## 2. 优先级定义

| 优先级 | 定义 |
| --- | --- |
| P0 | 配置契约、安全、唯一环境入口或服务启动链路的阻断场景 |
| P1 | 派生地址、固定默认值、跨平台兼容和文档一致性场景 |

## 3. 功能测试用例

| 用例编号 | 关联 AC | 优先级 | 测试目标 | 前置条件 / 测试数据 | 操作步骤 | 预期结果 |
| --- | --- | --- | --- | --- | --- | --- |
| S15-CONTRACT-001 | AC1.1 | P0 | 模板只包含冻结的 12 个公共键 | 使用受版本控制的 `.env.example` | 解析非注释赋值行并按出现顺序收集键名 | 键名、顺序与冻结契约完全一致；不存在未知、重复、固定或私有键 |
| S15-CONTRACT-002 | AC1.1、AC1.2 | P0 | 两文件公共区结构一致 | `.env` 已完成安全迁移 | 忽略赋值右侧并在私有区标记处截断，逐行比较两文件公共区 | 分组、中文注释、空行、键名和顺序完全一致；允许公共值不同 |
| S15-CONTRACT-003 | AC1.3 | P0 | 每个公共键都有生产消费者 | 冻结公共键集合 | 扫描 Compose、DRF、前端配置、Bootstrap 与 deploy helper | 每个公共键至少存在一个生产读取点，不允许只出现在文档或测试中 |
| S15-CONTRACT-004 | AC1.4 | P0 | 公共地址统一派生 | 主机 `platform.example.test`、协议 `https`、非默认四服务端口 | 分别加载 DRF、Bootstrap Summary 和 helper 配置 | Jenkins/backend/frontend/MySQL 地址均使用同一公开主机和对应端口；API 固定追加 `/api/v1` |
| S15-CONTRACT-005 | AC1.4 | P1 | 本地 Vite 与 Playwright 使用真实明文入口 | 公开协议设为 `https`，Vite webServer 未配置 TLS | 解析 Vite 代理目标和 Playwright baseURL | 本地直连地址仍为 `http`；不得生成无法访问的本地 `https` URL |
| S15-CONTRACT-006 | AC2.1、AC3.2 | P0 | 遗留固定键被拒绝且不能覆盖行为 | 在合法私有配置中追加一个已退休键 | 执行契约校验与 Preflight | 在任何 Docker 命令前以 `CONFIG_ENV_CONTRACT_DRIFT` 失败；产品常量保持冻结值 |
| S15-CONTRACT-007 | AC2.1、AC3.2 | P0 | 缺失、错序、多余和重复均可诊断 | 分别构造四份脱敏配置变体 | 对每个变体执行契约校验 | 每种漂移都失败；诊断含类型、键名和适用行号，不含赋值 |
| S15-JENKINS-001 | AC2.3 | P0 | 固定 Bootstrap Job 名不可被 env 改名 | 私有配置残留旧 Job 名键 | 加载 Init Groovy 与 helper，扫描生产读取 | 两端均使用 `AiApiTest-DWP-Platform-Bootstrap` 代码常量；旧键被契约拒绝且无生产读取 |
| S15-JENKINS-002 | AC2.1、AC2.3 | P0 | 固定 Job 集、executor 和超时不可覆盖 | 设置旧 Job、executor、请求/轮询/总超时键为异常值 | 运行静态契约和 helper 单元测试 | Job 集、executor=40、请求/轮询/总超时仍使用代码常量，旧 env 不影响行为 |
| S15-JENKINS-003 | AC2.1 | P0 | Stage13 一次性删除能力彻底退役 | 检查 Init Groovy、Compose 与文档 | 搜索两个删除开关、allowlist 和 `Job.delete()` 分支 | 生产代码无删除开关读取和受控删除分支；仍可幂等修复受管 Job |
| S15-JENKINS-004 | AC2.1、AC4.2 | P0 | 本地挂载固定化后仍创建 Job | Compose 不再注入 `LOCAL_WORKSPACE_REPO` | 静态检查 Init Groovy 与 Jenkinsfile 的 workspace 路径和控制流 | Init 不会因缺少开关提前退出；固定使用容器内 `/workspace/AiApiTest-DWP`；环境目录 Job 仍使用隔离 SCM checkout |
| S15-BACKEND-001 | AC2.1、AC2.3 | P0 | 后端 Job binding 使用固定名称 | 进程环境提供错误的旧 Job 名 | 执行 `sync_jenkins_job_bindings` 单元测试 | 失败重试、模块重试和 Daily 绑定均写入冻结 Job 名，忽略旧 env |
| S15-BACKEND-002 | AC1.4、AC2.1 | P1 | 后端 Jenkins client 和序列化链接统一派生 | 使用非默认公开主机/协议/端口 settings | 创建 Jenkins config 并序列化构建链接 | 内部 API 固定 `http://jenkins:8080`；公开链接来自派生 settings；请求超时固定 15 秒 |
| S15-BACKEND-003 | AC3.1、AC3.4 | P0 | 环境目录服务令牌正确闭环 | backend 仅注入 `ENVIRONMENT_CATALOG_SERVICE_TOKEN`，不注入 SCM URL | 加载 settings 并调用内部接口鉴权测试 | settings 能直接读取令牌；worker 未收到令牌；同步启用时 Preflight 条件必填相关私有项 |
| S15-BACKEND-004 | AC2.4 | P0 | MySQL root 凭据不传播 | 渲染 Compose 配置 | 检查 backend、worker、backend-bootstrap 的 environment | 三者都不含 root 密码；仅 MySQL 服务使用 root 密码；应用只使用 `DB_USER`/`DB_PASSWORD` |
| S15-BACKEND-005 | AC2.1 | P1 | Cookie 固定策略与公开协议一致 | 分别使用 `http`、`https` 公开协议 | 重载 Django settings | Cookie 名、时长、SameSite、Path 固定；`Secure` 在 HTTPS 时为 true、HTTP 时为 false |
| S15-SECURITY-001 | AC3.1 | P0 | 模板不公开任何私有项 | 私有键冻结清单 | 扫描 `.env.example` 的键和敏感模式 | 不含账号、密码、token、密钥、初始化账号和内部同步配置键，也无可用凭据占位 |
| S15-SECURITY-002 | AC3.3、AC3.4 | P0 | 失败输出和 Git diff 不泄露真实值 | 本地 `.env` 含现有私有值 | 触发契约失败，检查 pytest/Jenkins 摘要和 `git diff` | 仅出现键名/状态/行号；`.env` 不被 Git 跟踪，实际值不出现在日志、diff 或验收资料 |
| S15-HELPER-001 | AC1.4、AC4.3 | P0 | 首次 bootstrap 不误用缺凭据模板 | 临时目录不存在 `.env` | 分别执行 PowerShell/Bash helper 的静态/隔离测试 | helper 生成公共模板后明确停止，要求人工补私有配置；不会继续启动基础服务 |
| S15-HELPER-002 | AC1.4、AC4.1 | P1 | 两套 helper 使用相同新键派生提示 | 准备合法脱敏配置 | 检查 PowerShell/Bash 地址解析 | 两端均只读取平台公开主机/协议和端口；不再读取旧 URL、bind host 或 Job 名键 |
| S15-COMPOSE-001 | AC2.2、AC2.4 | P0 | Compose 无退休插值且内部地址固定 | 使用 `.env.example` 渲染静态 Compose | 执行 `docker compose config` 和静态扫描，不启动服务 | 配置可解析；无 `${退休键...}`；内部依赖仍使用 `mysql:3306`、`jenkins:8080`、`backend:8000` |
| S15-DOCS-001 | AC4.1、AC4.3 | P1 | 当前使用文档与规则同步 | Stage15 实现完成 | 扫描根/模块 AGENTS、README、部署和快速启动文档 | 当前指南只介绍新公共键、私有配置边界、固定 Job 和唯一 Jenkins 入口；历史阶段归档不被篡改 |
| S15-REGRESSION-001 | AC4.2 | P0 | 固定环境 Job 完整回归 | 主人已 bootstrap MySQL/Jenkins，私有配置有效 | 仅通过固定 trigger helper 运行 Platform Bootstrap，开启全量测试 | 八阶段保持不变；backend/frontend/worker 健康；MySQL/Jenkins 不被 helper 管理；摘要和 artifact 完整 |

## 4. 回归与证据要求

- Python 静态与单元测试保留实际 pytest 汇总和覆盖率摘要；失败输出必须经敏感信息复核。
- 前端配置单元测试、typecheck、build/Playwright 由固定 Platform Bootstrap Job 归档；本需求无页面截图要求，UI 证据为 `N/A`。
- Compose 只允许执行 `docker compose config` 静态解析；AI 不直接执行 `up`、`restart`、`stop`、`down` 或镜像构建。
- 环境验收只登记 Jenkins Job/build、状态摘要和 artifact 名称，不提交原始日志、报告或 `.env`。
