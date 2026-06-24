# project-info AGENTS.md

本目录用于沉淀项目说明资料，包含项目架构图、项目架构说明书、执行流程图、交付说明图和面向接手人员的总览资料。

## 目录定位

- 只放项目说明、架构说明、流程说明、图片资产和面向协作交接的资料。
- 不放 `api-test/`、`back-end/`、`front-end/`、`jenkins/` 的业务实现代码。
- 不放 Allure 运行结果、Jenkins 构建产物、pytest runtime、数据库导出或其他运行时产物。
- 不提交真实账号、密码、token、cookie、Jenkins API Token、生产地址或不可迁移的业务常量。

## 文件约定

- 架构图优先命名为 `project-architecture.png` 或带版本后缀的 `project-architecture-vN.png`。
- 架构说明书优先命名为 `project-architecture.md`。
- 执行流程图优先命名为 `execution-flow.png` 或 `execution-flow.md`。
- Markdown 文档使用简体中文，说明应保持通用测试平台定位。
- 图片应尽量使用高分辨率输出；如果 4K 不稳定，允许使用 2K。

## 图片生成约定

- 需要 AI 生成位图图片时，使用项目当前会话可用的 imagegen 技能或等价的图像生成工具。
- 图片内容必须覆盖真实项目技术栈和已规划架构，不虚构未纳入当前计划的核心模块。
- 若图片中包含文字，文字应使用项目通用术语，如 `api-test`、`Jenkins`、`DRF Backend`、`Vue 3 Frontend`、`Allure Report`、`Docker MySQL/Jenkins`。
- 生成后的图片必须保存到本目录，不能只停留在临时输出目录。

## 协作规则

- 修改本目录前先读取根目录 `AGENTS.md` 和主计划文件。
- 若说明内容涉及某个子模块的实现细节，应优先读取对应子目录的 `AGENTS.md`。
- 本目录文档只描述架构和流程，不改变阶段开发边界。
- `CLAUDE.md` 只保留 `@AGENTS.md` 引用，具体规则维护在本文件。
