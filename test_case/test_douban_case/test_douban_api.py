# -*- coding: utf-8 -*-
# Create Date:2026/6/2
# Author: dengwanpeng

import allure

import config
from test_case.page_api.douban.douban_api import DoubanAPI


@allure.epic(f"{config.get_website_name()}-接口自动化")
@allure.feature("豆瓣电影页面")
class TestDoubanAPI:
    """豆瓣电影页面"""

    def setup_method(self):
        self.douban_api = DoubanAPI()

    @allure.story("豆瓣电影首页-冒烟用例")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_movie_homepage(self):
        """
        豆瓣电影首页-冒烟用例
        1.访问豆瓣电影首页
        2.断言页面可访问且包含关键内容
        """
        with allure.step("1.访问豆瓣电影首页"):
            response = self.douban_api.movie_homepage()
            assert response is not None, "访问豆瓣电影首页失败，响应为空"

        with allure.step("2.断言页面可访问且包含关键内容"):
            assert response.status_code == 200, f"首页状态码异常：{response.status_code}"
            assert "豆瓣" in response.text, "首页未包含'豆瓣'关键字"
            assert "电影" in response.text, "首页未包含'电影'关键字"

    @allure.story("即将上映页面-冒烟用例")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_movie_coming_soon(self):
        """
        即将上映页面-冒烟用例
        1.访问即将上映页面（成都）
        2.断言页面可访问且包含关键内容
        """
        with allure.step("1.访问即将上映页面"):
            response = self.douban_api.movie_coming_soon()
            assert response is not None, "访问即将上映页面失败，响应为空"

        with allure.step("2.断言页面可访问且包含关键内容"):
            assert response.status_code == 200, f"即将上映页面状态码异常：{response.status_code}"
            assert "即将上映" in response.text, "即将上映页面未包含'即将上映'关键字"

    @allure.story("电影详情页-冒烟用例")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_movie_subject_detail(self):
        """
        电影详情页-冒烟用例
        1.访问电影详情页（肖申克的救赎）
        2.断言页面可访问且包含豆瓣相关标识
        """
        with allure.step("1.访问电影详情页"):
            response = self.douban_api.movie_subject_detail()
            assert response is not None, "访问电影详情页失败，响应为空"

        with allure.step("2.断言页面可访问且包含豆瓣相关标识"):
            assert response.status_code == 200, f"电影详情页状态码异常：{response.status_code}"
            # 豆瓣可能触发反爬虫验证，返回验证页面或详情页
            assert "豆瓣" in response.text, "页面未包含'豆瓣'关键字"
