# -*- coding: utf-8 -*-
# Create Date:2026/6/2
# Author: dengwanpeng

import allure

from test_case.page_api.public.base_api import BaseAPI


class DoubanAPI(BaseAPI):

    @allure.step("接口：访问豆瓣电影首页")
    def movie_homepage(self, status_code=200, **kwargs):
        """访问豆瓣电影首页"""
        # Author: AI
        # Create Date: 2026-06-04
        # IsAI: True
        url = "/"
        error_msg = kwargs.pop("error_msg", "访问豆瓣电影首页")
        return self.get(url, status_code=status_code, return_response=True, error_msg=error_msg, **kwargs)

    @allure.step("接口：访问即将上映页面")
    def movie_coming_soon(self, city="chengdu", status_code=200, **kwargs):
        """访问即将上映页面"""
        # Author: AI
        # Create Date: 2026-06-04
        # IsAI: True
        url = f"/cinema/later/{city}/"
        error_msg = kwargs.pop("error_msg", "访问即将上映页面")
        return self.get(url, status_code=status_code, return_response=True, error_msg=error_msg, **kwargs)

    @allure.step("接口：访问电影详情页")
    def movie_subject_detail(self, subject_id="1432146", status_code=200, **kwargs):
        """访问电影详情页"""
        # Author: AI
        # Create Date: 2026-06-04
        # IsAI: True
        url = f"/subject/{subject_id}/"
        error_msg = kwargs.pop("error_msg", "访问电影详情页")
        return self.get(url, status_code=status_code, return_response=True, error_msg=error_msg, **kwargs)
