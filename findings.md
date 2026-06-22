# Findings & Decisions

## Requirements
- 当前框架已有完整接口自动化结构，可通过 AI 编写接口方法和 pytest 用例。
- 已有可执行 demo，可生成 Allure 测试报告。
- 需要在现有框架结构基础上增加 CICD 能力。
- 需要在网页端测试平台实现执行用例、错误重试、测试报告展示、Jenkins 执行查询等功能。
- 用户要求先一起头脑风暴并反复对接需求，直到需求确认通过，再使用 TDD 模式开发。
- 项目必须保持通用接口自动化框架定位，不绑定具体业务系统，不引入真实账号、cookie、token 或业务常量。
- 前端使用 Vue 3，目录为 `front-end/`。
- 后端使用 Python DRF，目录为 `back-end/`。
- 现有接口自动化测试框架需要迁移到 `api-test/`，包含 `report/`、`test_case/`、`test_data/`、`utils/`、`config.py`、`conftest.py`、`pytest.ini`、`requirements.txt`、`runpytest.py`。
- 迁移后必须执行 `runpytest.py` 验证路径处理和运行能力未受影响。
- Jenkins 第一阶段必须实现，目录为 `jenkins/`，通过 Groovy 脚本调用本地接口自动化测试、失败重试、Allure 报告生成等能力。
- 失败重试需要支持选择一个或多个失败用例重试、一键重跑全部失败用例、按模块重试，模块通过测试用例文件夹区分。
- 失败用例重试通过组合 pytest 用例 ID 进行重跑。
- Web 平台需要展示每条失败用例的简要信息，并支持点击打开 Allure 报告。
- 平台需要用户登录和权限，先保留管理员和普通用户两类角色，当前权限可以一致，但模型要预留后续差异化权限空间。
- 截图是参考设计，不要求完整照搬。
- 这是大型任务，需要分 10 个阶段开发，每个阶段都必须执行完整 TDD 流程，开发计划文档要持续记录阶段、任务和进度。
- 每个阶段必须单独完成：需求分析、编写测试用例、开发、测试。
- 每个阶段开发和测试完成后，必须单独执行 `git commit` 和 `git push`。
- DRF 认证使用 DRF Token。
- 后端数据库默认直接使用本地 MySQL。
- 前端组件库使用 Element Plus。
- Jenkins 查询与触发 API 阶段要确认 Windows 和 Linux 兼容；脚本源文件存放在 `jenkins/` 并通过 git 管理。
- Allure 报告展示方式确认打开静态 HTML 报告。
- 开发和测试中产生的文档全部记录在 `docs/`。

## Research Findings
- 根目录没有 `.codegraph/`，后续代码理解直接使用 `rg` 和文件读取。
- 项目已有 `runpytest.py`、`conftest.py`、`config.py`、`test_case/page_api/`、`test_case/test_gbif_case/`、`report/` 等结构。
- 根目录已有上一轮任务的规划文件，本轮已替换为 CICD + 测试平台需求设计计划。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 需求阶段先不写实现代码 | 用户要求需求确认后才进入 TDD 开发 |
| 设计时将 Jenkins 能力抽象为可替换集成 | 便于本地测试、模拟 Jenkins、未来对接真实 Jenkins |
| 把平台功能拆成任务编排、执行器、报告、CICD 集成、前端展示几个域 | 降低复杂度，便于测试和渐进交付 |
| 每阶段完成后单独 commit 和 push | 满足用户对阶段边界和版本管理的要求 |
| 后端默认本地 MySQL，不再使用 SQLite 作为默认数据库 | 用户已明确指定数据库方案 |
| `AGENTS.md` 和 `README.md` 必须先反映 CICD 平台定位 | 这两个文件是后续 AI 和工程师最容易先读到的入口，必须避免继续传递旧的单体接口自动化框架定位 |

## Documentation Alignment
- 2026-06-22 17:54:17 +08:00：已将 `AGENTS.md` 更新为 CICD AI 自动化测试平台的后续 AI 接手规则，明确必须读取主计划、`task_plan.md`、`findings.md`、`progress.md`、`README.md` 后再继续开发。
- 2026-06-22 17:54:17 +08:00：已将 `README.md` 更新为平台总览，包含 `api-test/`、`jenkins/`、`back-end/`、`front-end/`、`docs/` 的职责，10 阶段主计划和当前 `api-test` 运行入口。
- 当前工作区显示 `api-test/` 已存在迁移内容，根目录旧接口框架文件处于删除状态；后续继续 Stage 2 前必须核对迁移测试和实际验收结果，不能仅凭目录存在标记完成。

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 规划文件已有旧任务内容 | 已替换为当前任务计划，并在进度中记录 |

## Resources
- `AGENTS.md`
- `runpytest.py`
- `conftest.py`
- `config.py`
- `test_case/page_api/public/base_api.py`

## Visual/Browser Findings
- 参考图 1：模块通过率列表页包含顶部导航、左侧菜单、筛选区、模块/库类型页签、模块表格、通过率、运行时间，以及“一键失败重试”“模块重试”“更多”菜单；更多菜单含近 7 天、近 30 天、上传报告、Jenkins 任务、环境比对、作废等入口。
- 参考图 2：失败用例弹窗包含用例名、来源、日期、错误类型、执行状态等筛选项，支持选择失败用例，展示用例名、用例描述、错误类型、断言、执行状态、错误信息/确认信息；顶部有 Jenkins 任务、测试账号、替换测试账号、更多菜单；更多菜单含失败重试和一键失败重试。
