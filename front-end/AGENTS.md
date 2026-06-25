# front-end/AGENTS.md

本目录是 Vue 3 前端。进入 `front-end/` 开发前，必须先遵守根目录 `AGENTS.md`，再遵守本文件。

## 前端开发-技能推荐

必须执行的技能： /vue-best-practices ， /frontend-design

进行前端开发时，推荐使用下面的SKILL：
- ui-ux-pro-max：前端和UI设计时使用
- vue-pinia-best-practices
- vue-router-best-practices
- vue-testing-best-practices
- vue-debug-guides
- ckm:design-system：令牌体系结构设计

## 模块职责

- 登录页、登录态和用户信息展示。
- 平台基础布局、顶部导航和左侧菜单。
- 模块通过率列表。
- 失败用例弹窗、筛选、选择和重试操作。
- Jenkins 任务入口和 Allure 报告入口。

## 技术约定

- 使用 Vue 3、Vite、TypeScript。
- 使用 Vue Router 管理路由。
- 使用 Pinia 管理状态。
- 使用 Axios 封装后端 API 请求。
- 使用 Element Plus 作为组件库。
- 测试使用 Vitest 和 Vue Test Utils。

## 设计约定

- 不做营销页，首屏是可操作测试平台。
- 参考现有测试平台截图的表格、筛选、弹窗和操作入口，但不照搬公司业务字段。
- 操作入口要围绕失败重试、模块重试、Jenkins 任务和 Allure 报告。
- 普通用户和管理员第一版权限可一致，但前端结构要预留后续管理员专属入口。

## TDD 要求

- Stage 8 先写登录和路由守卫测试，再实现基础工程与登录。
- Stage 9 先写模块列表和失败用例弹窗测试，再实现页面。
- Stage 10 先写报告入口相关测试，再做联调。

## 禁止事项

- 不提交真实后端地址、token、账号、密码。
- 不把具体公司业务模块常量写死到页面。
- 不绕过后端权限或直接读取服务器文件路径。
