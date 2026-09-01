# 运行期依赖降级：功能用例依赖环境数据的标准做法

功能测试用例（尤其审批流/会签）几乎必然依赖环境数据——流程模板 ID、各角色账号、表单主表字段。这些**图谱查不到**（图里只有 `src/**/*.java`），用例必须做**运行期降级**而非硬编码，保证"克隆仓库即可收集、缺数据安全跳过"。

## 使用前提

本文件只描述“确认环境无可复用数据、且已按 `test-data-reuse.md` 完成查询与造数分析”之后的运行期降级。任何模块都必须先查现有数据，再决定是否进入这里；不能用环境变量或 `pytest.skip` 绕过复用和造数尝试。

## 三类依赖的降级策略

### 1. 流程模板 ID（workflowId）

先查询再使用：

1. 运行时调 `getCreateWorkflowList` 查询当前环境可创建的流程模板，并按业务名称、状态和权限筛选；`E9_CS_WORKFLOW_NAME` 只能作为筛选提示。命中后复用返回的 `workflowId`，不要重复创建模板。
2. 若用户通过 `E9_CS_WORKFLOW_ID` 提供候选 ID，仍必须先调用列表/详情接口确认该 ID 在当前环境存在且满足用例条件；验证失败不能直接使用该 ID。
3. 查询确认无满足条件的模板后，才进入 `test-data-reuse.md` 的 MCP 反查和接口造数流程；造数不可行时按四项失败格式阻断，不能直接 skip。
4. 已完成查询和造数尝试仍无法定位：`pytest.skip("未定位到会签流程模板；已查询并尝试造数，需人工准备模板...")`，跳过不误判失败。

```python
def _find_workflow_id(workflow_api):
    wf_list = workflow_api.get_create_workflow_list()
    for item in wf_list:
        workflow_id = str(item.get("workflowId") or "")
        name_matches = not CS_WORKFLOW_NAME or CS_WORKFLOW_NAME in str(item.get("workflowName") or "")
        configured_matches = not CS_WORKFLOW_ID or workflow_id == CS_WORKFLOW_ID
        if name_matches and configured_matches and workflow_id.isdigit():
            return int(item["workflowId"])
    return None
```

### 2. 角色账号（人员01~05）

- 用例通过 `login_employee(role)` 按 `employee1`~`employee5` 登录。
- `config.json`/`test_data/account.json` 槽位账号/密码为空时，`login_employee` 内部 `pytest.skip`，自动降级。
- 用例文档字符串写清角色映射（人员01=employee1、会签人=employee2+employee3、审批人=employee4+employee5），并注明**前提**是环境中流程模板的节点人员与账号一致。

### 3. 表单主表字段（mainData）

优先级从高到低：

1. 环境变量 `E9_CS_MAINDATA`（JSON 数组，如 `[{"fieldName":"xxx","fieldValue":"yyy"}]`）。
2. 运行时调 `getCreateWorkflowRequestInfo(workflowId)` 取字段定义，`isMand` 字段回填占位值、非必填字段仅在已有默认值时带上。
3. 取不到字段时 mainData 为空，创建会返回 `PARAM_ERROR`，此时用例断言明确报"表单字段无效，请配置环境"。

## 其他可降级项

- 节点名断言：`E9_CS_NODE2_NAME`/`E9_CS_NODE3_NAME` 环境变量（默认"审批2"/"审批3"），避免写死流程内部节点名。
- 流程标题：用 `autotest-` 前缀的可丢弃标题，便于识别与清理。

## 原则

- **降级用 `pytest.skip`，不 `xfail`、不弱化断言**——缺少依赖是"未执行"，不是"通过"。
- 环境变量只作为查询筛选或字段构造提示，不能绕过当前环境查询；数据基线仅在确认环境数据不可复用且契约允许时作为可审计的兜底。
- 显式断言失败时，先声明"本地工作副本版本可能与测试环境部署版本不一致"，再分析。
- 因数据缺失而 skip 时，消息必须写清查询结论、已尝试的造数步骤、失败原因和人工准备内容；四项内容不全时不得收尾。
