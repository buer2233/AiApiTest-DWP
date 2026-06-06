---
name: api-test-common
description: 通用接口自动化编写 skill，随 ai-api-test 框架分发，物理位置 `.claude/skills/api-test-common/`。用于在 ai-api-test 或其复制项目中新增、维护、补齐、迁移接口方法与 pytest 用例。触发场景包括：新增接口方法、新增接口测试用例、维护已有接口方法与用例、补齐参数化、修复接口断言、抓包生成、参考已有用例、cURL 手工生成、pytest 报错驱动维护、按 URL 查重复实现、处理 UTF-8 中文编码、执行 pytest 与 Allure 验证闭环。
---

# api-test-common

`api-test-common` 是 `ai-api-test` 的项目内接口自动化编写 skill。它把“新增”和“维护”拆成两条独立上下文路径，支持接口方法层 + pytest 用例层的通用接口自动化流程，适合复制到任意 Web 项目后继续使用。

## 适用范围

当任务涉及在当前项目中新增或维护以下内容时，优先使用本 skill：

- `test_case/page_api/` 下的接口方法
- `test_case/test_*_case/` 下的 pytest 接口用例
- 抓包数据到接口方法/用例的转换
- 参考已有用例补齐同类用例
- 根据 cURL 和响应体生成或维护接口方法/用例
- 根据 pytest 真实失败维护已有接口用例
- 修复接口断言、Allure 标注、导入路径、返回结构和 pytest 执行失败

## 前置门禁（新增 / 维护分流）

任何进入接口自动化编写/维护的任务，AI 必须先确认任务类型：

| 任务类型 | 适用场景 | 读取顺序 |
|---|---|---|
| 新增 | 新接口、新用例、补齐新链路 | 先读 `doc/preflight_gates_new.md`；门禁通过并选定方式后，再读 `doc/coding_style_guide.md` + 对应 `doc/mode_*.md` |
| 维护 | 既有用例修复、接口方法调整、链路回溯、参数/断言更新 | 先读 `doc/preflight_gates_maintenance.md`；门禁通过并选定方式后，再读 `doc/coding_style_guide.md` + `doc/maintenance_prompt_context.md` + 对应 `doc/mode_maintenance_*.md` |

若任务类型未明确，先询问“新增还是维护”。若用户已明确表达“维护 / 修复 / 同步最新链路 / 回归更新 / 按 pytest 报错修”等信号，可直接推断为维护。

## 用例编写/维护方式

| 方式 | 新增任务 | 维护任务 |
|---|---|---|
| ① 抓包驱动 | `doc/mode_capture_driven.md` | `doc/mode_maintenance_capture_driven.md` |
| ② 参考已有用例 | `doc/mode_reference_case.md` | `doc/mode_maintenance_reference_case.md` |
| ③ cURL 手工 | `doc/mode_curl_manual.md` | `doc/mode_maintenance_curl_manual.md` |
| ④ pytest 报错驱动 | 不适用 | `doc/mode_maintenance_pytest_driven.md` |

硬性要求：

- 编写任何接口方法或 pytest 用例前，必须先读 `doc/coding_style_guide.md`。
- 若任务类型为维护，必须额外读 `doc/maintenance_prompt_context.md`。
- 选定方式后，必须读上表对应的 `doc/mode_*.md` 并按其中步骤执行。
- 需要排查历史高频问题时，按需读 `doc/high_frequency_experience.md`。
- 不允许只凭 `SKILL.md` 摘要执行具体方式的详细步骤。

维护方式④默认优先使用 `/test-fixing`；只有 `/test-fixing` 无法解决、维护遇到困难或前后接口/调用栈信息不明确时，才使用 `/Debugging` 断点调试辅助定位。

## 流程图

Mermaid 源文件见 `flow_chart/flow.md`。当前 common skill 只保留 Mermaid 源文档，不包含导出的流程图片。

## 项目规范锚点

- 通用配置：`config.py`
- 统一入口：`runpytest.py`
- 接口基类：`test_case/page_api/public/base_api.py`
- 请求增强：`utils/timeout_http_adapter.py`
- 抓包底座：`capture/capture_addon.py`
- 抓包允许前缀：`capture/allowed_prefixes.txt`
- 抓包禁止前缀：`capture/blocked_prefixes.txt`
- URL 索引：`tools/page_api_index.sqlite3`
- 抓包运行时产物：`runtime/latest.jsonl`、`runtime/capture_selection.md`

## 核心原则（详见 `doc/core_principles.md`）

1. **两层结构**：先写接口方法，再写 pytest 用例调用接口方法。
2. **最小必要改动**：只在用户指定位置插入，不重构无关代码。
3. **UTF-8 与中文安全优先**：文件按 UTF-8 读写，写入后真实校验。
4. **先复用，后新增**：优先查 `tools/page_api_index.sqlite3`，按 URL path + HTTP method 查重。
5. **以真实返回为准**：断言基于抓包、cURL 或 pytest 实际返回。
6. **Allure 标准化**：类级 `epic/feature`，方法级 `story/severity`，步骤级 `with allure.step(...)`。
7. **接口方法返回规范**：默认只断言 HTTP `status_code`，然后 `return res.json()`；业务断言写在 pytest 用例中。
8. **抓包过滤可配置**：`allowed_prefixes.txt` 为空时不做白名单限制，非空时先按允许前缀筛选；`blocked_prefixes.txt` 为空时不做黑名单限制，非空时再排除匹配前缀的请求。
9. **测试闭环**：默认执行 pytest，生成 Allure 结果；导入路径、执行目录、关键失败和最终结果必须说明。

## 失败排查优先级

1. 导入路径问题：`ModuleNotFoundError` / `ImportError`
2. 编码问题：中文乱码、文件解析失败
3. 插入位置错误、装饰器误挂
4. fixture / 前置依赖问题
5. base_url、headers、cookies、token、代理或证书问题
6. 接口真实返回与断言不匹配
7. payload 类型、字段名或请求方法不匹配
8. 接口方法返回层级误判

排查后若确定为环境、网络、认证、账号或被测系统问题，停止无意义改代码，上报用户并说明证据。

## 输出结果模板

```text
【新增/维护接口用例】(N个)
用例函数名：完整中文标题

【新增/维护接口方法】(N个)
方法名：完整中文说明

pytest 执行命令
...

关键日志
...

报错与修复过程
...

最终结果
...
```

默认必须返回新增/维护接口用例列表、新增/维护接口方法列表和 pytest 执行结果；未新增也要写 `新增/维护接口方法（0个）`。
