# 方式1：抓包驱动

适用：用户选择新增方式1，或表达“用抓包 / 读 latest.jsonl / 已完成页面操作”。

## 必读

1. `doc/coding_style_guide.md`
2. 本文件
3. 抓包服务异常时读取 `capture/README.md`

## 流程

1. 检查是否需要重启抓包服务。
2. 未运行时执行 `tools/check_capture_server.py`，必要时启动 `capture/start.bat`。
3. 告知用户代理信息：`127.0.0.1:12138`。
4. 用户完成页面操作后，读取 `runtime/latest.jsonl`。
5. 运行 `tools/scan_page_api.py` 刷新 `tools/page_api_index.sqlite3`。
6. 运行 `tools/match_captures.py` 生成 `runtime/capture_selection.md`。
7. 等待用户确认勾选；没有用户确认，不得生成代码。
8. 读取勾选接口的请求、响应、顺序和依赖关系。
9. 按业务场景设计用例，避免机械“一接口一用例”。
10. 对新接口生成接口方法；对已实现接口优先复用。
11. 生成 pytest 用例，使用 Allure 标注和步骤。
12. 运行 pytest 验证并生成 Allure 结果。

## 设计要求

- 静态资源由抓包脚本固定过滤，二进制响应默认不入例。
- `capture/allowed_prefixes.txt` 为空时不做允许前缀限制；有内容时，每行一个允许前缀，仅保留匹配前缀的请求。
- `capture/blocked_prefixes.txt` 为空时不做禁止前缀限制；有内容时，每行一个禁止前缀，排除匹配前缀的请求。
- 过滤优先级固定为：先应用 `allowed_prefixes.txt`，再应用 `blocked_prefixes.txt`。
- 登录、登出、埋点、心跳等接口不做内置路径判断，需要时通过 `capture/blocked_prefixes.txt` 排除。
- Cookie、Authorization、token 不硬编码；通过 `config.default_headers`、`config.default_cookies` 或 fixture 注入。
- 业务断言必须基于真实响应体。
- `@allure.feature` 可由用户指定，也可由抓包接口路径和业务语义总结生成。
- 生成接口方法时使用 `BaseAPI`、`self.build_url(url)`、`self.get_base_request()`。
