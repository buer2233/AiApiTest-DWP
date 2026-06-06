# 核心原则详细执行规则

## 1. 最小必要改动

- 只在用户指定位置插入或追加。
- 不大面积覆盖原文件。
- 不擅自重构无关代码。
- 不因为局部问题整体改造公共逻辑。

## 2. UTF-8 与中文安全优先

- 所有目标文件必须按 UTF-8 读取，并按 UTF-8 写回。
- 写入中文后重新读取文件确认新增片段存在、无成片问号乱码。
- 如果中文显示异常，先区分终端显示问题和文件真实内容损坏。

## 3. 先复用，后新增

- 新增接口方法前，先按 URL `pure_path` + HTTP method 查 `tools/page_api_index.sqlite3`。
- 索引命中时复用已有接口方法；未命中才按用户指定位置新增方法。
- 新增接口方法后运行 `python .claude/skills/api-test-common/tools/scan_page_api.py` 刷新索引。
- 索引不可用时，可回退到 `rg` 搜索 URL path、方法名或接口描述。

索引更新：

```bash
python .claude/skills/api-test-common/tools/scan_page_api.py
python .claude/skills/api-test-common/tools/scan_page_api.py --full
```

## 4. 以真实返回为准

- 断言必须基于真实接口返回与真实运行结果。
- 如果参考结构与实际返回不一致，必须改断言，不硬套经验。
- 复用已有接口方法前，先确认它返回完整 JSON、`response.get("data")`、文本还是原始 `Response`。

## 5. 测试必须闭环

- 完成代码后默认执行 pytest，除非用户明确不要求运行。
- 推荐从项目根执行：

```bash
python runpytest.py --case-path <目标用例目录或文件>
```

或：

```bash
python -m pytest <目标用例文件或节点> -v --tb=short
```

- 记录执行目录、执行命令、关键日志、报错信息、最终结果。
- 如果失败，必须根据真实报错定位并修复，直到通过或确认是环境、网络、认证、账号、被测系统问题。
