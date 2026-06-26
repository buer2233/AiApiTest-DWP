# project_picture AGENTS.md

本目录用于存放项目架构图、流程图、项目说明图片、架构说明书和面向交接的可视化资料。

## 目录定位

- 只放架构图、流程图、说明图、架构说明文档和图片生成相关资料。
- 不放需求分析、UI 原型、测试用例、业务实现代码或运行时产物。
- 图片和说明必须保持通用测试平台定位，不绑定具体业务系统。

## 推荐技能

生成或更新项目说明图片时，优先使用以下技能或等价工具：

- `imagegen`：使用 Codex 图像生成能力生成 PNG 等位图图片。
- `drawio-skill`：绘制架构图和流程图时使用。

## 文件约定

- 架构图优先命名为 `project-architecture.png` 或带版本后缀的 `project-architecture-vN.png`。
- 中文架构图优先命名为 `project-architecture-cn.png` 或 `project-architecture-cn-4k.png`。
- 架构说明书优先命名为 `项目架构说明书.md` 或 `project-architecture.md`。
- 执行流程图优先命名为 `execution-flow.png` 或 `execution-flow.md`。
- 图片应尽量使用高分辨率输出；如果 4K 不稳定，允许使用 2K。

## 图片生成约定

- 需要 AI 生成位图图片时，使用当前会话可用的 `imagegen` 技能或等价图像生成工具。
- 图片内容必须覆盖真实项目技术栈和已规划架构，不虚构未纳入当前计划的核心模块。
- 若图片中包含文字，除专业名词外应使用简体中文。
- 专业名词可保留原名，例如 `api-test`、`Jenkins`、`DRF Backend`、`Vue 3 Frontend`、`Allure Report`、`Docker MySQL/Jenkins`。
- 生成后的图片必须保存到本目录，不能只停留在临时输出目录。

