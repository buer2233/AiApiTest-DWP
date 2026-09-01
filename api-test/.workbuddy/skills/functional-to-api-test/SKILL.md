---
name: functional-to-api-test
description: 为 E9+AI接口自动化测试框架将 E9 的功能测试用例（手工/业务描述）转换为接口自动化测试用例，并处理所有模块的前置数据查询复用、接口造数和缺失数据阻断。当用户提供功能测试用例步骤、业务审批流/会签流程描述、或要求"把 XX 功能用例转成接口自动化""按功能用例写接口自动化""功能用例转自动化"时使用。工作流分四步：功能步骤映射后端接口（仅通过 codebase-memory MCP 查 E9 代码知识图谱）、接口封装、用例实现、执行与运行期依赖降级。禁止用 Grep/Glob/Read/Bash 等本地工具查询 E9 源码，仅能通过 MCP 完成代码分析。
---

# E9+AI接口自动化测试框架：功能测试用例 → 接口自动化

本技能把一段**功能测试用例**（通常是"人员 A 创建并提交 → 人员 B 会签 → 人员 C 审批"这类业务流转描述）转换为 `api-test-E9/` 框架下的**接口自动化测试用例**。

工作流是**任务式四阶段**，但核心是"从功能步骤反推后端接口"。命令均相对 `api-test-E9/` 给出，不得写死本机绝对路径。

所有模块统一遵守前置数据决策契约，详见 `references/test-data-reuse.md`。该契约适用于流程、文档、邮件、看板及其他任何接口用例，不得因模块不同而省略。

## 硬性禁令（最高优先级）

- **仅通过 MCP 查 E9 代码**：定位接口、查参数契约、看方法实现，一律走 `codebase-memory` MCP（查询端点 `http://10.20.62.239:9750/mcp`，运维 `http://10.20.62.239:9750/servers/e9-ops/mcp`）。**绝对禁止**用 Grep/Glob/Read/Bash 查询 E9 源码、SVN 提交或知识图谱。图谱未覆盖的文件（JSP/SQL/前端）只能注明"图谱未覆盖"，不得转用本地工具。
- **不在 `page_api/`、`test_case/` 硬编码 IP/域名**，统一用 `config.base_url` 或 `base_url` fixture。
- **不把账号密码写入代码、日志、Allure 附件**。账号统一走 `load_account(role)`。
- **断言失败先声明环境版本假设**，未确认部署版本前不把失败定性为产品缺陷。

## 什么时候用

- 用户给出一段功能测试用例（含步骤序号、角色、列表/状态校验点），要求转接口自动化。
- 用户描述一个业务流程（创建、提交、会签、审批、流转）要求落地为自动化。
- 用户说"把 XX 功能用例转自动化"、"按功能用例写接口自动化"、"功能用例转接口自动化"。

不适用于：纯 UI 自动化（Playwright/Selenium）、纯单元测试、与 E9 无关的功能。

## 工作流总览

```
功能用例步骤 → ① 映射后端接口 → ② 封装接口方法 → ③ 实现用例 → ④ 执行 + 依赖降级
```

前三步的产物分别落在 `page_api/`（封装）与 `test_case/`（用例）；第四步决定"跑还是降级跳过"。

## 阶段 ①：功能步骤映射后端接口（核心）

这是本技能最有价值的一步——把"人类操作"翻译成"HTTP 调用"。用 MCP 图谱按下列顺序反推：

1. **识别功能动词 → 搜语义**。`search_graph(project="e9", query="流程提交 会签 审批")` 定位候选类与方法。动词对照：创建/发起 → `doCreateRequest`、提交/审批通过/会签 → `submitRequest`、查询状态/当前节点 → `getRequestStatus`、看列表 → 对应 `*BaseInfo` + `splitPageKey`。
2. **看类级 `@Path` 确定 URL 前缀**。用 `get_code_snippet` 取含 `@Path("/xxx")` 的 Controller（如 `WorkflowPAAction`）。接口方法 = 类级 path + 方法级 path。
3. **看入参实体确定请求字段**。找到方法签名里的请求实体（如 `ReqOperateRequestEntity`），取其字段列表，并看 `request2Entity` 之类解析方法确认"JSON body 优先、form 参数兜底"的协议。
4. **看返回实体确定断言字段**。找 `PAResponseEntity`（`code:{name,statusCode}`、`data`、`errMsg`）与 `data` 内的实体（如 `currentNodeName/currentNodeId/status`）。
5. **区分列表"待办/已办"**。E9 列表用 `viewScope` 区分（`doing`=待办、`done`=已办）；`splitPageKey(viewScope=...)` 拿到 sessionkey 后走 EC `get_table_datas` 取行。

查询细节（工具参数、只读 Cypher、覆盖范围）见 `references/mcp-query-guide.md`。

**产出**：一份"功能步骤 → 接口 + 参数 + 断言字段"的映射表，写进 `references/` 或直接作为用例设计注释。对 E9 workflow 公共 API（`/api/workflow/paService/*`）已有约定映射，见 `references/workflow-pa-service.md`。

## 阶段 ②：封装接口方法

按 `docs/api_test_case_spec.md` 写封装：

1. 目录 `page_api/<模块名>_api/`，主文件 `<模块名>_api.py` 或 `<模块名>_base_api.py`，类名 `{Name}API`。
2. 每个接口方法遵守"`url` 变量单独提取 → `error_msg` 用 kwargs.pop → 构造参数 → `self.get/post/put/delete`"顺序，"三行元数据 `# Author:`/`# Create Date:`/`# IsAI:`"必留。
3. 已存在的 URL 必须复用（先看 `page_api/` 现有封装，如 `WorkflowAPI` 已含 `do_force_over`，同一 Controller 的新方法应加进同一类，**不要新建重复类**）。
4. JSON body 型接口用 `json=payload`，表单型用 `data=form_data`；请求头统一 `self._browser_headers(...)`。

## 阶段 ③：实现用例

按 `docs/api_test_case_spec.md` 写用例：

1. 目录 `test_case/test_<模块名>_case/`，文件 `test_<模块名>_api.py`；模块级 `@pytest.fixture(scope="class", autouse=True)` + `global` + `setup_class` 模式注入登录态。
2. 用 `login_admin.<模块名>` / `login_employee("employeeN")` 按角色取 API；多角色流程用工厂 `login_employee(role)` 逐个登录（同一 role 自动缓存）。
3. **按功能用例步骤原样组织断言**——"提交前列表校验""提交后列表校验"分别对应"先查后提交""提交后再查"的 allure.step 块；每条断言用 `assert` + 失败信息带上下文。
4. 会签/审批这类**有状态流转**的用例，用 `getRequestStatus`（或等价状态接口）断言当前节点，而非只看提交接口的返回码。
5. 测试类与方法文档字符串写清角色映射（人员01=employee1 等）与运行前提。

## 阶段 ④：执行 + 运行期依赖降级

1. 用 venv 的 python 收集用例：`<venv>/python.exe -m pytest <用例目录> --collect-only`，先确认能收集（`test collected`）。
2. **先查并复用，再判断是否造数**：先通过现有接口方法查询当前测试环境中是否已有满足条件的数据，并优先复用；不得在已有可用数据时重复创建。查询应使用真实业务筛选条件，并把命中的业务 ID/关键字段作为后续接口入参锚点。流程模板、流程实例、文档、邮件、看板、表单等所有模块均执行此顺序。
3. **仅在数据为空时尝试接口造数**：只有确认当前环境无满足条件的数据，才通过 MCP 反查可用的创建/保存/发送/提交等接口，分析完整入参、权限和依赖，按可执行的多步接口链路尝试造数；不得直接硬编码内部 ID 或跳过查询。
4. **造数失败必须阻断该用例的可执行实现并如实报告**：当造数流程过于复杂、依赖无法满足或接口调用失败时，AI 必须明确说明：①当前测试环境缺失的具体数据；②已经执行的查询、接口反查和造数尝试；③失败的真实原因（含接口返回的脱敏错误或缺失依赖）；④需要人工协助构建的具体数据及完成后继续编写用例的条件。不得用假数据、弱化断言或把未完成链路伪装成通过。
5. 数据确实无法在阶段实现时，运行期才允许按 `references/runtime-fallback.md` 使用 `pytest.skip`；`skip` 原因必须包含缺失数据和人工准备提示，不能用 `xfail` 或弱化断言代替。
6. 完整降级模式与示例见 `references/runtime-fallback.md`；前置数据复用、查询、造数和失败报告的详细契约见 `references/test-data-reuse.md`。

## 交付收尾

- 运行 `python tools/chinese_documentation_check.py --root . --include-skills`，本次交付文件不得有违规项（`temp/` 与既有 skills 的告警可忽略，说明即可）。
- 用 `present_files` 展示新增的封装与用例文件。

## 命令参考

```powershell
# 收集用例（不执行，先验证收集成功）
<venv>/python.exe -m pytest test_case/test_<模块名>_case --collect-only -q

# 执行指定用例
<venv>/python.exe -m pytest test_case/test_<模块名>_case --alluredir=report/allure-results-<tag>
```

本环境 `runpytest.py` 内部硬编码 `"python"` 且 `--clean` 触发沙箱批量删除拦截，故直接用 venv 绝对路径 + 独立结果目录规避。
