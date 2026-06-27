# project-info/project_detail/AGENTS.md

本目录用于存放项目架构图、流程图、项目说明图片、架构说明书和面向交接的可视化资料。进入本目录工作前，必须先遵守根目录 `AGENTS.md` 和 `project-info/AGENTS.md`，再遵守本文件。

## 目录定位

- 本目录承载平台整体架构和跨模块设计，不属于单个需求 loop 的必备阶段。
- 只放架构图、流程图、说明图、架构说明文档和图片生成相关资料。
- 不放需求分析、UI 原型、测试用例、业务实现代码或运行时产物。
- 图片和说明必须保持通用测试平台定位，不绑定具体业务系统。

## 架构内容边界

- 架构说明必须体现 monorepo、固定开发 loop、DRF 后端、Vue 3 前端、Jenkins 严格执行主干、`api-test` 执行核心、Docker 基础设施和 Allure 报告入口。
- 架构说明必须体现后期整个平台可通过 Docker Compose 整体打包部署，且容器化不能改变 Jenkins 作为测试执行唯一主干的原则。
- 如果架构图新增模块，必须同步说明该模块职责、上下游关系和是否属于固定 loop。
- 不能把尚未确认的功能画成既定架构；未确认内容只能标注为草案或待定。
- 涉及后端、前端、Jenkins、`api-test` runner、Nginx、MySQL、报告产物和 volume 的关系时，必须说明容器边界、服务间访问方式和不可写死的配置项。

## 推荐技能

- `drawio-skill`：绘制架构图、流程图、ER 图和导出 PNG/SVG/PDF。
- `imagegen`：生成 PNG 等位图说明图片时使用。

## 文件约定

- 架构说明书优先命名为 `project-architecture.md`。
- 架构图源文件优先命名为 `project-architecture.drawio`。
- 普通预览 PNG 优先命名为 `project-architecture.png`。
- 带嵌入 XML 的可编辑 PNG 优先命名为 `project-architecture.drawio.png`。
- 执行流程图优先命名为 `execution-flow.drawio`、`execution-flow.png` 或 `execution-flow.md`。
- 图片应尽量使用高分辨率输出；如果 4K 不稳定，允许使用 2K。

## draw.io 导出约定

- 导出前先校验 `.drawio` XML。
- 普通预览 PNG 不使用 `-e`。
- 最终可编辑 PNG 使用 `-e`，并在导出后运行 `repair_png.py`。
- 当前 Windows draw.io CLI 路径可参考 `project-architecture.md` 中的说明。

## 安全要求

- 不在架构图或说明中暴露真实账号、密码、token、cookie、Jenkins API Token、租户密钥、生产 URL 或敏感地址。
- 示例地址、端口、凭据和业务名称必须使用占位符或脱敏值。
