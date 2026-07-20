# Platform Bootstrap 自动迁移与首次初始化设计

## 状态

主人于 2026-07-20 确认设计，待书面规格复核后实施。该修订扩展已冻结的 Stage13 需求，不改变 Daily 全模块、环境目录同步或前端页面范围。

## 问题与目标

现有固定 Platform Bootstrap Job 在空 MySQL 上会部署应用，但 ready 探针因未执行 Django migration 返回 `schema_not_ready`。新机器无法由唯一的环境入口达到可用状态。

目标是让同一固定 Job 在不管理 MySQL/Jenkins 基础服务、不重置数据的前提下，自动完成 schema 与首次必要数据初始化。

## 选定设计

Pipeline 增加 `Schema & Initial Data` 阶段，顺序为：

`Checkout/Workspace -> Bootstrap Preflight -> Dependency Assurance -> Schema & Initial Data -> Deploy -> Health -> Tests -> Archive & Summary`

迁移阶段由 `jenkins/scripts/platform_bootstrap` 的可测试服务实现，Groovy 仅编排阶段。服务通过 Compose 启动一次性、自动删除、无端口、无常驻职责的 `backend-bootstrap` 容器；该容器复用 backend 镜像与数据库连接配置，但独占私有 `INITIAL_ADMIN_*` 变量，backend 和 worker 不接收管理员密码。

阶段按照固定顺序执行：

1. `python manage.py migrate --noinput`
2. `python manage.py seed_environment`
3. `python manage.py init_admin --bootstrap-only`

不增加 Jenkins 参数。`migrate --noinput` 本身会计算待执行 migration：空库创建 `django_migrations` 与所有 Django 应用表；已有库只应用未记录的版本。它不使用 `flush`、`reset`、`drop`、卷删除、自动 rollback 或历史伪造。

## 首次数据边界

- `seed_environment` 只在环境目录尚未初始化时，从镜像内 `api-test/utils/package_environment.yaml` 创建投影；已存在平台环境时成功跳过，绝不覆盖管理员通过平台维护的目录。
- `init_admin --bootstrap-only` 只在账号表为空时读取私有 `INITIAL_ADMIN_*` 创建首个 admin；已有任意账号时成功跳过，不修改密码、角色、显示名称或其他既有账号。
- 缺失或不合规的管理员变量仅在确实需要创建首个账号时使阶段失败。命令输出、结构化诊断、Summary 与 Artifact 必须经现有脱敏链路处理。

## 失败、安全与兼容性

任一子命令失败时，Job 不进入 Deploy；保留已经产生的 schema 变更，不进行自动回滚或数据清理，并归档脱敏后的阶段证据和可操作诊断。ready endpoint 保持只读，只报告 `schema_not_ready`，不能执行迁移。

固定 Job 的 `disableConcurrentBuilds()` 继续保障同一 Job 内无并发迁移。迁移阶段不能启动、停止、重建或删除 mysql/jenkins，也不能以直接 Docker、Django 或宿主机命令形成旁路。

## 验收与测试

- 空数据库：三项命令顺序正确，创建全部 schema、环境投影和唯一首个管理员。
- 已迁移数据库：migration 无待执行项时成功；环境与账号数据不被覆盖或升级。
- 存在待执行 migration：只应用待执行项，随后才允许 Deploy。
- 初始化失败：Deploy 未调用，诊断和证据不含私有密码。
- 健康检查：仍只读；基础 MySQL/Jenkins 容器 ID 不变。
- Jenkins 静态与 Pipeline 单元测试：八阶段顺序、无参数旁路、Compose 服务边界和禁止破坏性命令均被覆盖。

## 影响范围

修改范围包括 `jenkins/` Bootstrap 核心、Pipeline、静态/单元测试，根 Compose 中的一次性 bootstrap 服务，后端 `init_admin` 的 bootstrap-only 语义，以及根/模块规则、部署文档、Stage13 需求、测试用例、RTM 与验收包。无新增 DRF API、Vue 页面、数据表或 api-test 执行协议。
