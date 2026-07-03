# Swagger接口文档补充-Stage1-Swagger接口文档补充-需求简述

## 0. 需求分级与流程裁剪

- 定级：S
- 定级原因：本次只为现有 DRF 后端补齐 Swagger/OpenAPI 文档能力和后端协作规则，不新增业务数据表，不改变现有业务接口语义，不新增前端页面。
- 裁剪阶段：裁剪 UI 原型和前端开发阶段，因为本需求只涉及后端接口文档入口和后端规则文档；保留需求澄清冻结、架构影响评估、API 契约冻结、容器化兼容检查、功能测试用例和后端 TDD。
- 阶段目录：`Stage1-Swagger接口文档补充`

## 1. 需求背景

当前快速启动文档已经把后端接口文档地址写为 `http://127.0.0.1:8000/api/docs/`，但后端尚未注册 Swagger/OpenAPI 文档端点，依赖中也没有 schema 生成组件。为后续 AI 协作、前后端联调、Jenkins 验收和接口契约冻结，需要补齐可访问、可回归测试的 Swagger 接口文档。

## 2. 需求目标

1. 后端必须提供 OpenAPI schema 端点，供机器读取当前接口契约。
2. 后端必须提供 Swagger UI 端点，供开发和验收人员浏览当前接口文档。
3. Swagger 文档必须覆盖当前用户权限底座接口，包括登录、登出、当前用户、注册、用户列表、邀请码列表/创建和邀请码作废。
4. `back-end/AGENTS.md` 必须明确要求：新增或变更接口时同步维护 Swagger 文档。

## 3. 范围

### 3.1 本次包含

- 新增 `GET /api/schema/` OpenAPI 3 schema 端点。
- 新增 `GET /api/docs/` Swagger UI 端点。
- 为当前后端 API 补充 schema 摘要、标签、请求参数、请求体、响应结构和关键错误码说明。
- 增加后端自动化测试，验证 schema/docs 端点存在且包含当前核心 API 路径。
- 更新后端 AGENTS 规则。

### 3.2 本次不做

- 不新增业务 API。
- 不调整现有业务接口路径、请求字段、响应字段或鉴权行为。
- 不新增数据表或迁移。
- 不新增前端页面。
- 不接入生产环境域名、真实凭据或外部固定地址。

## 4. 需求澄清冻结

主人已明确提出三项要求：

1. `back-end/AGENTS.md` 添加后端必须包含 Swagger 接口文档的要求。
2. 补充当前项目的 Swagger 接口文档。
3. 提交并推送远端。

本需求不存在待澄清项，按上述口径冻结。

## 5. API 契约冻结

### 5.1 文档端点

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/schema/` | 返回 OpenAPI 3 schema，默认 JSON/YAML 协商由 schema 组件处理 | 无需登录 |
| GET | `/api/docs/` | 返回 Swagger UI 页面，读取 `/api/schema/` | 无需登录 |

### 5.2 当前业务接口需进入 Swagger

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 用户登录并写入 HttpOnly Cookie |
| POST | `/api/v1/auth/logout` | 用户登出并清理 Cookie |
| GET | `/api/v1/auth/me` | 获取当前登录用户 |
| POST | `/api/v1/auth/register` | 使用邀请码注册用户 |
| GET | `/api/v1/users` | 管理人员分页查询用户 |
| GET | `/api/v1/invitations` | 管理人员分页查询邀请码 |
| POST | `/api/v1/invitations` | 管理人员创建邀请码 |
| POST | `/api/v1/invitations/{invitation_id}/revoke` | 管理人员作废未使用邀请码 |

## 6. 架构影响评估

| 模块 | 影响 |
| --- | --- |
| DRF 后端 | 有影响：新增 schema 生成依赖、settings、URL 和视图 schema 注解 |
| Vue 前端 | 无影响：不改变前端调用路径 |
| Jenkins | 无直接影响：后续可通过 pytest 验证文档端点 |
| `api-test` | 无影响：不改测试执行协议 |
| Docker | 无直接影响：新增 Python 依赖由 `requirements.txt` 管理 |
| 数据模型 | 无影响：不新增或变更数据表 |
| 权限 | 无业务权限变更：文档端点公开，业务接口权限保持现状 |
| 报告协议 | 无影响 |
| 部署方式 | 无影响：不引入本机绝对路径、固定宿主机端口或手工依赖 |

## 7. 容器化兼容检查

- 新依赖必须写入 `back-end/requirements.txt`，容器构建可重复安装。
- 文档端点使用相对 URL 名称引用 schema，不写死 `127.0.0.1`、宿主机端口或个人目录。
- 不写入真实账号、密码、token、Cookie、生产 URL 或 Jenkins 凭据。

## 8. 验收口径

- `GET /api/schema/` 返回 200，schema 中 `openapi` 字段存在，且包含当前核心 API 路径。
- `GET /api/docs/` 返回 200，并包含 Swagger UI 页面内容。
- 后端测试通过并保存 pytest/coverage 运行证据。
- `back-end/AGENTS.md` 明确要求后端接口必须同步维护 Swagger 文档。
