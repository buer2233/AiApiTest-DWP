# front-end

`front-end` 是 AiApiTest-DWP 的 Vue 3 测试平台前端目录，后续负责登录、平台布局、模块通过率、失败用例弹窗、失败重试入口、Jenkins 任务入口和 Allure 报告入口。

当前阶段尚未开始前端实现。正式开发会在 Stage 8、Stage 9 和 Stage 10 分阶段完成。

## 目标职责

- Vue 3 + Vite + TypeScript 前端工程。
- 使用 Vue Router 管理登录页和平台页面。
- 使用 Pinia 保存 token、用户信息和平台状态。
- 使用 Axios 调用 DRF 后端 API。
- 使用 Element Plus 构建登录、表格、筛选、弹窗、菜单和操作按钮。
- 展示模块通过率、失败用例详情、失败重试操作和报告入口。

## 计划阶段

| 阶段 | 内容 |
|------|------|
| Stage 8 | Vue 3 前端基础与登录 |
| Stage 9 | 模块通过率与失败用例页面 |
| Stage 10 | 报告展示、联调、文档和交付 |

## 预期结构

```text
front-end/
├── package.json
├── vite.config.ts
├── src/
│   ├── api/
│   ├── components/
│   ├── layouts/
│   ├── router/
│   ├── stores/
│   └── views/
└── tests/
```

## 后续命令

安装依赖：

```powershell
npm install
```

运行测试：

```powershell
npm test
```

启动开发服务：

```powershell
npm run dev
```

## UI 原则

- 默认进入可操作测试平台，不做营销落地页。
- 页面围绕模块通过率、失败用例、重试入口、Jenkins 任务和报告入口设计。
- 保持平台字段通用，不引入具体公司业务模块常量。
- 使用 Element Plus 组件承载表单、表格、弹窗、菜单、分页、按钮和消息提示。
