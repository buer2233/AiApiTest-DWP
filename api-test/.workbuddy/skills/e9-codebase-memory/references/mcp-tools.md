# codebase-memory 工具说明

所有查询类工具都要带 `project="e9"`（`list_projects` 除外）。Grok 里工具名可能是 `codebase-memory__<工具名>`。调用前用 schema，不要猜参数。

## 发现与查询

| 工具 | 用来做什么 | 关键参数 |
|---|---|---|
| `list_projects` | 确认索引里有 `e9` | `include_details=true` 可看节点/边数 |
| `search_graph` | 按名称 / 全文 / 语义找符号 | `query`、`name_pattern`、`label`、`file_pattern`、`semantic_query`（数组）、`limit`、`offset` |
| `trace_path` | 调用链 BFS | `function_name`（尽量用 qualified name）、`direction=inbound\|outbound\|both`、`depth`（1–5，默认 3） |
| `get_code_snippet` | 按 qn 取源码片段 | 先 `search_graph` 拿到 `qualified_name` |
| `query_graph` | 只读 Cypher | `query`；复杂模式、聚合、多跳 |
| `get_graph_schema` | 节点/边类型与计数 | 不熟图结构时先跑一次 |
| `get_architecture` | 模块、入口、热点、聚类 | `aspects`：`overview` / `clusters` / `all` |
| `search_code` | 带图谱增强的文本搜索 | `pattern`、`file_pattern`；比全库 grep 好，但仍比 `search_graph` 重 |
| `index_status` | 索引状态与覆盖缺口 | — |
| `check_index_coverage` | 核对指定路径是否被完整索引 | `paths` 和/或 `scopes`，至少要有一个 |

`search_graph` 三种模式可组合：

- `query="update settings"`：BM25 全文，适合自然语言。
- `name_pattern=".*RequestManager.*"`：正则匹配名字。
- `semantic_query=["submit","workflow"]`：**必须是字符串数组**，不能传单个字符串。

常用 `label`：`Class`、`Method`、`Function`、`Interface`、`File`、`Package`、`Route`。

`trace_path` 返回 `ambiguous` 时：从 suggestions 里拷 `qualified_name`，再带着完整 qn 重调，不要用短名字硬猜。

## 只读 Cypher 示例

```cypher
MATCH (c:Class) WHERE c.name CONTAINS 'WorkflowRequest' RETURN c.name, c.file_path LIMIT 20
```

```cypher
MATCH (f:Method)-[:CALLS]->(g) WHERE f.qualified_name ENDS WITH '.isUpdate' RETURN g.qualified_name LIMIT 30
```

超时就收窄 `WHERE`、改用有向 `MATCH`、加 `LIMIT`。不要对 350 万边做无过滤全图扫描。

## 不要默认调用

| 工具 | 原因 |
|---|---|
| `detect_changes` | 内部走 `git diff`。E9 是 SVN，会失败。提交分析用 `references/svn-impact.md`。 |
| `index_repository` | 会锁项目、耗内存，改的是共享图谱。除非用户明确要求重建。 |
| `delete_project` | 破坏性。 |
| `manage_adr` 的 update | 会改共享 ADR。查询可以，写入先问。 |
| `ingest_traces` | 写入运行时边，先问。 |

## 索引覆盖（心里要有数）

当前 `e9` 图几乎只有 `src/` 下 Java（仓库 `.gitignore` 只放行了 `src/`）。下面这些**不在图里**：

- 各模块 JSP（`workflow/`、`hrm/`、`docs/` 等）
- `data/`、`sqlupgrade/` 下的 SQL
- `src4js*` 前端
- 静态资源

图外路径：用 `e9_svn_diff` 说明「图谱看不到」，不要假装 `search_graph` 已经覆盖，也不要用本地 Read/Grep 去补。

## 客户端怎么接到这套 MCP

把下面写进对方项目的 MCP 配置后**重启会话**：

```toml
[mcp_servers.codebase-memory]
url = "http://10.20.62.239:9750/mcp"
enabled = true
```

或 JSON：

```json
{
  "mcpServers": {
    "codebase-memory": {
      "url": "http://10.20.62.239:9750/mcp"
    }
  }
}
```

对方机器不需要 E9 源码副本，也不需要安装 CBM 二进制。`get_code_snippet` 读的是图谱主机上的 `code_repo`。

---

## 运维 MCP 工具（codebase-memory-ops）

运维 MCP（`e9-ops`，端点 `http://10.20.62.239:9750/servers/e9-ops/mcp`）提供图谱主机的维护能力。与查询 MCP 互补：查询负责"读代码"，运维负责"维护图谱"。

| 工具 | 用途 | 只读 | 关键参数 |
|------|------|------|---------|
| `e9_status` | 查看 E9 工作副本 SVN 版本和知识图谱状态 | ✅ | 无；不能指定历史 revision |
| `e9_svn_log` | 指定 revision 的提交元数据 + 变更路径 | ✅ | 仅 `revision`。禁止 `confirm` / path / 凭据 |
| `e9_svn_diff` | 指定 revision 的 unified diff | ✅ | `revision`；可选 `max_bytes`（默认 256KiB，上限 1MiB） |
| `e9_svn_update` | 对 E9 工作副本执行 `svn update`，不重建图谱 | ❌ | `confirm="e9-sync"` |
| `e9_reindex` | 重建/更新 e9 知识图谱（不跑 svn update） | ❌ | `confirm="e9-sync"`、`mode`（`full`/`moderate`/`fast`） |
| `e9_sync` | `svn update` + 重建图谱，全量 15–40 分钟 | ❌ | `confirm="e9-sync"`、`mode` |

**现网没有 `impact` / `callers`。** 影响范围用 `search_graph` + `trace_path(direction="inbound")`。提交分析第一步用 `e9_svn_log` + `e9_svn_diff`，不要用 `detect_changes`。

### 安全约束

- 所有写入操作必须传 `confirm="e9-sync"`，否则拒绝执行。
- `e9_sync` / `e9_reindex` 修改共享图谱，影响所有使用者。执行前先 `e9_status` 确认状态，并告知用户预计耗时。
- `e9_reindex` 失败时返回 `index_diagnostics`（force_full / extract 进度 / containment_oom）。

### mode 参数说明

| mode | 行为 |
|------|------|
| `"full"` | 完整重建（默认），包含所有边类型 |
| `"moderate"` | 中等粒度 |
| `"fast"` | 跳过 similarity/semantic 边，提取仍全量 |

### 配置示例

```json
{
  "mcpServers": {
    "codebase-memory-ops": {
      "url": "http://10.20.62.239:9750/servers/e9-ops/mcp"
    }
  }
}
```
