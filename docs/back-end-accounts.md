# DRF 后端基础工程与用户角色 - Stage 5 文档

## 概述

Stage 5 实现了 Django REST Framework 后端基础工程，包括用户认证、角色管理和 API 接口。

## 文件结构

```
back-end/
├── manage.py                          # Django 管理脚本
├── requirements.txt                   # Python 依赖
├── pytest.ini                         # pytest 配置
├── config/
│   ├── __init__.py
│   ├── settings.py                    # Django 设置
│   ├── urls.py                        # URL 路由
│   ├── wsgi.py                        # WSGI 入口
│   └── asgi.py                        # ASGI 入口
├── apps/
│   ├── __init__.py
│   └── accounts/
│       ├── __init__.py
│       ├── apps.py                    # App 配置
│       ├── models.py                  # 用户模型
│       ├── serializers.py             # 序列化器
│       ├── views.py                   # API 视图
│       ├── urls.py                    # URL 路由
│       ├── permissions.py             # 权限类
│       └── migrations/                # 数据库迁移
└── tests/
    ├── test_accounts_api.py           # 账户 API 测试
    └── test_database_settings.py      # 数据库配置测试
```

## 用户模型

### User 模型
- 继承自 `AbstractUser`
- 新增 `role` 字段，支持 `admin` 和 `member` 两种角色
- 默认角色为 `member`

### UserManager
- 自定义 `create_superuser` 方法
- 创建超级用户时自动设置 `role=admin`

## API 接口

### 1. 用户登录
```
POST /api/auth/login/
```

**请求体：**
```json
{
    "username": "string",
    "password": "string"
}
```

**响应：**
```json
{
    "token": "string",
    "user": {
        "id": 1,
        "username": "string",
        "role": "admin|member"
    }
}
```

### 2. 用户登出
```
POST /api/auth/logout/
```

**请求头：**
```
Authorization: Token <token>
```

**响应：** 204 No Content

### 3. 获取当前用户
```
GET /api/auth/me/
```

**请求头：**
```
Authorization: Token <token>
```

**响应：**
```json
{
    "id": 1,
    "username": "string",
    "role": "admin|member"
}
```

## 权限类

### PlatformAccessPermission
- 平台 API 访问权限
- `admin` 和 `member` 角色都可以访问
- 当前阶段两个角色权限一致

### IsPlatformAdmin
- 管理员权限
- 只有 `admin` 角色可以访问
- 预留后续管理员独有功能

## 数据库配置

### 所有环境
- 强制使用本地 MySQL，不再按 pytest 环境回退 SQLite。
- 连接地址固定为 `localhost:3306`。
- 通过环境变量配置：
  - `MYSQL_DATABASE` - 数据库名（默认：`ai_api_test_platform`）
  - `MYSQL_USER` - 用户名（默认：`root`）
- `MYSQL_PASSWORD` - 密码
- `MYSQL_PORT` - 本地 MySQL 端口，默认 `3307`，用于对齐 Docker Compose 的 `MYSQL_HOST_PORT`。

## 认证配置

- 使用 DRF Token 认证
- 默认需要认证
- 登录接口不需要认证

## CORS 配置

允许的前端源：
- `http://localhost:5173`
- `http://127.0.0.1:5173`

可通过环境变量 `CORS_ALLOWED_ORIGINS` 配置。

## 安装依赖

```bash
cd back-end
pip install -r requirements.txt
```

## 运行测试

```bash
cd back-end
python -m pytest tests/test_database_settings.py -v
python -m pytest tests/test_accounts_api.py -v
```

## 测试结果

```
tests/test_database_settings.py::test_database_connection_is_forced_to_local_mysql PASSED
tests/test_accounts_api.py::test_user_can_login_receive_token_read_current_user_and_logout PASSED
tests/test_accounts_api.py::test_admin_and_member_roles_can_be_saved PASSED
tests/test_accounts_api.py::test_create_superuser_defaults_to_admin_role PASSED
tests/test_accounts_api.py::test_admin_and_member_can_access_platform_api_with_same_permissions[admin] PASSED
tests/test_accounts_api.py::test_admin_and_member_can_access_platform_api_with_same_permissions[member] PASSED
tests/test_accounts_api.py::test_permissions_keep_admin_only_entrypoint PASSED

7 passed across database settings and accounts tests
```

## 数据库迁移

### 创建迁移
```bash
cd back-end
python manage.py makemigrations accounts
```

### 应用迁移
```bash
python manage.py migrate
```

### 检查迁移
```bash
python manage.py makemigrations --check --dry-run
```

## 验收标准

- [x] 用户可登录并获得 token
- [x] admin 和 member 两种角色可保存
- [x] 当前两个角色访问平台 API 权限一致
- [x] 权限类中保留管理员独有权限判断入口
- [x] 账户测试通过
- [x] 可创建管理员和普通用户
- [x] 使用 DRF Token 认证
- [x] 强制使用本地 MySQL `localhost:3306`

## 后续步骤

Stage 5 完成后，下一步是 **Stage 6: 测试任务与失败用例 API**。
