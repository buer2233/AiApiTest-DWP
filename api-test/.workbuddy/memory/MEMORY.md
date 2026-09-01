# E9 接口自动化项目长期记忆

## e9-ops 运维 MCP（更新代码 + 重建图谱）

- 端点 `http://10.20.62.239:9750/servers/e9-ops/mcp`（配在 `.workbuddy/mcp/codebase-memory-ops.json`），**10 工具**（2026-08-28 起）：`e9_status` / `e9_svn_log(revision)` / `e9_svn_diff(revision[,max_bytes])` / `e9_svn_update` / `e9_reindex(mode)` / `e9_sync` / **新增** `e9_list_revisions`(锚点前后 N 笔) / `list_revisions`(别名) / `e9_list_revisions_in_range`(闭区间) / `list_revisions_in_range`(别名)。写入类需 `confirm='e9-sync'`。
- 查询端 `http://10.20.62.239:9750/mcp`（`codebase-memory.json`），**15 工具**：`search_graph` / `query_graph` / `trace_path` / `get_code_snippet` / `search_code` / `index_status` / `list_projects` / `detect_changes` / `manage_adr` 等。查询工具需带 `project="e9"`。
- **查询 SVN revision 的正确姿势**：`e9_svn_log(rXXXX)` / `e9_list_revisions_in_range` 只覆盖「改动 E9 trunk」的提交；SVN 全局 revision 号里存在「未改 trunk」的空号（如 r349200 存在但 `to_exists=false`），直接 `e9_svn_log` 会返回 `revision_not_found`——先用 `e9_list_revisions_in_range` 定位真实 trunk revision，再取 log/diff。
- WorkBuddy 会话**未**挂载这两个 MCP，需直连 Streamable HTTP 驱动。通用直连脚本 `temp/mcp_call_any.py <query|ops> <tool> '<json_args>' [timeout]`。
- 增量索引已覆盖三种场景（修改定义、新增定义、新增文件），全量回退 OOM 问题已根治。有效配置：`CBM_MEM_BUDGET_MB=16384`、`CBM_WORKERS=1`、`CBM_RETAIN_TOTAL_MB=128`、`CBM_RETAIN_PER_FILE_MB=8`。
- 诊断日志：`C:\Users\admin\cbm-runtime\cache\logs\cbm-daemon.log`。直连脚本 `temp/mcp_call.py <tool> '<json_args>' [timeout_sec]`。

## Allure 报告查看

Allure 报告是前端 SPA，不能用 `file://` 直接打开。正确做法：用 `python -m http.server` 起本地静态服务，再通过 http 访问。

```bash
cd D:\AI\E9_svn_analyse\api-test-E9
python -m http.server 8917 --bind 127.0.0.1
# 访问：http://127.0.0.1:8917/allure-report-r<rev>/index.html
```

Git Bash 下 `allure` 命令行容易 fork 失败，改用 PowerShell：
```powershell
& "D:\Program Files (x86)\allure-2.13.8\bin\allure.bat" generate <results> -o <report> --clean
```

## runpytest.py 执行坑

`runpytest.py` 用 `subprocess.run(["python", ...])` 调用 PATH 上的 `python`，若 PATH 中没有 venv python 会命中无 pytest 的系统 Python。解决：把 venv python 前置到 PATH。

```bash
export PATH="/c/Users/admin/.workbuddy/binaries/python/envs/default/Scripts:$PATH"
python -m pytest test_case -m r<REV> --alluredir=report/allure-results-r<REV>
```

## 沙箱文件清理

沙箱 `report/allure-results` 批量删除被 `SAFE_DELETE_BULK_CONFIRM_REQUIRED` 拦截（阈值 50）。解决：使用独立结果目录（如 `allure-results-r<rev>`）绕开清理问题。

## 沙箱对 `.git` 写入会回滚（重要）

Bash 沙箱内对 `.git/` 目录的写入**会被虚拟化回滚**：本次命令内 `ls` 能看到文件，下一条命令再查就没了。命令行出现 `⚠️ Sandbox bypassed (escalation-approved)` 时才真正落盘。

**凡是写 `.git/` 内部文件（refs、config 等），一律改用 PowerShell 工具执行。**

## Git 远程操作两个坑

1. **`git fetch origin` 静默失败**：退出码 1、stdout/stderr 全空，常被误判为「远程被删」。真实原因是 HTTP 认证——全局 `credential.helper` 为 GCM，非交互环境弹不出登录窗。验证命令：

   ```bash
   GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git -c credential.helper= fetch origin
   # fatal: could not read Username for 'http://10.12.101.12': terminal prompts disabled
   ```

   网络本身是通的（`curl http://10.12.101.12/` 返回 302）。需 push/fetch 时先在可交互终端完成一次登录让 GCM 缓存凭据。

2. **`git update-ref` 在 ref 目录不存在时静默失败**：只追加 reflog、不创建 ref 文件，返回码仍为 0。恢复丢失的远端跟踪引用时，必须**先 `New-Item -Force` 建目录，再直接写 ref 文件**（内容即 40 位 commit hash）。目标 commit 从 `.git/logs/refs/remotes/origin/<branch>` reflog 末尾的「新值」列取得。`origin/HEAD` 为符号引用，内容是 `ref: refs/remotes/origin/master`。

## 接口封装命名规范

- `page_api/{模块}_api/{模块}_api.py` → `{Name}API` 命名空间自动加载。
- 命名空间查找规则：`login_admin.<name>` → `OdocFileAPI` 需 `name="odoc_file"`（`name.title().replace('_','')+'API'`）。

## 工作流 paService 公共 API（会签/提交/创建）

- 后端类 `WorkflowPAAction`（`src/com/engine/workflow/web/WorkflowPAAction.java`），类级 `@Path("/api/workflow/paService")`。
- 核心端点：
  - `POST /api/workflow/paService/doCreateRequest`：`workflowId`+`requestName`+`mainData[]`（元素 fieldName/fieldValue）+`otherParams.isnextflow=1`；返回 `data.requestid`。
  - `POST /api/workflow/paService/submitRequest`：`requestId`+`otherParams.src=submit`。
  - `GET /api/workflow/paService/getRequestStatus`：`requestId` → `data.currentNodeName/currentNodeId/status`。
  - `GET /api/workflow/paService/getCreateWorkflowRequestInfo`：`workflowId` → 表单定义。
  - `POST /api/workflow/paService/getCreateWorkflowList`：可创建流程模板列表。
- 列表待办/已办：`viewScope=doing`/`viewScope=done`。
- PA 响应：`{code:{name,statusCode},data,errMsg}`，SUCCESS.statusCode=1。
- WorkflowAPI 已封装对应方法；用例在 `test_case/test_workflow_case/test_workflow_countersign_case/`。