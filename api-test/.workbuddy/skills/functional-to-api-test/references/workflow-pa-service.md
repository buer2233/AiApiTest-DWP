# E9 workflow 公共 API 约定映射（/api/workflow/paService/*）

本次实战确认的后端 `WorkflowPAAction`（类级 `@Path("/api/workflow/paService")`）接口约定。已封装的 `WorkflowAPI.doForceOver` 也在同一 Controller。功能用例转接口自动化时优先对照本表，同一 Controller 的新方法加进 `WorkflowAPI`，不建重复类。

## 端点速查

| 功能动作（功能用例动词） | HTTP | 关键入参 | 返回/断言 |
|---|---|---|---|
| 创建并提交流程（创建/发起） | `POST /api/workflow/paService/doCreateRequest` | `workflowId`(int)、`requestName`、`mainData`(数组，元素 `fieldName`/`fieldValue`)、`otherParams.isnextflow="1"`（创建即流转） | `data.requestid`（新建流程 ID） |
| 提交流程（提交/审批通过/会签提交） | `POST /api/workflow/paService/submitRequest` | `requestId`(int)、`otherParams.src="submit"`、`remark` 可选 | 会签节点集齐全部人后引擎才流转 |
| 查询流程状态（断言当前节点） | `GET /api/workflow/paService/getRequestStatus` | `requestId` | `data.currentNodeName`/`currentNodeId`/`currentNodeType`/`status` |
| 可创建流程列表（动态定位模板） | `POST /api/workflow/paService/getCreateWorkflowList` | 无（POST 空表单） | 数组，元素 `workflowId`/`workflowName`/`workflowTypeId`/`workflowTypeName`/`formId` |
| 表单定义（构造主表数据） | `GET /api/workflow/paService/getCreateWorkflowRequestInfo` | `workflowId` | `data.workflowMainTableInfo.requestRecords[].workflowRequestTableFields[]`（`fieldName`/`fieldValue`/`isMand`） |
| 强制归档（已有封装） | `POST /api/workflow/paService/doForceOver` | `requestId`、`remark` | 见 `WorkflowAPI.do_force_over` |

## 会签语义（关键，易错）

- **会签 = 多人各自提交一次 `submitRequest`**，不是专门接口。`DoSubmitRequestCmd` 是唯一提交实现。
- src 默认 `submit`；`save` 只保存不流转。`submitRequest` 里 `otherParams.src="submit"` 明确即可。
- 会签节点集齐全部会签人后，引擎在最后一次 `submitRequest` 里自动 `flowNextNode` 流转到下一节点；未集齐时流程停在原节点（`getRequestStatus.currentNodeName` 不变）。
- 断言"仍在审批2 / 已到审批3"**必须查 `getRequestStatus` 的 currentNodeName**，不能只看 submitRequest 的返回码（未集齐时也返回 SUCCESS）。

## 主表数据 mainData 的构造规则

- `mainData` 元素 `fieldName` 必须命中表单的 `getFieldMap`（字段定义），否则 `errMsg` 报 `error_param_<fieldName>` 且返回 `PARAM_ERROR`。
- `DoCreateRequestCmd` 强制 `mainData` 非空（`mainData==null || size==0` 时 `PARAM_ERROR`）。
- 本技能的标准做法：优先环境变量 `E9_CS_MAINDATA` 显式传；否则运行时调 `getCreateWorkflowRequestInfo` 取字段定义，`isMand` 字段回填占位值。

## PA 响应结构

```json
{ "code": {"name": "SUCCESS", "statusCode": 1}, "data": {...}, "errMsg": {...} }
```

| statusCode | 含义 |
|---|---|
| 1 | SUCCESS |
| 2 | PARAM_ERROR |
| 3 | NO_PERMISSION |
| 4 | SYSTEM_INNER_ERROR |
| 5 | USER_EXCEPTION |
| 6 | FAIL |

代码里 `code` 可能是 `{"name":"SUCCESS","statusCode":1}` 也可能是枚举名，断言时对两者都兼容（规范化成字符串对比 `SUCCESS`/`1`）。

## 列表 viewScope

- `viewScope=doing`：待办。
- `viewScope=done`：已办（SQL 条件 `isremark in('2','4') or (isremark='0' and takisremark=-2)`）。

取列表行：`splitPageKey` 返回 `sessionkey` → EC `get_table_datas(data_key=sessionkey)` 的 `datas[]`，行里 `requestid` 即流程 ID（兼容 `requestid`/`requestId` 大小写）。