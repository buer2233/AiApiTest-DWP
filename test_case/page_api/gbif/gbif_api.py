# -*- coding: utf-8 -*-

import allure

from test_case.page_api.public.base_api import BaseAPI


class GbifAPI(BaseAPI):
    """GBIF API 接口封装"""

    # ==================== 物种搜索相关 ====================

    @allure.step("接口：物种搜索")
    def species_search(self, status_code=200, **kwargs):
        """按关键词搜索物种"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = "/api/species/search"
        payload = {}
        error_msg = kwargs.pop("error_msg", "物种搜索")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：物种名称列表")
    def species_names(self, status_code=200, **kwargs):
        """获取物种名称列表"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = "/api/species/names"
        payload = {}
        error_msg = kwargs.pop("error_msg", "物种名称列表")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    # ==================== 物种详情相关 ====================

    @allure.step("接口：获取物种名称")
    def species_name(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的名称"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/species/{taxon_key}/name"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种名称")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种俗名")
    def species_vernacular_name(self, taxon_key, **kwargs):
        """获取指定物种的俗名（可能返回204 No Content）"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/species/{taxon_key}/vernacularName"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种俗名")
        payload.update(kwargs)
        # 该接口可能返回 204 No Content，需要特殊处理
        resp = self.get(url, status_code=0, params=payload, error_msg=error_msg, return_response=True)
        if resp.status_code == 204:
            return None
        if resp.status_code == 200:
            return resp.json()
        # 其他状态码抛出断言错误
        assert False, (
            f"{error_msg},接口<{url}>异常-{resp.status_code},"
            f"reason:{resp.reason},text:{resp.text}"
        )

    @allure.step("接口：获取物种所有俗名")
    def species_vernacular_names(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的所有俗名列表"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/species/{taxon_key}/vernacularNames"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种所有俗名")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种处理信息")
    def species_treatments(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的处理信息"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/species/{taxon_key}/treatments"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种处理信息")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种组合信息")
    def species_combinations(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的组合信息"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/species/{taxon_key}/combinations"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种组合信息")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种清单数据集")
    def species_checklist_datasets(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的清单数据集"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/species/{taxon_key}/checklistdatasets"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种清单数据集")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种出现数据集")
    def species_occurrence_datasets(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的出现数据集"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/species/{taxon_key}/occurencedatasets"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种出现数据集")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    # ==================== 分类学相关 ====================

    @allure.step("接口：获取分类详情")
    def taxonomy_detail(self, dataset_key, taxon_key, status_code=200, **kwargs):
        """获取指定分类的详细信息"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/taxonomy/{dataset_key}/{taxon_key}"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取分类详情")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取父分类")
    def taxonomy_parents(self, dataset_key, taxon_key, status_code=200, **kwargs):
        """获取指定分类的父分类链"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/taxonomy/{dataset_key}/{taxon_key}/parents"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取父分类")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取子分类")
    def taxonomy_children(self, dataset_key, taxon_key, status_code=200, **kwargs):
        """获取指定分类的子分类列表"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/taxonomy/{dataset_key}/{taxon_key}/children"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取子分类")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取同义词")
    def taxonomy_synonyms(self, dataset_key, taxon_key, status_code=200, **kwargs):
        """获取指定分类的同义词列表"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/taxonomy/{dataset_key}/{taxon_key}/synonyms"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取同义词")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    # ==================== 外部关联 ====================

    @allure.step("接口：获取物种Wikidata信息")
    def species_wikidata(self, taxon_key, **kwargs):
        """获取指定物种的Wikidata信息（可能触发429限流）"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/api/wikidata/species/{taxon_key}"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种Wikidata信息")
        payload.update(kwargs)
        # 该接口可能触发 429 Too Many Requests 限流
        resp = self.get(url, status_code=0, params=payload, error_msg=error_msg, return_response=True)
        if resp.status_code == 429:
            return {"_rate_limited": True, "retry_after": resp.headers.get("Retry-After", "60")}
        if resp.status_code == 200:
            return resp.json()
        # 其他状态码抛出断言错误
        assert False, (
            f"{error_msg},接口<{url}>异常-{resp.status_code},"
            f"reason:{resp.reason},text:{resp.text}"
        )
