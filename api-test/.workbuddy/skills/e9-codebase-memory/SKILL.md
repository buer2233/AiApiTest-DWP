---
name: e9-codebase-memory
description: "通过远程 codebase-memory MCP 知识图谱查询 E9（Ecology）Java 结构、调用链，以及 E9 提交的变更影响点与影响范围。用户只要提到 E9、ecology、知识图谱、调用链、谁调用了、影响点、影响范围、变更影响、E9 提交分析、codebase-memory、search_graph，或使用 /e9-codebase-memory，就必须用本 skill。绝对禁止使用 Grep/Glob/Read/Bash 等本地工具查询 E9 代码，仅能通过 MCP。不要用于非 E9 仓库、不要调用 git 版 detect_changes、不要擅自重建或删除远程索引。"
---

# E9+AI接口自动化测试框架：E9 代码知识图谱 MCP

你正在查询一套**已经建好、远程共享**的 E9 Java 知识图谱。结构类问题用图谱，比逐文件 grep 更准、更省 token，也能跨包找到调用方。

图谱项目名固定为 **`e9`**。所有图谱工具都必须传 `project="e9"`。

默认远程地址（用户另给主机时以用户为准）：

- 查询 MCP Streamable HTTP：`http://10.20.62.239:9750/mcp`（优先）
- 查询 MCP SSE 备选：`http://10.20.62.239:9750/sse`
- 运维 MCP（时态 log/diff）：`http://10.20.62.239:9750/servers/e9-ops/mcp`

若当前会话没有 `codebase-memory` 的工具，告知用户把上述 URL 配进 MCP 后**新开会话**。不要在客户端机器上对 E9 做 `index_repository`。

工具参数细节读 [references/mcp-tools.md](references/mcp-tools.md)。

## 硬性规范

1. **仅通过 MCP 查询，禁止本地工具。** 查定义、调用方、被调用、架构、影响面时，**必须且仅能**通过 `codebase-memory` MCP 查询。**绝对禁止**使用 Grep/Glob/Read/Bash 等本地工具查询 E9 代码、SVN 提交信息或 CBM 知识图谱。图谱未覆盖的文件（JSP/SQL/前端）只能说明"图谱未覆盖"，不得转而用本地工具查询 E9 源码。
2. **必须带 `project="e9"`。** 空结果多半是漏了这个参数。
3. **先解析名字再追踪。** `trace_path`、`get_code_snippet` 需要唯一符号。若返回 `ambiguous`，从 suggestions 里选 `qualified_name`，或先 `search_graph`。禁止瞎猜 qn。
4. **不要改共享索引。** 除非用户明确要求重建或删除 E9 图谱，否则不要调用 `index_repository`、`delete_project`。
5. **覆盖范围不是整套产品。** 索引几乎只有 `src/**/*.java`。JSP、SQL、`src4js*`、图片、多数 Web 模块都**不在图里**。问题或变更文件一旦离开 `src/`，必须写明这条限制。
6. **没有覆盖检查，不下穷尽结论。** 说「没有别人调用」或「只影响这些文件」之前，对你引用的 Java 路径调用 `check_index_coverage`。结果干净只表示「没有记录到的缺口」，不是完整性证明。
7. **inbound = 影响范围。** 别人会不会被这次改动波及，用 `trace_path(direction="inbound")`。outbound 是改动代码自己依赖谁。默认影响分析：inbound，深度 2–3。

## 怎么调工具

先在 `codebase-memory` 这个 MCP 上发现工具，再按刚拿到的 schema 调用。名称可能带前缀（Grok 里常见 `codebase-memory__search_graph`）。不要编造参数名。

Grok 典型顺序：`search_tool` → `use_tool`。其它客户端可能直接露出 15 个工具。

## 流程 A — 代码信息查询

用户问某个类/方法做什么、谁调用它、模块怎么划分、功能在哪时用这条。

1. 每个会话先 `list_projects` 一次，确认存在 `e9`。
2. `search_graph`：
   - 自然语言：`query="提交流程请求"`
   - 近似类名：`name_pattern=".*WorkflowRequest.*"`，可加 `label`（`Class` / `Method` / `Function` / `Interface` / `Route`）
   - 语义检索（必须是**数组**）：`semantic_query=["submit","workflow"]`
3. 多条命中时，按用户说的模块选 qn（看分组前缀里的包路径）。
4. `trace_path`：把该 **qualified_name** 当作 `function_name`。解释代码默认 `direction="both"`；问「谁在用」用 `inbound`。
5. 有了唯一 qn 再 `get_code_snippet`。不要整文件倾倒。
6. 问的是模块而不是单个符号时，`get_architecture`，`aspects=["overview"]`（或 `clusters`）。
7. 答案里点名的每个 Java 文件都做 `check_index_coverage`。

`search_graph` 为空时：放宽正则、去掉 `label`、改用 `query=`。仍为空，多半在 JSP/SQL/前端 —— 明确说图谱未覆盖，不得转用本地 Grep/Read 查询 E9 源码。

## 流程 B — E9 提交影响点 / 影响范围

用户问最近一次改动、修订号 `rNNNNNN`、日志里的单号、变更影响、blast radius、「这次提交会改坏什么」时用这条。

**不要**调用 `detect_changes`（E9 用 SVN，`detect_changes` 跑的是 `git diff`）。

最短循环：

1. 确定修订号（用户提供的 `rNNNNNN`）。**仅**通过 MCP 查询变更信息，**禁止**执行本地 SVN 操作或使用 Grep/Read 等本地工具，禁止 `detect_changes`。
2. 运维 MCP 取时态（不要 `confirm`，不要 `e9_sync`）：
   - `e9_svn_log(revision)` → 作者 / 说明 / paths
   - `e9_svn_diff(revision)` → unified diff
3. 路径分成 **图内**（`src/**/*.java`）和 **图外**。
4. 每个图内文件：`search_graph(file_pattern=..., label=Class|Method)` 得到种子符号。现网 **没有** `impact` / `callers`。
5. 每个种子（优先变更方法，大约最多 15 个）：`trace_path(function_name=<qn>, direction="inbound", depth=3)`。
6. 把调用方归并到包/模块，去重。
7. 对你点名的 Java 路径做 `check_index_coverage`。
8. 写影响报告。图内证据和图外「索引看不到」必须分开写。纯 JSP/SQL 不要编造符号级影响面。

## 回答风格

- 先给结论（改了什么 / 谁会被波及）。
- 引用 **qualified name** 和 `file_path`，不要只写短方法名（E9 里 `isUpdate` 会撞名）。
- 区分 1 跳直接调用方和更深层的传递调用方。
- 标注把握：图谱支撑 / 不在索引 / 覆盖缺口。
- 不要声称图谱覆盖了 JSP 页面流、SQL 升级脚本或 `src4js` 里的 JS。

## 共享服务上的安全

该 MCP 在局域网无鉴权。默认只读：

- 可以直接用：search、trace、query_graph（只读 Cypher）、snippet、architecture、coverage、list_projects、index_status。
- 先问用户：`index_repository`、`delete_project`、`manage_adr` 的写入、`ingest_traces`。

---

## 运维 MCP（codebase-memory-ops）

本 SKILL 对应的查询 MCP（`codebase-memory`）只负责代码分析。图谱主机的 SVN 同步、索引重建、状态查看等**运维操作**由独立的 **codebase-memory-ops** MCP 提供。

### 服务信息

| 项目 | 值 |
|------|-----|
| 服务器名 | `e9-ops` |
| 协议版本 | MCP 2024-11-05（Streamable HTTP） |
| 端点 URL | `http://10.20.62.239:9750/servers/e9-ops/mcp` |
| SSE 备选 | `http://10.20.62.239:9750/servers/e9-ops/sse` |

### 可用工具

| 工具 | 用途 | 是否只读 | 关键参数 |
|------|------|---------|---------|
| `e9_status` | 查看图谱主机上 E9 工作副本的 SVN 版本和知识图谱状态 | ✅ 只读 | 无；不能查历史 revision |
| `e9_svn_log` | 指定 revision 的提交元数据与变更路径 | ✅ 只读 | 仅 `revision`（正整数或 `r` 前缀）。禁止 `confirm` / path / 凭据，不 `svn update` |
| `e9_svn_diff` | 指定 revision 的 unified diff | ✅ 只读 | `revision`；可选 `max_bytes`（默认 256KiB，上限 1MiB） |
| `e9_svn_update` | 在图谱主机上对 E9 工作副本执行 `svn update`，**不重建图谱** | ❌ 写入 | `confirm`（必须传 `"e9-sync"`） |
| `e9_reindex` | 用当前工作副本**重建/更新** e9 知识图谱，不执行 svn update | ❌ 写入 | `confirm`（必须传 `"e9-sync"`）、`mode`（`"full"` / `"moderate"` / `"fast"`，默认 `"full"`） |
| `e9_sync` | 先 `svn update` 再重建图谱（= `e9_svn_update` + `e9_reindex`）。全量模式可能耗时 **15–40 分钟** | ❌ 写入 | `confirm`（必须传 `"e9-sync"`）、`mode`（默认 `"full"`） |

现网 **没有** `impact` / `callers`。结构影响面用查询 MCP 的 `search_graph` + `trace_path`。

### 使用场景与决策树

```
需要做什么？
├── 查看图谱状态 / 当前 SVN 版本
│   └── 调用 e9_status（只读，无需确认）
│
├── 查某一笔历史提交改了什么
│   └── e9_svn_log(revision) + e9_svn_diff(revision)（只读，无需确认，不要 update）
│
├── 只更新 SVN 工作副本（不重建图谱）
│   └── 调用 e9_svn_update(confirm="e9-sync")
│       适用：图谱主机代码落后，但索引结构无需变动
│
├── 只重建图谱（SVN 已是最新）
│   └── 调用 e9_reindex(confirm="e9-sync", mode="fast")
│       mode 说明：
│       - "fast"：跳过 similarity/semantic 边，提取仍全量，适合快速刷新
│       - "moderate"：中等粒度
│       - "full"：完整重建（默认）
│
└── SVN 更新 + 重建图谱（完整同步）
    └── 调用 e9_sync(confirm="e9-sync", mode="full")
        注意：全量可能 15–40 分钟，日常建议用主机 sync-all.ps1
```

### 安全约束

1. **所有写入操作必须传 `confirm="e9-sync"`**。不传或传错值会拒绝执行。
2. `e9_sync` 和 `e9_reindex` 会修改共享图谱，影响所有使用者。执行前必须：
   - 先调用 `e9_status` 确认当前状态
   - 告知用户预计耗时（全量 15–40 分钟）
   - 获得用户明确确认后再执行
3. **不要在远端会话中同步陪跑**：`e9_sync` 是长时间操作，MCP 客户端可能超时。日常同步建议用户在主机上直接运行 `sync-all.ps1`。
4. `e9_reindex` 失败时会返回 `index_diagnostics`（force_full / extract 进度 / containment_oom），根据诊断信息决定是否重试或切换 mode。

### 典型调用流程

**场景 1：检查图谱是否最新**

```
用户：E9 图谱状态怎么样？
AI：调用 e9_status → 返回 SVN 版本和索引状态
```

**场景 2：有新提交需要同步到图谱**

```
用户：把 E9 图谱更新到最新
AI：
  1. e9_status → 确认当前版本
  2. 告知用户："当前 SVN rXXXXX，最新 rYYYYY，需要 sync。全量约 15-40 分钟，确认？"
  3. 确认后 → e9_sync(confirm="e9-sync")
  4. 同步完成后 → e9_status 验证结果
```

**场景 3：图谱查询结果异常，怀疑索引过期**

```
用户：search_graph 查不到刚提交的方法
AI：
  1. e9_status → 发现 SVN 版本落后
  2. 建议 e9_svn_update 或 e9_sync
  3. 用户选择后执行
```

### MCP 配置

将以下配置写入项目的 MCP 配置文件后**重启会话**：

```json
{
  "mcpServers": {
    "codebase-memory-ops": {
      "url": "http://10.20.62.239:9750/servers/e9-ops/mcp"
    }
  }
}
```

本项目的配置文件位于 `.workbuddy/mcp/codebase-memory-ops.json`。

> **与查询 MCP 的区别**：`codebase-memory`（查询 MCP）提供结构查询工具（无 `impact` / `callers`），`codebase-memory-ops`（运维 MCP）提供只读时态查询（`e9_svn_log` / `e9_svn_diff`）和写入类维护工具。两者互补：查询 MCP 负责「当前图里有什么」，运维 MCP 负责「某一笔 SVN 提交改了什么」以及维护图谱。
