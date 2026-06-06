import allure
import pytest

import config
from test_case.page_api.demo.demo_api import DemoAPI


@allure.epic(f"{config.get_website_name()}-接口自动化")
@allure.feature("通用接口示例")
class TestDemoAPI:
    """通用接口示例"""

    def setup_method(self):
        self.demo_api = DemoAPI()

    @pytest.mark.skip(reason="示例占位用例，真实用例请通过抓包、参考已有用例或 cURL 生成")
    @allure.story("示例 GET 请求")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_demo_get(self):
        """
        示例 GET 请求
        1.调用示例接口方法
        2.断言接口返回包含 JSON 数据
        """
        with allure.step("1.调用示例接口方法"):
            response = self.demo_api.demo_get()

        with allure.step("2.断言接口返回包含 JSON 数据"):
            assert isinstance(response, dict)
