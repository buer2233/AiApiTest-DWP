# 接口编码风格指南

AI 在编写任何接口方法或用例代码前必须先读取本文件并遵守。

## 编写前必检清单

1. 风格对齐：接口方法遵守本文件模板；pytest 用例对齐目标文件插入点上下文。
2. 接口查重：优先查 `tools/page_api_index.sqlite3`，以 URL `pure_path` + HTTP method 判断是否已覆盖。
3. 真实返回：抓包 / cURL 场景先看真实 response body；没有真实返回时不凭空补业务断言。
4. 编码校验：写入后重新读取确认新增片段存在、中文正常、`python -m py_compile` 通过。
5. 查找已实现接口方法时，优先查 `tools/page_api_index.sqlite3` 的 `api_methods` 表，而不是全仓库 grep。

## 接口方法编写规范

接口方法放在 `test_case/page_api/` 下，必须先于 pytest 用例编写。

```python
import allure

from test_case.page_api.public.base_api import BaseAPI


class ExampleAPI(BaseAPI):
    @allure.step("接口：查询示例数据")
    def example_query(self, status_code=200, **kwargs):
        """查询示例数据"""
        # Author: AI
        # Create Date: YYYY-MM-DD
        # IsAI: True
        url = "/api/example/query"
        payload = {}
        error_msg = kwargs.pop("error_msg", "查询示例数据")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：提交示例数据")
    def example_create(self, status_code=200, **kwargs):
        """提交示例数据"""
        # Author: AI
        # Create Date: YYYY-MM-DD
        # IsAI: True
        url = "/api/example/create"
        payload = {}
        error_msg = kwargs.pop("error_msg", "提交示例数据")
        payload.update(kwargs)
        return self.post(url, status_code=status_code, json=payload, error_msg=error_msg)
```

规则：

- 方法上方必须加 `@allure.step("接口：xxx")`。
- 接口方法优先直接调用 `BaseAPI` 封装的 `self.get(...)`、`self.post(...)`、`self.put(...)`、`self.delete(...)`，不要直接调用 `self.get_base_request().request(...)`。
- 只通过封装方法传入并断言 HTTP `status_code`，不在接口方法里断言业务 `code`。
- 默认返回封装方法解析后的 JSON；非 JSON 或重定向响应传入 `return_response=True` 获取原始 `res`，再按真实场景返回 `res.text` 或原始 `res`，并在用例中处理。
- 请求 URL 优先传相对路径给封装方法，由 `BaseAPI` 内部执行 `self.build_url(url)`；`config.base_url` 必须包含协议。
- headers、cookies、token 等通过 `BaseAPI`、`config.default_headers`、`config.default_cookies` 或 fixture 注入，不硬编码敏感值。
- payload 默认值直接写在 `payload` 中，再 `payload.update(kwargs)`。
- `error_msg = kwargs.pop("error_msg", "中文说明")` 传给封装方法，用于断言失败提示。

## 方法命名

- 使用 `snake_case`。
- 优先体现模块 + 资源 + 动作。
- 不把整条中文标题拼进方法名。
- 忽略无意义层级：`api`、`web`、`common` 等。
- 示例：`movie_subject_detail`、`movie_search_list`、`comment_create`。

## pytest 用例模板

```python
import allure

import config
from test_case.page_api.example.example_api import ExampleAPI


@allure.epic(f"{config.get_website_name()}-接口自动化")
@allure.feature("示例接口")
class TestExampleAPI:
    def setup_method(self):
        self.example_api = ExampleAPI()

    @allure.story("查询示例数据")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_example_query(self):
        """
        查询示例数据
        1.调用查询示例接口
        2.断言接口返回数据
        """
        with allure.step("1.调用查询示例接口1"):
            response1 = self.example_api.example_query1()
            assert response1, f"调用查询示例接口1接口报错:{response1}"
            
        with allure.step("2.调用查询示例接口2"):
            response2 = self.example_api.example_query2()
            assert response2, f"调用查询示例接口2接口报错:{response2}"
```

规则：

- 类级：`@allure.epic(f"{config.get_website_name()}-接口自动化")`。
- 类级：`@allure.feature("模块名")`，可由用户指定或由抓包总结。
- 方法级：`@allure.story("[用例名]")`。
- 方法级：默认 `@allure.severity(allure.severity_level.CRITICAL)`。
- 步骤级：使用 `with allure.step("1.xxx"):`。
- docstring 保留完整中文标题和步骤列表。

## 取值与断言

- 多层取值优先用 `self.xxx_api.get_value(data, ["data", 0, "fields"])`。
- 单层取值优先用 `.get()`。
- 业务断言写在 pytest 用例中，不写在接口方法中。
- 断言必须带清晰失败提示并包含关键响应信息。
- 非 JSON 返回按实际文本、状态码、响应头或跳转地址断言，不使用 `.get()`。
