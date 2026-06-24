# Stage 9: 模块通过率与失败用例页面

## 范围

Stage 9 在 Vue 3 前端中实现模块通过率页面和失败用例弹窗，接入 Stage 6 后端测试任务 API，并保留 Stage 7 Jenkins 入口和 Stage 10 Allure 静态报告入口。

本阶段实现：

- 模块通过率页面：模块数、失败模块、平均通过率、筛选区、模块/用例包/Jenkins 页签、模块运行表格。
- 模块表格字段：日期、用例包名、模块名、负责人、自动化负责人、通过率、运行时间、操作。
- 操作入口：失败重试、模块重试、Jenkins 任务、Allure 报告。
- 失败用例弹窗：用例名/描述筛选、错误类型筛选、执行状态筛选、失败用例列表、选择失败用例、失败重试、一键失败重试、Allure 报告。
- 前端 API 封装：`GET /api/test-runs/`、`GET /api/test-runs/{id}/failures/`、`POST /api/test-runs/{id}/retry-selected/`、`POST /api/test-runs/{id}/retry-all-failed/`、`POST /api/test-runs/{id}/retry-module/`、`GET /api/test-runs/{id}/report/`。

本阶段不实现：

- Allure HTML 静态服务本身，留到 Stage 10。
- Jenkins 构建详情页面，当前只保留入口。
- 多项目、多租户、环境对比、测试账号替换、作废等参考截图中的扩展能力。

## 设计说明

页面继续遵守 `front-end/DESIGN.md` 的 Claude 风格：

- 奶油画布 `#faf9f5` 作为页面背景。
- 陶土色 `#cc785c` 作为主操作色。
- 深色产品面板 `#181715` 用于模块页头部，形成操作台焦点。
- 筛选、指标、表格和弹窗使用 8px 左右圆角、细边框和紧凑信息密度。
- 移动端将筛选项和操作按钮换行，表格保留横向滚动，避免字段压缩到不可读。

视觉原则记录见 `docs/stage9-visual-philosophy.md`。

## TDD 记录

RED：

```powershell
cd front-end
npm test -- module-pass-rate.spec.ts
npm test -- failure-cases-dialog.spec.ts
```

初始失败原因：

- `@/api/testRuns` 缺失，模块通过率和失败用例弹窗尚无实现。
- 实现后首次测试发现 Element Plus 表格/选择器在 jsdom 中会触发递归更新，改为测试专用轻量 stub，业务代码仍使用真实 Element Plus。

GREEN：

```powershell
cd front-end
npm test -- module-pass-rate.spec.ts
npm test -- failure-cases-dialog.spec.ts
npm test
npm run build
```

结果：

- `module-pass-rate.spec.ts`：3 passed。
- `failure-cases-dialog.spec.ts`：4 passed。
- 前端全量测试：4 files passed，12 tests passed。
- `npm run build` 成功；仍有 Vite/Rollup 对 `@vueuse/core` 注释和大 chunk 的既有 warning。

## 浏览器检查

使用当前 Vite 服务 `http://127.0.0.1:5173/platform`，通过 Playwright 注入本地登录态并 mock Stage 9 API 响应：

- 未登录访问 `/platform` 会跳转 `/login?redirect=/platform`。
- 注入 token 后模块通过率页可展示测试数据。
- 点击失败模块的失败重试可打开失败用例弹窗。
- 桌面端弹窗、筛选条、表格和操作按钮可见。
- 移动端筛选项和按钮可换行；表格保持横向滚动，无文本互相覆盖。
- 控制台未发现 warning/error。

## 已知问题

- `TestRunSerializer` 当前没有后端原生 `module_name`、`owner`、`automation_owner`、`pass_rate`、`duration_seconds` 字段；前端已按 `case_path` 和 `summary` 做回退。后续如需要更完整展示，可在后端 serializer 补充计算字段。
- Stage 9 的 Jenkins 任务入口当前打开占位 URL `/jenkins/builds?run_id=<run_id>`，真实 Jenkins 构建详情页留给后续联调阶段。
- Stage 10 仍需完成 Allure 静态 HTML 可访问路径的后端服务与前端报告入口联调。
