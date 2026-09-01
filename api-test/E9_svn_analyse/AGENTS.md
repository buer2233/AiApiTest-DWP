# E9_svn_analyse/AGENTS.md — E9 代码分析专属规范

本目录是 E9 影响分析的**分析侧**：分析 CLI（`svn_analyse/`）、CLI 测试（`tests/`）、需求与开发文档（`docs/`）、分析产物（`output/`）。

- 框架侧规范（page_api / test_case / 命名 / 技术栈 / 语言规范）见 `../AGENTS.md`。
- 面向用户的编排（分析 → 用例 → 执行 → 报告）由 `.workbuddy/skills/svn-impact/` SKILL 承担，分析时先读该 SKILL。
- 本文件只放 E9 代码分析专属内容；框架通用要求不在此重复。

## 目录结构

```text
api-test-E9/E9_svn_analyse/
├── AGENTS.md              # 本文件
├── svn_analyse/           # 分析 CLI 包（python -m svn_analyse）
├── tests/                 # 分析 CLI 测试套件
├── docs/                  # 需求/计划书/进度日志（从项目根迁入）
└── output/                # 分析产物（不入 Git，重新生成即覆盖）
    ├── _inventory.json    #   api-test-E9 库存快照（脱敏）
    └── r<rev>/            #   单笔分析结果（facts/design/report）
```

E9 源码和知识图谱由外部 MCP 服务（codebase-memory）维护，所有代码分析统一通过 MCP 完成。本仓库不构建或维护本地图谱，不要求本地 SVN 工作副本。

## 分析 CLI 用法

在 `E9_svn_analyse/` 目录下执行（或任何把该目录加入 PYTHONPATH 的位置）：

| 命令 | 用途 |
|------|------|
| `python -m svn_analyse inventory` | 扫描 api-test-E9 已有 URL / 方法 / 用例 |
| `python -m svn_analyse reverse-lookup r<rev>` | 四期 T4.2：重建反查证据包；`--symbol` 查询单符号块，`--skip-mcp` 仅静态反查 |
| `python -m svn_analyse render output/r<rev>` | 根据 facts.json + design.json 重生成 HTML/MD |
| `python -m svn_analyse retest r<rev>` | 阶段 C：按 pytest mark 执行并出 Allure |
| `python -m svn_analyse select --keyword/--revision` | 按关键词或版本选取关联用例 |
| `python -m svn_analyse check-consistency --revision r<rev>` | 比较 revision mark 与 MCP callers |

**路径约定**：分析产物默认落在本目录 `output/`，不入 Git。

## revision 输入约定

一次只接受一个正整数 revision（可带 `r` 前缀）。拒绝 `HEAD`、版本范围、负数、零和一条消息中的多个版本。

## 外部 MCP 规范

- **所有代码分析统一走外部 MCP**：变更查询、影响分析、调用链追踪均由 MCP（codebase-memory）完成；本仓库不启动本地图谱服务，不直接调图谱 CLI，不执行本地 SVN 操作，不要求用户提供 SVN 地址或凭据。
- **版本与索引**由外部服务维护：版本路由、源码快照、图谱 sync/init 和 active generation 均不在本仓库执行。
- **MCP 不可用时降级**：查询失败写入 `facts.warnings` 并降低置信度，不中断分析；不静默编造图谱结论。
- 外部服务必须提供认证、版本/仓库 ACL 和审计，只暴露调用方需要的白名单工具，禁止通用 shell、任意路径、SVN URL 或凭据参数。

## E9 代码查询规范（codebase-memory MCP）

查询 E9 业务代码时，必须优先使用 `codebase-memory` MCP 知识图谱，不要一上来就 grep：

- **核心原则**：先图谱后文件。查定义、调用方、被调用、架构、影响面时，先调 MCP 工具，再考虑 Grep/Glob/Read。
- **项目名**：所有图谱工具必须传 `project="e9"`。
- **覆盖范围**：索引仅覆盖 `src/**/*.java`。JSP、SQL、`src4js*` 前端、静态资源**不在图内**，问题涉及这些路径时必须写明此限制。
- **禁止事项**：不调 `detect_changes`（E9 用 SVN 不是 git）、不调 `index_repository`/`delete_project`（共享图谱，不可擅自修改）。
- **详细流程**：见 `.workbuddy/skills/e9-codebase-memory/SKILL.md` 及其 `references/` 目录。

## 需求 / 计划 / 进度约定

- 需求权威定义：`docs/E9系统AI自动化需求方案.html`（已冻结，9 项需求，v2.1 排期）。
- 三期执行依据：`docs/三期开发/E9三期开发计划书.md`（T3.1–T3.10）。
- 进度记录：T3.x 追加到 `docs/三期开发/三期开发进度.md`（格式同一/二期）。
- 需求已冻结，发现缺口**不擅自改需求文档**：在三期进度文档登记变更申请（编号自变更 11 起），等人工评审。
- AI 严格按计划书任务编号执行，不自行新增任务。

## 安全红线

- 测试环境凭据文件（`config.json`、`test_data/account.json`）按三期已批准变更允许提交团队内部 GitLab，同事 clone 即用；凭据永久存于 `.git` 历史，改密需重写历史。
- 不把账号、密码、cookie、token、完整请求头/响应体写入 `output/`、`docs/`、进度日志、Allure 附件。
- `output/`、`report/`、`runtime/`、`logs/`、`__pycache__/`、`.workbuddy/memory/` 禁止提交。
- 测试失败先声明「本地工作副本版本可能与测试环境部署版本不一致」，未确认部署版本不把断言失败定性为产品缺陷。
- 不在代码中硬编码 IP 地址或域名，统一使用 `config.json`。

## 语言规范

所有 SKILL 说明文本、代码注释、模块/类/函数文档字符串和命令行参数描述使用简体中文；代码标识符、命令、文件路径、协议名称、产品名称和 JSON 字段名保持原样。交付前运行 `python ../tools/chinese_documentation_check.py --root .. --include-skills`。