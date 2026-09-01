# MCP 查询指南：从功能步骤反推后端接口

本文件沉淀"如何仅通过 codebase-memory MCP 把功能动词翻译成 HTTP 接口"的可复用方法。项目名固定 `project="e9"`，所有查询工具都带它。

## 工具清单（查询 MCP，端点 `http://10.20.62.239:9750/mcp`）

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `list_projects` | 确认存在 `e9` | `include_details=true` |
| `search_graph` | 语义/名称/文件找符号 | `query`、`name_pattern`（正则）、`label`（Class/Method/Route/...）、`semantic_query`（**必须字符串数组**）、`file_pattern`、`limit` |
| `get_code_snippet` | 按 qualified_name 取源码 | 先 `search_graph` 拿到唯一 qn |
| `query_graph` | 只读 Cypher | `query` |
| `trace_path` | 调用链 BFS | `function_name`（尽量 qn）、`direction`、`depth` |
| `get_architecture` | 模块/入口/热点 | `aspects` |

现网**没有** `impact`/`callers`。结构影响面用 `search_graph` + `trace_path(inbound)`。

## 反推接口的固定套路

### 1. 功能动词 → `search_graph` 语义搜索

```
search_graph(project="e9", query="流程提交 会签 审批")
```

命中 `label=Method`/`Class` 的结果里挑名字带业务含义的（如 `submitRequest`、`doCreateRequest`）。`search_mode=bm25` 说明走全文；空结果就放宽：去掉 label、加正则 `name_pattern=".*Countersign.*"`。

### 2. 确认 URL 前缀 → 看 Controller 类级 `@Path`

用 `get_code_snippet` 取含方法的 Controller 类（带 `$` 结尾的 qn 是类，不带是方法）：

```
get_code_snippet(project="e9", qualified_name="e9.src.com.engine.workflow.web.WorkflowPAAction")
```

类里会看到 `@Path("/api/workflow/paService")` 与一堆 `@Path("/submitRequest")` 方法。**URL = 类级 path + 方法级 path**。

也可用 `query_graph` 直接列某个 Controller 文件的全部 Route（比读整段类源码省 token）：

```cypher
MATCH (r:Route) WHERE r.file_path CONTAINS "WorkflowPAAction" RETURN r.name, r.path, r.method LIMIT 60
```

`Route` 节点的 `name` 通常是方法级路径（如 `/submitRequest`），`path` 是文件相对路径，`method` 是 POST/GET。

### 3. 确认请求字段 → 找请求实体 + 解析方法

看 Controller 方法签名，入参常是 `ReqOperateRequestEntity` 之类实体。取该实体源码看字段：

```
get_code_snippet(qualified_name="e9.src.com.engine.workflow.entity.publicApi.ReqOperateRequestEntity")
```

再看 `request2Entity`（JSON body 优先、form 兜底的解析入口）确认协议与字段名大小写：

```
get_code_snippet(qualified_name="e9.src.com.engine.workflow.biz.publicApi.RequestOperateBiz.request2Entity")
```

关键结论（E9 workflow 实况）：**优先解析 JSON body；body 为空才回退 form/query 参数**。字段名如 `workflowId`、`requestId`、`requestName`、`mainData`、`otherParams`。

### 4. 确认返回结构 → 找响应实体

返回 `PAResponseEntity`（`code` 是枚举 `{name,statusCode}`、`data`、`errMsg`），`code.statusCode`：SUCCESS=1、PARAM_ERROR=2、NO_PERMISSION=3、SYSTEM_INNER_ERROR=4、USER_EXCEPTION=5、FAIL=6。

`data` 内的实体决定断言字段，例如流程状态返回 `currentNodeName`/`currentNodeId`/`currentNodeType`/`status`。

### 5. 区分列表"待办/已办"

E9 待办列表链路：`doingBaseInfo` → `splitPageKey(viewScope=doing)` → EC `get_table_datas(dataKey=sessionkey)`；已办同理但换 `viewScope=done` 与 `doneBaseInfo`。`viewScope` 是 `GenerateDataInfoBiz` 里 `String scope = reqparams.get("viewScope")` 的决定性分支。

## 直接调 MCP 的脚本

WorkBuddy 会话未挂载该 MCP 时，用 `temp/mcp_query.py <tool> '<json_args>' [timeout]` 直连 Streamable HTTP（本项目已备好同款脚本）：

```bash
"C:/Users/admin/.workbuddy/binaries/python/versions/3.13.12/python.exe" temp/mcp_query.py \
  search_graph '{"project":"e9","query":"会签提交 审批","limit":15}' 120
```

## 覆盖范围（心里要有数）

索引几乎只有 `src/**/*.java`。JSP、SQL、`src4js*`、图片、多数 Web 模块**不在图里**。说到"只有这些文件受影响"前先 `check_index_coverage`。图外文件只能写"图谱未覆盖"，不得转本地 Grep/Read。

## 常见坑

- `search_graph` 空结果：多半漏了 `project="e9"`，或 `semantic_query` 误传字符串（必须数组）。
- `get_code_snippet` 的 `qualified_name` 不唯一时报 `ambiguous`，从 suggestions 抄 qn，别硬猜短名。
- 类源码 >500 行会 `source_clipped=true`，大 Controller 用 `query_graph` 列 Route 代替读全类。