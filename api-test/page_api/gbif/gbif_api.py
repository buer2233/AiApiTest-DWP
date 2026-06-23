# -*- coding: utf-8 -*-

import allure

from page_api.public.base_api import BaseAPI


class GbifAPI(BaseAPI):
    """
    GBIF API 接口封装
    公开的可用于接口测试的网站：https://api.gbif.org
    """

    # ==================== 物种搜索相关 ====================

    @allure.step("接口：物种搜索")
    def species_search(self, status_code=200, **kwargs):
        """按关键词搜索物种"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = "/v1/species/search"
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
        url = "/v1/species/name_usage/search"
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
        url = f"/v1/species/{taxon_key}/name"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种名称")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种俗名")
    def species_vernacular_name(self, taxon_key, **kwargs):
        """获取指定物种的第一个俗名"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/v1/species/{taxon_key}/vernacularNames"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种俗名")
        payload.update(kwargs)
        payload.setdefault("limit", 1)
        data = self.get(url, status_code=200, params=payload, error_msg=error_msg)
        return data.get("results", [None])[0] if data.get("results") else None

    @allure.step("接口：获取物种所有俗名")
    def species_vernacular_names(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的所有俗名列表"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/v1/species/{taxon_key}/vernacularNames"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取物种所有俗名")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种处理信息")
    def species_treatments(self, taxon_key, status_code=200, **kwargs):
        """获取指定物种的描述信息"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = f"/v1/species/{taxon_key}/descriptions"
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
        url = f"/v1/species/{taxon_key}/combinations"
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
        url = "/v1/dataset/search"
        payload = {"type": "CHECKLIST", "taxon_key": taxon_key}
        error_msg = kwargs.pop("error_msg", "获取物种清单数据集")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    @allure.step("接口：获取物种出现数据集")
    def species_occurrence_datasets(self, taxon_key, status_code=200, **kwargs):
        """按出现记录分面获取指定物种关联的数据集"""
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        url = "/v1/occurrence/search"
        payload = {"taxon_key": taxon_key, "facet": "datasetKey", "limit": 0}
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
        url = f"/v1/species/{taxon_key}"
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
        url = f"/v1/species/{taxon_key}/parents"
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
        url = f"/v1/species/{taxon_key}/children"
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
        url = f"/v1/species/{taxon_key}/synonyms"
        payload = {}
        error_msg = kwargs.pop("error_msg", "获取同义词")
        payload.update(kwargs)
        return self.get(url, status_code=status_code, params=payload, error_msg=error_msg)

    # ==================== 外部关联 ====================

    @allure.step("接口：获取物种Wikidata信息")
    def species_wikidata(self, taxon_key, **kwargs):
        """获取指定物种的Wikidata信息。

        GBIF 公开 v1 API 未提供网站内部 Wikidata 接口的稳定等价路径。
        """
        # Author: AI
        # Create Date: 2026-06-10
        # IsAI: True
        return {
            "_unavailable": True,
            "taxonKey": taxon_key,
            "reason": "GBIF public v1 API has no stable Wikidata endpoint.",
        }
