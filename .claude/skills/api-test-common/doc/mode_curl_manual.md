# 方式3：cURL 手工

适用：用户选择新增方式3，或消息中已粘贴 `curl ...`、请求信息和响应体。

## 必读

1. `doc/coding_style_guide.md`
2. 本文件

## 流程

1. 解析 cURL 的 method、url、headers、cookies、query、body。
2. 识别敏感 headers：Cookie、Authorization、token、session 等不硬编码。
3. 将完整 URL 拆分为 `config.base_url` + path；若域名与当前 `config.base_url` 不一致，提醒用户确认。
4. 按 `pure_path` + method 查 `tools/page_api_index.sqlite3`，命中则复用已有方法。
5. 未命中且新增门禁允许新增接口时，根据请求生成接口方法。
6. 根据真实响应体设计 pytest 断言。
7. 生成 Allure 标注和步骤。
8. 执行 pytest 验证。

## 规则

- cURL 中的敏感值默认抽象为配置、fixture 或方法参数。
- GET 请求使用 `params=payload`；JSON POST 使用 `json=payload`；表单使用 `data=payload`。
- 文件上传可使用 `files=`，但不要提交真实文件或敏感文件。
- 接口方法只断言 HTTP 状态码并默认返回 `res.json()`；响应体断言放在 pytest 用例。
