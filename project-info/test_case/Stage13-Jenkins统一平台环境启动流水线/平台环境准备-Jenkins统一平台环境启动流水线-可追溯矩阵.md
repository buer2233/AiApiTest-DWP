# 平台环境准备-Jenkins统一平台环境启动流水线-可追溯矩阵（RTM）

- UI 映射来源：`../../UI/Stage13-Jenkins统一平台环境启动流水线/平台环境准备-Jenkins统一平台环境启动流水线-UI区域语义拆解与实现范围映射.md`。
- 校准结论：正常、异常、边界、权限和安全场景均已对齐 R1-R6；R1-R4 为外部系统页面，R5 不实现，R6 为设计标注层，均不新增 Vue DOM。

## 追溯矩阵

| AC 编号 | 需求功能 | 测试用例编号 | UI 元素 / 页面 | API / Pipeline 契约 | 实现位置 | 验收状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `AC-S13-1.1` | F1 | `TC-S13-F1-001` | R2/R3 | Preflight / `CONFIG_ENV_MISSING` | 待实现 | 待测 |
| `AC-S13-1.2` | F1 | `TC-S13-F1-002` | R2/R3/R6 | Preflight 四类 Docker 故障：稳定、非空、彼此可区分的结构化 code | 待实现 | 待测 |
| `AC-S13-1.3` | F1 | `TC-S13-F1-003` | R1/R6 | Jenkins 只读检查 | 待实现 | 待测 |
| `AC-S13-1.4` | F1 | `TC-S13-F1-004` | R2/R3 | `BOOTSTRAP_MYSQL_NOT_RUNNING` | 待实现 | 待测 |
| `AC-S13-1.5` | F1 | `TC-S13-F1-005` | R2/R3 | `BOOTSTRAP_MYSQL_UNHEALTHY` | 待实现 | 待测 |
| `AC-S13-1.6` | F1 | `TC-S13-F1-006` | R2/R6 | `DOCKER_SOCKET_PERMISSION_DENIED` | 待实现 | 待测 |
| `AC-S13-2.1` | F2 | `TC-S13-F2-001` | R2/R3 | `SATISFIED` / `REUSED` | 待实现 | 待测 |
| `AC-S13-2.2` | F2 | `TC-S13-F2-002` | R2/R3 | `INSTALL_SUCCESS` | 待实现 | 待测 |
| `AC-S13-2.3` | F2 | `TC-S13-F2-003` | R2/R3 | `INSTALL_FAILED` 聚合 | 待实现 | 待测 |
| `AC-S13-2.4` | F2 | `TC-S13-F2-004` | R2/R6 | 依赖失败部署前终止 | 待实现 | 待测 |
| `AC-S13-2.5` | F2 | `TC-S13-F2-005` | R1/R2 | `build_all=true` 缓存构建 | 待实现 | 待测 |
| `AC-S13-2.6` | F2 | `TC-S13-F2-006` | R2/R3 | build-input hash / `BUILD_SUCCESS` | 待实现 | 待测 |
| `AC-S13-2.7` | F2 | `TC-S13-F2-007` | R6 | 业务 Job api-runner 唯一入口 | 待实现 | 待测 |
| `AC-S13-2.8` | F2 | `TC-S13-F2-008` | R2/R3 | `API_RUNNER_IMAGE_NOT_READY` | 待实现 | 待测 |
| `AC-S13-2.9` | F2 | `TC-S13-F2-009` | R6 | runner 镜像内源码 | 待实现 | 待测 |
| `AC-S13-3.1` | F3 | `TC-S13-F3-001` | R1/R2/R3 | `build_all=true` | 待实现 | 待测 |
| `AC-S13-3.2` | F3 | `TC-S13-F3-002` | R1/R2/R3 | `build_all=false` 无变化 | 待实现 | 待测 |
| `AC-S13-3.3` | F3 | `TC-S13-F3-003` | R2/R3 | 增量恢复缺失服务 | 待实现 | 待测 |
| `AC-S13-3.4` | F3 | `TC-S13-F3-004` | R2/R3 | `DEPLOY_SERVICE_FAILED` | 待实现 | 待测 |
| `AC-S13-3.5` | F3 | `TC-S13-F3-005` | R6 | volume/bootstrap 禁止项 | 待实现 | 待测 |
| `AC-S13-3.6` | F3 | `TC-S13-F3-006` | R6 | Compose `name: aiapitest-dwp` | 待实现 | 待测 |
| `AC-S13-4.1` | F4 | `TC-S13-F4-001` | R2/R3 | GET `/api/v1/health/live/` | 待实现 | 待测 |
| `AC-S13-4.2` | F4 | `TC-S13-F4-002` | R2/R3 | GET `/api/v1/health/ready/` 200 | 待实现 | 待测 |
| `AC-S13-4.3` | F4 | `TC-S13-F4-003` | R5/R6 | Nginx 配置声明的健康入口与 `/api` proxy | 待实现 | 待测 |
| `AC-S13-4.4` | F4 | `TC-S13-F4-004` | R2/R3 | worker heartbeat / `HEALTH_WORKER_STALE` | 待实现 | 待测 |
| `AC-S13-4.5` | F4 | `TC-S13-F4-005` | R1/R2 | `run_full_tests=false` | 待实现 | 待测 |
| `AC-S13-4.6` | F4 | `TC-S13-F4-006` | R1/R2/R4 | `run_full_tests=true` 平台全量 | 待实现 | 待测 |
| `AC-S13-4.7` | F4 | `TC-S13-F4-007` | R2/R3/R4 | 失败保留服务与证据 | 待实现 | 待测 |
| `AC-S13-4.8` | F4 | `TC-S13-F4-008` | R2/R3 | ready 503 安全 reason code | 待实现 | 待测 |
| `AC-S13-4.9` | F4 | `TC-S13-F4-009` | R6 | backend/frontend-test/api-runner 载体 | 待实现 | 待测 |
| `AC-S13-5.1` | F5 | `TC-S13-F5-001` | R3/R4 | 成功 Build Summary | 待实现 | 待测 |
| `AC-S13-5.2` | F5 | `TC-S13-F5-002` | R2/R3 | 失败诊断块与 rerun | 待实现 | 待测 |
| `AC-S13-5.3` | F5 | `TC-S13-F5-003` | R2/R3 | 多依赖域摘要 | 待实现 | 待测 |
| `AC-S13-5.4` | F5 | `TC-S13-F5-004` | R4 | Jenkins Allure 插件/归档 | 待实现 | 待测 |
| `AC-S13-5.5` | F5 | `TC-S13-F5-005` | R2/R3/R4 | 日志与 artifact 脱敏 | 待实现 | 待测 |
| `AC-S13-5.6` | F5 | `TC-S13-F5-006` | R4/R6 | runner `docker cp` 标准产物 | 待实现 | 待测 |
| `AC-S13-5.7` | F5 | `TC-S13-F5-007` | R2/R3/R6 | `RUNNER_ARTIFACT_EXPORT_FAILED` | 待实现 | 待测 |
| `AC-S13-6.1` | F6 | `TC-S13-F6-001` | R1/R2/R3 | helper 触发/queue/build 轮询 | 待实现 | 待测 |
| `AC-S13-6.2` | F6 | `TC-S13-F6-002` | R2/R3 | helper auth/job/timeout 错误 | 待实现 | 待测 |
| `AC-S13-6.3` | F6 | `TC-S13-F6-003` | R2/R3/R6 | AI 解释结构化失败 | 待实现 | 待测 |
| `AC-S13-6.4` | F6 | `TC-S13-F6-004` | R5/R6 | AGENTS/静态唯一入口门禁 | 待实现 | 待测 |
| `AC-S13-6.5` | F6 | `TC-S13-F6-005` | R1/R2/R3 | 手工与 helper 同契约 | 待实现 | 待测 |

## 漂移检查清单

- [x] 无遗漏需求：42 条 AC 均有主测试用例。
- [x] 无凭空用例：42 条主用例、14 条扩展用例和 6 条组合用例共 62 条，均以完整 `TC-S13-*` 编号在下表映射 AC/状态机。
- [x] 无遗漏界面：已引用 Stage13 UI 映射并校准正常、异常、边界、权限、安全场景；R1-R4 为外部页面，R5 不实现，R6 为设计标注层，均不新增 Vue DOM。
- [x] 无契约漂移：健康 API、Jenkins 参数、已冻结错误码、runner 产物协议均引用冻结需求；未冻结故障只断言可区分语义、结构、脱敏和状态边界，不新增公共枚举。
- [ ] 无未实现需求：实现位置待 Task 1-5 完成后补齐。
- [ ] 无孤儿代码：实现后扫描。
- [ ] 全部达成：真实验收后更新。

## 漂移处置记录

| 发现的漂移 | 类型 | 处置 | 状态 |
| --- | --- | --- | --- |
| RTM 使用 `ERR-002/003/007`、`ST-007` 缩写，机器核验漏计 4 条 TC | 测试追溯漂移 | 全部改为完整稳定编号并执行 62/62 双向差集检查 | 已关闭 |
| 扩展用例写死 9 个冻结需求未定义的 reason/错误码字符串 | 契约漂移 | 保持需求不变，改为断言可区分语义、诊断结构、脱敏、非零退出、一次构建和禁止并发 | 已关闭 |
| 功能测试、RTM 与验收包的 UI 校准状态和引用入口不一致 | UI 覆盖漂移 | 三份测试资料显式引用 Stage13 UI 映射并记录正常/异常/边界/权限/安全及 R1-R6 DOM 边界 | 已关闭 |
| `TC-S13-F1-002` 写死四个冻结需求未命名的 Docker 预检错误码 | 契约漂移 | 保持需求不变，改为断言四类结构化 code 稳定、非空、彼此可区分，并保留退出码/证据/建议/不部署边界 | 已关闭 |

## 扩展与状态组合用例映射

| 测试用例 | 关联 AC / 状态机 |
| --- | --- |
| `TC-S13-ERR-001`,`TC-S13-ERR-002`,`TC-S13-ERR-003` | `AC-S13-2.3` |
| `TC-S13-BND-001` | `AC-S13-2.1`,`AC-S13-2.2` |
| `TC-S13-SEC-001` | `AC-S13-1.6`,`AC-S13-6.4` |
| `TC-S13-ERR-004` | `AC-S13-4.3`,`AC-S13-4.7` |
| `TC-S13-BND-002` | `AC-S13-4.7` |
| `TC-S13-ERR-005` | `AC-S13-5.1`,`AC-S13-5.2` |
| `TC-S13-BND-003` | `AC-S13-5.1` |
| `TC-S13-ERR-006`,`TC-S13-ERR-007`,`TC-S13-ST-007` | `AC-S13-6.2` |
| `TC-S13-CONC-001` | `AC-S13-6.2`,`AC-S13-6.5` |
| `TC-S13-ERR-008` | `AC-S13-5.6`,`AC-S13-5.7` |
| `TC-S13-ST-001` | §5 `queued -> preflight -> dependency_check -> deploy -> health_check -> tests -> success`；覆盖 F1-F5 主 AC |
| `TC-S13-ST-002` | §5 `preflight -> failed`；`AC-S13-1.1~1.6` |
| `TC-S13-ST-003` | §5 `dependency_check -> failed`；`AC-S13-2.3`,`2.4` |
| `TC-S13-ST-004` | §5 `deploy/health/tests -> failed`；`AC-S13-3.4`,`4.7`,`5.2` |
| `TC-S13-ST-005` | runner 测试失败但导出成功；`AC-S13-5.6` |
| `TC-S13-ST-006` | runner 导出失败保留；`AC-S13-5.7` |
