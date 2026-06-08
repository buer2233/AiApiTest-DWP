# 核心原则详细执行规则

## 1. 两层结构

- 接口自动化必须保持接口方法层和 pytest 用例层分离。
- 先在 `test_case/page_api/` 编写或复用接口方法，再在 `test_case/test_*_case/` 编写 pytest 用例调用接口方法。
- pytest 用例不直接拼装底层 HTTP 请求，除非是在验证框架公共能力。

## 2. 最小必要改动

- 只在用户指定位置插入或追加。
- 不大面积覆盖原文件。
- 不擅自重构无关代码。
- 不因为局部问题整体改造公共逻辑。

## 3. UTF-8 与中文安全优先

- 所有目标文件必须按 UTF-8 读取，并按 UTF-8 写回。
- 写入中文后重新读取文件确认新增片段存在、无成片问号乱码。
- 如果中文显示异常，先区分终端显示问题和文件真实内容损坏。

## 4. 先复用，后新增

- 新增接口方法前，先按 URL `pure_path` + HTTP method 查 `tools/page_api_index.sqlite3`。
- 索引命中时复用已有接口方法；未命中才按用户指定位置新增方法。
- 新增接口方法后运行 `python .claude/skills/api-test-common/tools/scan_page_api.py` 刷新索引。
- 索引不可用时，可回退到 `rg` 搜索 URL path、方法名或接口描述。

索引更新：

```bash
python .claude/skills/api-test-common/tools/scan_page_api.py
python .claude/skills/api-test-common/tools/scan_page_api.py --full
```

## 5. 以真实返回为准

- 断言必须基于真实接口返回与真实运行结果。
- 抓包、cURL 和 pytest 报错驱动场景，都以对应的实际 response body 或运行结果为准。
- 如果参考结构与实际返回不一致，必须改断言，不硬套经验。
- 复用已有接口方法前，先确认它返回完整 JSON、`response.get("data")`、文本还是原始 `Response`。

## 6. Allure 标准化

- pytest 用例统一使用 Allure 标注。
- 类级使用 `@allure.epic(...)` 和 `@allure.feature(...)`。
- 方法级使用 `@allure.story(...)` 和 `@allure.severity(...)`。
- 关键步骤使用 `with allure.step(...)` 包裹，步骤文案使用清晰中文。

## 7. 接口方法返回规范

- 接口方法默认只断言 HTTP `status_code`，不在接口方法内断言业务 `code`。
- 默认通过 `BaseAPI` 封装方法返回解析后的 JSON。
- 业务字段、业务状态和数据结构断言写在 pytest 用例中。
- 非 JSON、重定向或需要原始响应的接口，按 `coding_style_guide.md` 使用 `return_response=True` 后在用例中处理。

## 8. 抓包过滤可配置

- `allowed_prefixes.txt` 为空时不做白名单限制。
- `allowed_prefixes.txt` 非空时，先按允许前缀筛选请求。
- `blocked_prefixes.txt` 为空时不做黑名单限制。
- `blocked_prefixes.txt` 非空时，再排除匹配前缀的请求。

## 9. 测试闭环

- 完成代码后默认执行 pytest，除非用户明确不要求运行。
- 默认生成 Allure 结果，并说明 Allure 结果目录或生成状态。
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
