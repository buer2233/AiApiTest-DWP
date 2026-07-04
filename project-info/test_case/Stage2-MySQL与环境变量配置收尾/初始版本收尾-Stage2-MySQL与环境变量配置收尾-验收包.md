# 初始版本收尾-Stage2-MySQL与环境变量配置收尾-验收包

## 验收结论

| 项 | 结论 |
| --- | --- |
| 需求状态 | 已实现并完成回归，等待主人最终验收 |
| 需求分级 | M |
| SQLite 处理 | `back-end/db.sqlite3` 已保留，等待主人确认 MySQL 功能无误后再决定是否删除 |
| MySQL 状态 | Docker MySQL 运行中，Django 已连接 MySQL，迁移检查通过 |
| `api-test` 范围 | 按主人裁决，本轮未修改 `api-test` 代码和执行协议 |
| 真实 `.env` | 未提交；仅提交脱敏 `.env.example` |

## 交付文件

| 类型 | 路径 |
| --- | --- |
| 需求说明 | `project-info/demand/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-需求说明.md` |
| 功能测试用例 | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-功能测试用例.md` |
| 可追溯矩阵 | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-可追溯矩阵.md` |
| 验收包 | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-验收包.md` |
| 环境模板 | `.env.example` |

## 验证证据

| 验证项 | 结果 | 证据文件 |
| --- | --- | --- |
| 后端 pytest + 覆盖率 | `40 passed`，TOTAL `92%` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-后端pytest证据-20260704.txt` |
| Django system check | `System check identified no issues` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-后端manage-check证据-20260704.txt` |
| 初始化管理员 | `初始化管理人员已存在。`，命令幂等且不输出密码 | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-init_admin证据-20260704.txt` |
| MySQL 迁移检查 | `migrate_check=ok` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-MySQL迁移检查证据-20260704.txt` |
| MySQL 数据计数 | `database_vendor=mysql`，`user_account=2`，`invitation_code=2` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-MySQL数据计数证据-20260704.txt` |
| Docker 容器状态 | `aiapitest-mysql`、`aiapitest-jenkins` 均为 `Up` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-Docker容器状态证据-20260704.txt` |
| 前端 typecheck | 通过 | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-前端typecheck证据-20260704.txt` |
| 前端 unit | `2 files / 5 tests passed` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-前端unit证据-20260704.txt` |
| 前端 build | 构建成功；存在 Vite chunk size 体积提示，不阻断本需求 | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-前端build证据-20260704.txt` |
| Playwright E2E | `18 passed` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-前端playwright证据-20260704.txt` |
| Jenkins 静态测试 | `16 passed` | `project-info/test_case/Stage2-MySQL与环境变量配置收尾/初始版本收尾-Stage2-MySQL与环境变量配置收尾-Jenkins静态测试证据-20260704.txt` |

## AC 验收映射

| AC | 状态 | 证据 |
| --- | --- | --- |
| AC1.1 | 通过 | 后端配置测试、后端 pytest |
| AC1.2 | 通过 | MySQL 迁移检查、MySQL 数据计数、Docker 容器状态 |
| AC1.3 | 通过 | `init_admin` 证据、MySQL 数据计数 |
| AC1.4 | 通过 | 后端 pytest + 测试 settings |
| AC2.1 | 通过 | 前端 unit、typecheck |
| AC2.2 | 通过 | 前端 unit、Vite 配置 |
| AC2.3 | 通过 | 前端 unit、Playwright E2E |
| AC2.4 | 通过 | 前端 unit、build |
| AC3.1 | 通过 | `.env.example`、部署/快速启动文档、Jenkins/Docker 静态测试 |
| AC3.2 | 通过 | Jenkins/Docker 静态测试 |
| AC3.3 | 通过 | 根 `AGENTS.md`、`project-info/AGENTS.md` |
| AC3.4 | 通过 | Docker 部署文档、快速启动文档、脚本静态测试 |

## 留待主人验收确认

- MySQL 功能确认无误后，再由主人决定是否删除 `back-end/db.sqlite3`。
- 当前 Docker 容器是既有 `aiapitest-mysql` / `aiapitest-jenkins` 容器，不删除容器或 volume。
- 前端构建存在大 chunk 提示，属于后续性能优化项，不影响本次 MySQL 与环境变量收尾验收。
