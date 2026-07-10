# 环境与模块通过率页面-Jenkins依赖复用与趋势图修复-验收包

## 1. 冻结输入

- 需求：`../../demand/Stage11-Jenkins依赖复用与趋势图修复/环境与模块通过率页面-Jenkins依赖复用与趋势图修复-需求说明.md`
- 测试：`./环境与模块通过率页面-Jenkins依赖复用与趋势图修复-功能测试用例.md`
- UI 映射：`../../UI/Stage11-Jenkins依赖复用与趋势图修复/环境与模块通过率页面-Jenkins依赖复用与趋势图修复-UI区域语义拆解与实现范围映射.md`

## 2. 实现与验证

- Jenkins/Docker：工具镜像预装 `api-test/requirements.txt` 并设置预装标志；仅该 Linux 镜像 venv 使用 `--system-site-packages`，其它 agent 保持隔离；静态测试 50 passed。
- 后端 pytest：168 passed，覆盖率 90%；新增每日去重、模块重试优先、完成时间相同/为空时按 id 兜底和本地时区跨日窗口测试。
- 前端 Vitest/构建：8 files / 18 tests passed；`vue-tsc` 和 Vite 生产构建通过。
- api-test：执行器与工具层契约 62 passed。业务用例目录内两条故意失败样例不作为工具层回归失败；个人 `.idea/workspace.xml` 检查不属于本需求交付。
- 真实 Jenkins console：`AiApiTest-DWP-Module-Rerun #27` 使用镜像 `sha256:e482cf...` 执行，输出 `All requirements already satisfied; skip pip install.`，未输出缺失依赖安装或 `Successfully installed`；pytest 逐用例过程正常打印。
- 真实趋势接口：7 天返回 5 条且 5 个日期唯一；30 天返回 28 条且 28 个日期唯一；7 天最后一条为 `2026-07-10/module_rerun/90.00%`。
- Playwright：Stage11 真实 E2E 1 passed（约 1.1 分钟）；受影响模块页/趋势/Jenkins 回归 23 passed；逐点 accessibility role、390px 标签高度和不重叠均有真实浏览器断言。
- 独立对抗审查：首轮发现 3 项 Important（agent 依赖污染、时区跨日、SVG 子节点无障碍树）和 2 项相关 Minor；修复后复核确认全部闭环，最终无 Critical/Important。

### 2.1 Playwright 截图

- `./环境与模块通过率页面-Jenkins依赖复用与趋势图修复-Playwright验收-桌面.png`
- `./环境与模块通过率页面-Jenkins依赖复用与趋势图修复-Playwright验收-移动端.png`

### 2.2 已知非阻塞信息

- 前端构建保留既有 Rollup PURE 注释和 chunk size warning，不影响构建产物。
- 本机启动前发现 PyMySQL 1.0.2 低于仓库 `>=1.1` 要求，已升级到 1.2.0 后使用真实 MySQL 启动；代码和配置无需新增兼容分支。
- 30 天窗口内原始历史量极大时，接口仍会先加载窗口记录再在 Python 中按日优选；当前数据量和同模块互斥策略下可接受，后续可按实际容量指标评估数据库窗口函数优化。
- Windows/非工具 Linux agent 的隔离 venv 分支已有静态契约测试，本轮没有真实 Windows agent 执行证据。

## 3. 容器化检查

- Dockerfile 只复制仓库相对路径 `api-test/requirements.txt`，未引入本机绝对路径或凭据。
- 带预装标志的 Linux Jenkins executor 从镜像只读继承依赖，requirements 变化时仍在 executor venv 补差异。
- 非工具 Linux/Windows agent 使用隔离 venv 并执行同一缺失检测协议，不继承未知全局包。
- `docker compose ... config --quiet` 通过；Jenkins 重建后 40 executors、busy=0、queue=0，预装标志值为 1。

## 4. 主人终审

- 状态：自动化、真实环境和独立审查均已通过，提交推送后交主人终审。
