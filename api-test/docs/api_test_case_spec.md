# api-test/docs/api_test_case_spec.md

本文件是 E9 接口自动化测试框架的**用例与接口方法编写规范**，包含完整的新增用例指南、代码模板和编码规范。
当需要新增接口模块、编写测试用例或审查代码风格时读取本文件。

---

## 一、新增接口自动化用例 — 完整指南

以下以新增一个"公告模块"为例，展示完整的接入流程。

### 步骤 1：创建接口封装类

在 `page_api/` 下创建模块目录和接口文件：

```text
page_api/announce_api/           # 按规范命名: 模块名_api
├── __init__.py                  # 空文件即可
└── announce_api.py              # 接口封装类
```

`announce_api.py` 模板：

```python
# -*- coding: utf-8 -*-
"""E9 公告模块接口封装。"""

import allure
from page_api.public.base_api import BaseAPI


class AnnounceAPI(BaseAPI):
    """E9 公告相关接口。"""

    @allure.step("接口：获取公告列表")
    def get_announce_list(self, page=1, limit=10, status_code=200, **kwargs):
        """获取公告分页列表。"""
        error_msg = kwargs.pop("error_msg", "获取公告列表")
        params = {"page": page, "limit": limit}
        params.update(kwargs)
        return self.get(
            "/api/announce/list",
            status_code=status_code,
            params=params,
            error_msg=error_msg,
        )

    @allure.step("接口：获取公告详情")
    def get_announce_detail(self, announce_id, status_code=200, **kwargs):
        """根据 ID 获取公告详情。"""
        error_msg = kwargs.pop("error_msg", "获取公告详情")
        return self.get(
            f"/api/announce/detail/{announce_id}",
            status_code=status_code,
            error_msg=error_msg,
        )
```

**编写要点：**
- `@allure.step("接口：...")` 装饰器让每个接口调用在 Allure 报告中显示为独立步骤。
- `error_msg` 参数用于断言失败时提供中文错误说明，通过 `kwargs.pop` 取出避免传入 requests。
- 每个方法固定 `status_code` 参数，默认 200，传入 `status_code=0` 可跳过状态码断言。
- URL 路径写相对路径，`BaseAPI.build_url()` 会自动拼接 `base_url`。

### 步骤 2：创建测试用例

在 `test_case/` 下创建用例目录和测试文件：

```text
test_case/test_announce_case/    # 按规范命名: test_模块名_case
├── __init__.py                  # 空文件即可
└── test_announce_api.py         # 测试用例
```

`test_announce_api.py` 模板：

```python
# -*- coding: utf-8 -*-
"""E9 公告模块接口自动化用例。"""

import allure
import pytest
from page_api.announce_api.announce_api import AnnounceAPI


@allure.epic("E9-接口自动化")
@allure.feature("E9 公告接口")
class TestAnnounceAPI:
    """公告接口测试。"""

    @allure.story("获取公告列表-正常场景")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_announce_list(self, base_url):
        """验证公告列表接口正常返回分页数据。"""
        api = AnnounceAPI(base_url=base_url)

        response = api.get_announce_list(page=1, limit=10)

        # 业务断言：根据实际接口响应结构调整
        assert response.get("code") == 0, f"业务码异常: {response}"
        data = response.get("data", {})
        assert isinstance(data.get("list"), list), f"列表字段异常: {data}"

    @allure.story("获取公告列表-边界场景")
    def test_get_announce_list_empty_page(self, base_url):
        """验证超出总页数时返回空列表。"""
        api = AnnounceAPI(base_url=base_url)

        response = api.get_announce_list(page=9999, limit=10)

        assert response.get("code") == 0
        assert response.get("data", {}).get("list") == []

    @allure.story("获取公告详情-异常场景")
    def test_get_announce_detail_not_found(self, base_url):
        """验证不存在的公告 ID 返回错误。"""
        api = AnnounceAPI(base_url=base_url)

        response = api.get_announce_detail(announce_id=0, status_code=0)

        # 不存在的资源可能返回非 200 状态码，跳过 HTTP 断言后自行判断
        assert response.status_code in (200, 404, 500)
```

**编写要点：**
- 使用 `@allure.epic` / `@allure.feature` / `@allure.story` / `@allure.severity` 构建 Allure 报告层级。
- 测试方法接收 `base_url` fixture（由 `conftest.py` 提供），传给接口类实例化。
- 每个测试方法独立创建 `AnnounceAPI` 实例，保证 Session 隔离。
- 覆盖**正常场景、边界场景、异常场景**三种类型。
- 业务断言用 `assert response.get("code") == 0` 而非直接 `response["code"]`，避免 KeyError。

### 步骤 3：注册模块信息

编辑 `utils/package_module.yaml`，新增模块条目：

```yaml
test_announce_case:
  module_name: 公告模块
  module_dev: 张三
  module_test: 李四
```

### 步骤 4：运行验证

```powershell
# 执行新模块用例
python runpytest.py --case-path test_case/test_announce_case --clean

# 生成并查看 Allure 报告
python runpytest.py --case-path test_case/test_announce_case --open-report
```

---

## 二、接口封装类编码规范

### 2.1 文件结构：两大类方法

每个接口封装文件按方法性质分为两个区域，使用注释分隔线明确区分：

```python
class SomeAPI(BaseAPI):
    """模块接口封装。"""

    # --------------------------------通用方法---------------------------------------

    # 不包含接口请求的辅助方法：时间戳生成、数据过滤、headers 构造等

    # --------------------------------接口方法---------------------------------------

    # 包含接口请求的方法：每个方法对应一个后端接口
```

### 2.2 接口方法编写规范

每个接口方法必须遵循以下模式（参考 `page_api/login_api/login_api.py` 的 `get_os_info`）：

```python
@allure.step("接口：功能描述")
def method_name(self, param1, param2, status_code=200, **kwargs):
    """方法功能说明。"""
    # Author: 作者名
    # Create Date: 创建日期
    # IsAI: True/False
    url = "/api/path/to/endpoint"          # ★ URL 单独提取为变量，方便后续扫描和分析
    error_msg = kwargs.pop("error_msg", "中文错误说明")
    # ... 构造请求参数 ...
    return self.get(                       # 或 self.post / self.put / self.delete
        url,                               # ★ 使用 url 变量，不硬编码字符串
        status_code=status_code,
        params=params,                     # GET 请求用 params
        # data=form_data,                  # POST 表单用 data
        # json=body,                       # POST JSON 用 json
        headers=self._browser_headers(),
        error_msg=error_msg,
    )
```

**要点：**
- `url` 变量必须单独提取到方法体顶部，方便 grep/扫描工具快速定位所有接口路径。
- 每个接口方法必须包含 `# Author:`、`# Create Date:`、`# IsAI:` 三行元数据注释。
- 接口方法内部按顺序：`url` → `error_msg` → 构造参数 → 调用 `self.get/post/put/delete`。

### 2.3 通用方法规范

- 不包含接口请求的辅助方法放在 `# ----通用方法----` 区域。
- 包括但不限于：时间戳生成、响应字段过滤、headers 构造、数据转换等。
- 使用 `@staticmethod` 或实例方法视是否需要访问 `self.base_url` 而定。

### 2.4 目录与文件

- 目录命名：`page_api/模块名_api/`，如 `page_api/login_api/`、`page_api/announce_api/`
- 主文件命名：`模块名_api.py`，如 `login_api.py`、`announce_api.py`
- 每个模块目录必须包含 `__init__.py`（可为空文件）

### 2.5 类与方法

- 继承 `page_api.public.base_api.BaseAPI`，不要自己创建 Session。
- 类名使用 `模块名API`（PascalCase），如 `LoginAPI`、`AnnounceAPI`。
- 使用 `self.get()` / `self.post()` / `self.put()` / `self.delete()` 发送请求，不直接调用 `self.request()`。
- 每个接口方法加 `@allure.step("接口：...")` 装饰器。
- 方法签名中保留 `status_code` 参数（默认 200），`status_code=0` 表示跳过 HTTP 状态码断言。
- 敏感参数（如 password）通过 `**kwargs` 传入，不在方法签名中显式声明。
- 如果接口需要特定的 headers（如 Content-Type、Referer），在方法内构造后通过 `headers=` 传入。

### 2.6 返回值

- 默认返回 `response.json()`（dict 或 list），由 `BaseAPI.request()` 自动处理。
- 需要返回原始 Response 对象时，传入 `return_response=True`。
- 不要手动解析 JSON 或处理 Cookie，这些由 BaseAPI 统一管理。

### 2.7 错误处理

- `error_msg` 参数用于断言失败时提供中文错误说明，通过 `kwargs.pop("error_msg", "默认值")` 取出。
- 不要在接口封装层做业务断言（如 `assert response["code"] == 0`），业务断言应放在测试用例层。

---

## 三、测试用例编码规范

### 3.1 目录与文件

- 目录命名：`test_case/test_模块名_case/`，如 `test_case/test_login_case/`
- 测试文件命名：`test_模块名_api.py`，如 `test_login_api.py`
- 每个用例目录必须包含 `__init__.py`（可为空文件）

### 3.2 类与方法

- 测试类使用 `@allure.epic("E9-接口自动化")` 和 `@allure.feature("E9 模块名接口")`。
- 测试类名使用 `Test模块名API`，如 `TestE9LoginAPI`、`TestAnnounceAPI`。
- 测试类文档字符串必须包含三行元数据注释：
  ```python
  class TestSomeAPI:
      """模块接口测试。

      Author: dengwanpeng
      Create Date: 2026-08-11
      IsAI: True
      """
  ```
- 测试方法名以 `test_` 开头，配合 `@allure.story` 描述测试场景。
- 使用 `@allure.severity` 标注严重级别：`BLOCKER` > `CRITICAL` > `NORMAL` > `MINOR` > `TRIVIAL`。
- 每个测试方法至少覆盖一个断言点，避免一个方法测所有逻辑。

### 3.3 依赖与数据

- 使用 `base_url` fixture 实例化接口类，不要硬编码 URL。
- 每个测试方法独立创建接口类实例，保证 Session 隔离。
- **测试账号**：统一通过 `utils/common_function.py` 的 `load_account(role)` 读取。
  - `load_account("admin")` 获取管理员账号，用于大多数用例。
  - `load_account("employee1")` 获取普通成员账号，用于流程/权限类用例。
  - 账号文件位于 `test_data/account.json`，环境变量 `E9_LOGINID` / `E9_USERPASSWORD` 优先。
- 公用测试数据放在 `test_data/` 目录，模块私有的测试数据放在模块目录内。

### 3.4 断言

- 业务断言用 `assert response.get("code") == 0` 而非直接 `response["code"]`，避免 KeyError。
- 断言失败信息要包含关键上下文（如响应 JSON），方便排查：`f"业务码异常: {response}"`。
- 覆盖**正常场景、边界场景、异常场景**三种类型。

### 3.5 用例模板快速参考

```python
# -*- coding: utf-8 -*-
"""E9 {模块名}接口自动化用例。"""

import allure
import pytest
from page_api.{模块名}_api.{模块名}_api import {模块名}API
from utils.common_function import load_account


@allure.epic("E9-接口自动化")
@allure.feature("E9 {模块名}接口")
class Test{模块名}API:
    """{模块名}接口测试。"""

    def setup_method(self):
        self.account = load_account("admin")

    @allure.story("{场景描述}")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_{方法名}(self, base_url):
        """{用例描述}。"""
        api = {模块名}API(base_url=base_url)

        response = api.{接口方法}()

        assert response.get("code") == 0, f"业务码异常: {response}"
```

---

## 四、通用编码规范

- 多层取值优先用 `BaseAPI.get_value(data, list_key)`，单层取值优先用 `.get()`。
- Python 文件使用 `# -*- coding: utf-8 -*-` 头。
- 注释使用简体中文，保持与现有代码风格一致。
- 新增执行能力优先放在 `tools/`，供 Jenkins 和后端复用。
- 运行产物写入 `runtime/`，报告产物写入 `report/`，不要提交。
- 不在 `page_api/` 和 `test_case/` 中硬编码 IP 地址或域名，统一使用 `config.base_url` 或 `base_url` fixture。