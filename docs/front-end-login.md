# Stage 8: Vue 3 前端基础与登录

## 范围

Stage 8 建立 `front-end/` 的 Vue 3 基础工程、登录态、路由守卫和平台基础布局。

本阶段包含：

- Vue 3 + Vite + TypeScript 工程。
- Vue Router 路由与未登录访问保护。
- Pinia 保存 DRF Token 和用户信息。
- Axios 封装后端认证 API。
- Element Plus 登录页和平台基础布局。
- 使用 `npx getdesign@latest add claude` 安装 `DESIGN.md`，并按 Claude 风格落地暖陶土色、奶油画布、深色产品面板和简洁编辑式排版。

本阶段不包含：

- 模块通过率真实表格数据。
- 失败用例弹窗和重试交互。
- Allure 报告打开联调。
- 真实后端账号或真实 token。

## 文件

- `front-end/package.json`
- `front-end/package-lock.json`
- `front-end/vite.config.ts`
- `front-end/tsconfig.json`
- `front-end/index.html`
- `front-end/DESIGN.md`
- `front-end/src/main.ts`
- `front-end/src/App.vue`
- `front-end/src/router/index.ts`
- `front-end/src/stores/auth.ts`
- `front-end/src/api/http.ts`
- `front-end/src/api/auth.ts`
- `front-end/src/views/LoginView.vue`
- `front-end/src/layouts/AppLayout.vue`
- `front-end/src/styles/main.css`
- `front-end/tests/auth.spec.ts`
- `front-end/tests/setup.ts`

## 登录流程

后端登录接口沿用 Stage 5 契约：

```http
POST /api/auth/login/
```

请求体：

```json
{
  "username": "local-user",
  "password": "local-password"
}
```

响应体：

```json
{
  "token": "<drf-token>",
  "user": {
    "id": 1,
    "username": "local-user",
    "role": "admin"
  }
}
```

前端保存：

- `localStorage["auth.token"]`
- `localStorage["auth.user"]`

请求拦截器会在后续 API 请求中加入：

```http
Authorization: Token <drf-token>
```

## 路由

| 路径 | 行为 |
|------|------|
| `/` | 重定向到 `/platform` |
| `/login` | 登录页；已登录时重定向到 `/platform` |
| `/platform` | 平台基础布局；未登录时重定向到 `/login?redirect=/platform` |

`admin` 和 `member` 当前都允许进入平台壳，后续角色差异保留给更细粒度页面能力。

## 开发代理

Vite 开发服务会把 `/api` 代理到本机 DRF 后端：

```text
/api -> http://127.0.0.1:8000
```

因此浏览器中登录请求使用：

```text
POST http://127.0.0.1:5173/api/auth/login/
```

该请求会被 Vite 转发到：

```text
POST http://127.0.0.1:8000/api/auth/login/
```

本地调试时需要同时保证：

- DRF 后端运行在 `127.0.0.1:8000`。
- Vue/Vite 前端运行在 `127.0.0.1:5173`。
- 本地测试管理员密码使用 `server_acount.md` 中记录的 DRF 账号密码。

## 设计

本阶段按用户要求参考 `https://getdesign.md/claude/design-md`，执行：

```powershell
cd front-end
npx getdesign@latest add claude
```

实际采用的设计要点：

- 奶油色画布：`#faf9f5`
- 暖陶土主色：`#cc785c`
- 深色产品面板：`#181715`
- 小圆角按钮和输入框。
- 顶部导航、左侧菜单、筛选条和平台内容区结构，为 Stage 9 的表格和失败弹窗留出位置。

## TDD 记录

RED：

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm test -- auth.spec.ts
```

结果：

```text
1 failed
Failed to resolve import "@/api/auth"
```

失败原因符合预期：测试先引用尚未实现的认证 API、路由、Pinia store 和布局组件。

GREEN：

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm test -- auth.spec.ts
```

结果：

```text
1 passed, 4 tests passed
```

回归：

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm test
```

结果：

```text
1 passed, 4 tests passed
```

构建：

```powershell
cd D:\AI\Hermes\dev\AiApiTest-DWP\front-end
npm run build
```

结果：

```text
vue-tsc --noEmit && vite build
built successfully
```

生产依赖审计：

```powershell
npm audit --omit=dev
```

结果：

```text
found 0 vulnerabilities
```

## 浏览器检查

开发服务器：

```powershell
cd front-end
npm run dev -- --port 5173
```

检查结果：

- 访问 `/platform` 时未登录会跳转到 `/login?redirect=/platform`。
- 注入本地测试 token 后可进入 `/platform`。
- 桌面窄宽度下修复了 Stage 8 卡片标题被指标网格挤压的问题。
- 移动宽度下登录页无文本重叠，表单可向下滚动访问。

## 已知问题

- `npm install` 对完整依赖树报告 5 个开发依赖漏洞；生产依赖审计为 0 漏洞。本阶段不使用 `npm audit fix --force`，避免引入破坏性升级。
- `vite build` 有第三方 `@vueuse/core` 注释警告和 Element Plus 首包体积大于 500 kB 的提示；Stage 9/10 可在页面增多后再做按需组件和 chunk 拆分。
- 2026-06-23 运行时发现 Vite 初始配置缺少 `/api` 代理，导致 `http://127.0.0.1:5173/api/auth/login/` 返回 404；已补充代理测试和配置。修复后 `admin/admin` 返回 400 是密码错误，`admin/admin123456` 可登录成功。
