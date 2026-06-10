# 高频问题经验

## 导入路径

- 优先从项目根运行：`python runpytest.py`。
- 直接 pytest 时优先在项目根执行：`python -m pytest test_case/...`。
- 出现 `ModuleNotFoundError` 时，先确认当前目录是项目根，且导入路径符合 `test_case/page_api/...`。

## base_url

- `config.base_url` 必须包含协议和域名，例如 `https://www.gbif.org`。
- 不要使用额外 `is_https` 字段，协议由 `base_url` 决定。

## 认证信息

- 不硬编码真实 Cookie、token、Authorization。
- 放到 `config.default_headers` / `config.default_cookies`，或通过 fixture 临时注入。

## 返回结构

- 接口方法默认返回完整 `res.json()`。
- 业务断言写在 pytest 用例中。
- 对 HTML、文本、空响应、重定向等非 JSON 场景，接口方法可返回 `res.text` 或原始 `res`，但必须按真实响应写断言。

## Allure

- Python 依赖是 `allure-pytest`。
- 生成 HTML 报告还需要本机安装 Allure CLI。

## Windows 与中文路径

- Windows + 中文路径下尽量用仓库相对路径。
- 文件编辑优先用 `apply_patch`，补丁要小。
- 运行命令时显式设置工作目录，避免相对导入误判。
