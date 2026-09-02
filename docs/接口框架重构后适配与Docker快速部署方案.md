# 接口框架重构后适配与 Docker 快速部署方案

## 现状与根因

`package_environment.yaml`、`package_module.yaml` 是接口自动化测试的配置事实源；MySQL 只保存平台投影和执行结果。历史实现只在空库首次初始化环境，模块同步也没有纳入 Platform Bootstrap，因此持久化卷会继续展示旧环境、旧模块和旧用例。

## 已落地的快速适配链路

固定 `AiApiTest-DWP-Platform-Bootstrap` 的 `Schema & Initial Data` 阶段按以下顺序执行：

1. `migrate --noinput`
2. `seed_environment --reconcile`：读取镜像内 `api-test/utils/package_environment.yaml`，更新/创建当前环境，停用 YAML 中已删除的历史环境。
3. `sync_modules --reconcile`：读取镜像内 `api-test/utils/package_module.yaml`，更新模块元数据和 `case_path`，停用已删除模块，并为启用环境创建缺省快照。
4. `init_admin --bootstrap-only`

模块页只查询启用模块；模块重试继续通过后端生成 Jenkins 参数 `CASE_PATH=test_case/<package_name>`，实际执行目标由 `api-test/tools/ci_runner.py` 统一解析，不在前端或后端重复实现 pytest 协议。

配置变更后的标准动作：提交两个 YAML 与代码后，触发固定 Platform Bootstrap Job（`build_all=true`）。禁止直接启动 backend/frontend 旁路替代该 Job。

## 大型接口框架重构的适配方法

- 配置层：以 YAML 的 package/env key、模块元数据和 case path 建立稳定契约，先做 schema 校验，再投影数据库。
- 执行层：Jenkins 只调用共享 `ci_runner.py`；全量、模块重试、失败重试均传递同一套参数和报告产物契约。
- 数据层：模块/环境主表允许幂等更新和逻辑停用；快照、失败用例、Jenkins 任务保持追加或可审计，不删除历史记录。
- 展示层：前端只消费 DRF API；环境和模块列表来自同步后的投影，不能写死业务常量。
- 迁移层：每次重构先增加契约测试，再执行 bootstrap 重投影，最后运行模块级真实测试和 Allure 验证。

## 新电脑部署清单

1. 安装 Docker Desktop（启用 Linux containers）与 Git，克隆仓库。
2. 复制配置模板并填写私有值：

   ```powershell
   Copy-Item .env.example .env
   # 编辑 .env，至少补齐 MYSQL_ROOT_PASSWORD、DB_USER、DB_PASSWORD、DJANGO_SECRET_KEY、AUTH_TOKEN_SECRET、INITIAL_ADMIN_*。
   ```

3. 设置 `PROJECT_WORKSPACE` 为当前仓库绝对路径；端口按本机占用情况修改。
4. 由主人或运维启动基础服务：

   ```powershell
   .\scripts\deploy-docker.ps1
   ```

5. 等待 Jenkins 页面可访问且 Init Groovy 创建固定 Job，然后触发：

   ```powershell
   .\scripts\trigger-platform-bootstrap.ps1
   ```

6. Job 成功后访问 `.env` 派生的前端地址（默认 `http://127.0.0.1:5173`）。需要完整回归时执行：

   ```powershell
   .\scripts\trigger-platform-bootstrap.ps1 -BuildAll false -RunFullTests true
   ```

不要把 `.env`、MySQL/Jenkins volume、运行报告或本机绝对路径提交 Git。换电脑时只迁移代码和私有配置；是否迁移命名 volume 由运维按数据保留策略决定。

## Jenkins 可用性验收

Jenkins 根地址必须返回登录页或经认证的 200；当前环境对 `http://127.0.0.1:8080/` 返回 `403`，因此本次不能判定 Jenkins 或 Pipeline 可用。修复凭据、反向代理或安全策略后，使用固定 Job 逐项验证：Platform Bootstrap、通用 API、模块重试、失败重试、Daily 父/Worker、环境目录同步。每项至少检查参数受理、构建进入队列、最终状态、归档 artifact 和 Allure 入口，并保留 Jenkins build URL 作为验收证据。
