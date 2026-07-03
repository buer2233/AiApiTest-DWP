# Swagger接口文档补充-Stage1-Swagger接口文档补充-功能测试用例

## 1. 测试范围

依据 `project-info/demand/Stage1-Swagger接口文档补充/Swagger接口文档补充-Stage1-Swagger接口文档补充-需求简述.md` 编写，覆盖 Swagger/OpenAPI 文档端点、当前接口路径收录、公开访问和回归安全边界。

## 2. 功能测试用例

| 用例编号 | 优先级 | 模块 | 场景 | 操作步骤 | 预期结果 |
| --- | --- | --- | --- | --- | --- |
| SWAGGER-TC-001 | P0 | OpenAPI Schema | 获取 schema | 未登录状态请求 `GET /api/schema/` | 返回 200；响应包含 `openapi`、`paths` 字段 |
| SWAGGER-TC-002 | P0 | OpenAPI Schema | 核心 API 路径收录 | 读取 `GET /api/schema/` 的 `paths` | 包含登录、登出、当前用户、注册、用户列表、邀请码列表/创建、邀请码作废路径 |
| SWAGGER-TC-003 | P0 | Swagger UI | 访问文档页面 | 未登录状态请求 `GET /api/docs/` | 返回 200；页面包含 Swagger UI 相关内容 |
| SWAGGER-TC-004 | P1 | 权限边界 | 文档端点公开但业务接口仍鉴权 | 未登录请求 `/api/schema/` 后，再未登录请求 `/api/v1/auth/me` | 文档端点 200；业务接口仍返回 401 |
| SWAGGER-TC-005 | P1 | 回归 | 现有业务接口行为不变 | 执行后端全部 pytest | 现有登录、注册、邀请码、用户列表测试继续通过 |

## 3. 异常和边界

- 文档端点不得依赖真实 Jenkins、MySQL 固定宿主机端口或本机绝对路径。
- schema 不得暴露真实密码、token、Cookie 示例值或生产地址。
- 当前业务接口错误码需保持现有格式：`{"error": {"code": "...", "message": "...", "details": []}}`。
