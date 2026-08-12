# api-test/docs/api_test_case_spec.md

本文件是 E9 接口自动化测试框架的**用例与接口方法编写规范**。
当新增接口模块、编写测试用例或审查代码时读取本文件。

---

## 一、接口封装类编码规范

### 1.1 目录与文件

```
page_api/{模块名}_api/                   # 目录名: 模块名_api
├── __init__.py
├── {模块名}_api.py                       # 主接口文件（或 {模块名}_base_api.py）
└── {模块名}_{子模块名}_api.py                     # 可选：子模块文件（最多一个）
```

**命名规则：**
- 目录名：`模块名_api`（如 `login_api`、`workflow_api`、`portal_api`）
- 主文件：`模块名_api.py` 或 `模块名_base_api.py`（如 `login_api.py`、`workflow_base_api.py`）
- 类名：`{Name}API`（PascalCase），由模块名推导（如 `LoginAPI`、`WorkflowAPI`、`PortalAPI`）

### 1.2 文件结构：两大类方法

```python
# -*- coding: utf-8 -*-
"""E9 {模块名}模块接口封装。"""

import allure
from page_api.public.base_api import BaseAPI


class {Name}API(BaseAPI):
    """E9 {模块名}接口。"""

    # --------------------------------通用方法---------------------------------------

    # 模块特有的辅助方法：数据构造、表单参数组装等。
    # 跨模块公用的 `_browser_headers()` 和 `_timestamp()` 已由 BaseAPI 提供。

    def _build_form_data(self, **kwargs):
        """构造公共表单参数。"""
        ...

    # --------------------------------接口方法---------------------------------------

    @allure.step("接口：获取待办基础信息")
    def get_doing_base_info(self, status_code=200, **kwargs):
        ...
```

### 1.3 接口方法编写规范

每个接口方法遵循以下模式（参考 `page_api/workflow_api/workflow_base_api.py`）：

```python
@allure.step("接口：功能描述")
def method_name(self, param1, status_code=200, **kwargs):
    """方法功能说明。"""
    # Author: 作者名
    # Create Date: 创建日期
    # IsAI: True/False
    url = "/api/path/to/endpoint"          # ★ URL 单独提取为变量
    error_msg = kwargs.pop("error_msg", "中文错误说明")
    # ... 构造请求参数 ...
    return self.post(                      # 或 self.get / self.put / self.delete
        url,
        status_code=status_code,
        data=form_data,                    # POST 表单用 data
        headers=self._browser_headers(form=True, origin=True),
        error_msg=error_msg,
    )
```

**要点：**
- `url` 变量单独提取到方法体顶部，方便 grep 扫描
- 三行元数据注释 `# Author:` / `# Create Date:` / `# IsAI:` 必须保留
- 内部顺序：`url` → `error_msg` → 构造参数 → 调用 `self.get/post/put/delete`
- `status_code` 参数默认 200，传入 `status_code=0` 跳过 HTTP 断言
- `error_msg` 通过 `kwargs.pop` 取出，避免传入 requests
- 敏感参数通过 `**kwargs` 传入，不在方法签名中显式声明
- 请求头统一用 `self._browser_headers(form=..., origin=...)`（BaseAPI 提供）
- 不要在接口封装层做业务断言（如 `assert response["code"] == 0`）

### 1.4 通用方法规范

- 跨模块公用的 `_browser_headers()`、`_timestamp()` 已在 `BaseAPI` 中定义，子类直接继承
- 模块特有的辅助方法（如 `_build_form_data`）保留在子类的 `# ----通用方法----` 区域
- 使用 `@staticmethod` 或实例方法视是否需要访问 `self.base_url` 而定

---

## 二、测试用例编码规范

### 2.1 目录与文件

```
test_case/test_{模块名}_case/             # 目录名: test_模块名_case
├── __init__.py
└── test_{模块名}_api.py                   # 测试文件
```

### 2.2 用例编写模板

参考 `test_case/test_workflow_case/test_workflow_base_case/test_workflow_base1_case.py`：

```python
# -*- coding: utf-8 -*-
"""E9 {模块名}接口自动化用例。"""

import allure
import pytest


@pytest.fixture(scope="class", autouse=True)
def _setup_class(login_admin, login_employee):
    """注入登录态，初始化各模块引用（class 级别，仅执行一次）。"""
    global api_admin, api_emp1
    api_admin = login_admin.{模块名}
    emp1 = login_employee("employee1")
    api_emp1 = emp1.{模块名}


@allure.epic("E9-接口自动化")
@allure.feature("E9 {模块名}接口")
class Test{模块名}API:
    """{模块名}接口测试。

    Author: dengwanpeng
    Create Date: 2026-08-12
    IsAI: True
    """

    def setup_class(self):
        self.api_admin = api_admin
        self.api_emp1 = api_emp1

    @allure.story("{场景描述}")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_{方法名}(self):
        """{用例描述}。"""
        with allure.step("1.步骤名称"):
            response = self.api_admin.{接口方法}()

            assert response.get("code") == 0, f"业务码异常: {response}"
```

### 2.3 编写要点

**Fixture 与初始化：**
- 用模块级 `@pytest.fixture(scope="class", autouse=True)` + `global` 变量 + `setup_class` 模式
- `login_admin` 自动注入管理员登录态，`login_employee("employee1")` 按需登录员工
- 通过 `login_admin.{模块名}` 命名空间获取接口实例，无需手动 import 或实例化

**Allure 标注：**
- 测试类：`@allure.epic("E9-接口自动化")` + `@allure.feature("E9 {模块名}接口")`
- 测试方法：`@allure.story("{场景描述}")` + `@allure.severity`
- 严重级别：`BLOCKER` > `CRITICAL` > `NORMAL` > `MINOR` > `TRIVIAL`

**断言：**
- 优先用 `.get()` 取值，避免 KeyError
- 失败信息包含关键上下文：`f"页面标题异常: {response}"`
- 覆盖**正常场景、边界场景、异常场景**三种类型
- 已实现的接口方法必须全部在用例中调用，不允许漏测

**元数据：**
- 测试类文档字符串和测试方法内均需包含 `# Author:` / `# Create Date:` / `# IsAI:` 三行

**测试账号：**
- 统一通过 `utils/common_function.py` 的 `load_account(role)` 读取
- 账号文件：`test_data/account.json`，环境变量 `E9_LOGINID` / `E9_USERPASSWORD` 优先

---

## 三、命名空间与模块发现

`login_admin.{模块名}` 按三级策略自动查找：

| 优先级 | 策略 | 示例 |
|--------|------|------|
| 1 | `page_api/{name}_api/{name}_api.py` | `login_admin.portal` → `page_api/portal_api/portal_api.py` → `PortalAPI` |
| 2 | 扫描 `page_api/*_api/{name}_api.py`（子模块） | `login_admin.reqlist` → `page_api/workflow_api/reqlist_api.py` |
| 3 | `page_api/{name}_api/{name}_base_api.py` | `login_admin.workflow` → `page_api/workflow_api/workflow_base_api.py` → `WorkflowAPI` |

新增模块时零配置——只要按规范创建目录和文件，命名空间自动生效。

---

## 四、通用编码规范

- Python 文件使用 `# -*- coding: utf-8 -*-` 头，注释使用简体中文
- `_browser_headers()` 和 `_timestamp()` 已由 `BaseAPI` 提供，子类无需重复定义
- 不在 `page_api/` 和 `test_case/` 中硬编码 IP 或域名，统一使用 `config.base_url`
- 运行产物写入 `runtime/`，报告产物写入 `report/`，不提交 Git