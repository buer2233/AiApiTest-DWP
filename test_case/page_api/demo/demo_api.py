import allure

from test_case.page_api.public.base_api import BaseAPI


class DemoAPI(BaseAPI):
    @allure.step("接口：示例 GET 请求")
    def demo_get(self, status_code=200, **kwargs):
        """示例 GET 请求"""
        # Author: AI
        # Create Date: 2026-06-02
        # IsAI: True
        url = "/"
        payload = {}
        error_msg = kwargs.pop("error_msg", "示例 GET 请求")
        payload.update(kwargs)
        res = self.get_base_request().request("GET", self.build_url(url), params=payload)
        assert res.status_code == status_code, (
            f"{error_msg},接口<{self.build_url(url)}>报错-{res.status_code},"
            f"reason:{res.reason},text:{res.text}"
        )
        return res.json()
