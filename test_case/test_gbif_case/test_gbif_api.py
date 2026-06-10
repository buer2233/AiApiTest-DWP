# -*- coding: utf-8 -*-

import allure
import config
from test_case.page_api.gbif.gbif_api import GbifAPI


@allure.epic(f"{config.get_website_name()}-接口自动化")
@allure.feature("GBIF物种数据接口")
class TestGbifAPI:
    """GBIF API 接口测试"""

    def setup_class(self):
        self.gbif_api = GbifAPI()
        # 使用抓包中的测试数据：taxon_key=35 (Bryophyta)
        self.taxon_key = 35
        self.dataset_key = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"

    # ==================== 物种搜索相关 ====================

    @allure.story("按关键词搜索物种")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_species_search_by_keyword(self):
        """
        按关键词搜索物种
        1.调用物种搜索接口，搜索关键词"Plantae"
        2.断言返回结果包含物种列表
        """
        with allure.step("1.调用物种搜索接口"):
            response = self.gbif_api.species_search(q="Plantae", limit=10)
            assert response, f"调用物种搜索接口报错:{response}"

        with allure.step("2.断言返回结果结构"):
            assert "results" in response, f"响应缺少results字段:{response}"
            assert "count" in response, f"响应缺少count字段:{response}"
            assert response["count"] > 0, f"搜索结果数量应大于0，实际:{response['count']}"

        with allure.step("3.断言结果详情"):
            results = response["results"]
            assert len(results) > 0, "搜索结果列表不应为空"
            first_result = results[0]
            assert "key" in first_result, f"结果缺少key字段:{first_result}"
            assert "scientificName" in first_result, f"结果缺少scientificName字段:{first_result}"

    @allure.story("物种搜索分页查询")
    @allure.severity(allure.severity_level.NORMAL)
    def test_species_search_pagination(self):
        """
        物种搜索分页查询
        1.调用物种搜索接口，设置offset和limit
        2.断言分页参数生效
        """
        with allure.step("1.调用分页搜索接口"):
            response = self.gbif_api.species_search(q="Plantae", limit=5, offset=0)
            assert response, f"调用物种搜索接口报错:{response}"

        with allure.step("2.断言分页结果"):
            assert response.get("limit") == 5, f"limit应为5，实际:{response.get('limit')}"
            assert response.get("offset") == 0, f"offset应为0，实际:{response.get('offset')}"
            assert len(response.get("results", [])) <= 5, "返回结果数不应超过limit"

    # ==================== 物种详情相关 ====================

    @allure.story("获取物种名称")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_species_name(self):
        """
        获取物种名称
        1.调用获取物种名称接口
        2.断言返回正确的物种名称
        """
        with allure.step("1.调用获取物种名称接口"):
            response = self.gbif_api.species_name(self.taxon_key)
            assert response, f"调用获取物种名称接口报错:{response}"

        with allure.step("2.断言返回结果"):
            assert "n" in response, f"响应缺少n字段:{response}"
            assert response["n"] == "Bryophyta", f"物种名称应为Bryophyta，实际:{response['n']}"

    @allure.story("获取物种俗名")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_species_vernacular_name(self):
        """
        获取物种俗名
        1.调用获取物种俗名接口
        2.断言返回俗名信息（可能返回204 No Content）
        """
        with allure.step("1.调用获取物种俗名接口"):
            response = self.gbif_api.species_vernacular_name(self.taxon_key)

        with allure.step("2.断言返回结果"):
            # 该接口可能返回 None（204 No Content），这是正常情况
            if response is not None:
                assert "vernacularName" in response, f"响应缺少vernacularName字段:{response}"
                assert "language" in response, f"响应缺少language字段:{response}"
                assert response.get("taxonKey") == self.taxon_key, \
                    f"taxonKey应为{self.taxon_key}，实际:{response.get('taxonKey')}"
                allure.attach(f"俗名: {response.get('vernacularName')}", name="物种俗名")
            else:
                allure.attach("接口返回204 No Content，该物种无单独俗名数据", name="响应状态")

    @allure.story("获取物种所有俗名列表")
    @allure.severity(allure.severity_level.NORMAL)
    def test_species_vernacular_names(self):
        """
        获取物种所有俗名列表
        1.调用获取所有俗名接口
        2.断言返回俗名列表
        """
        with allure.step("1.调用获取所有俗名接口"):
            response = self.gbif_api.species_vernacular_names(self.taxon_key)
            assert response, f"调用获取所有俗名接口报错:{response}"

        with allure.step("2.断言返回结果"):
            assert "count" in response, f"响应缺少count字段:{response}"
            assert "results" in response, f"响应缺少results字段:{response}"
            assert response["count"] > 0, f"俗名数量应大于0，实际:{response['count']}"

        with allure.step("3.断言俗名详情"):
            first_vernacular = response["results"][0]
            assert "vernacularName" in first_vernacular, f"俗名缺少vernacularName字段:{first_vernacular}"
            assert "language" in first_vernacular, f"俗名缺少language字段:{first_vernacular}"

    @allure.story("获取物种处理信息")
    @allure.severity(allure.severity_level.NORMAL)
    def test_species_treatments(self):
        """
        获取物种处理信息
        1.调用获取处理信息接口
        2.断言返回处理信息（可能为空数组）
        """
        with allure.step("1.调用获取处理信息接口"):
            response = self.gbif_api.species_treatments(self.taxon_key)
            assert response is not None, "调用获取处理信息接口返回None"

        with allure.step("2.断言返回结果"):
            assert isinstance(response, list), f"响应应为数组类型，实际:{type(response)}"

    @allure.story("获取物种组合信息")
    @allure.severity(allure.severity_level.NORMAL)
    def test_species_combinations(self):
        """
        获取物种组合信息
        1.调用获取组合信息接口
        2.断言返回组合信息（可能为空数组）
        """
        with allure.step("1.调用获取组合信息接口"):
            response = self.gbif_api.species_combinations(self.taxon_key)
            assert response is not None, "调用获取组合信息接口返回None"

        with allure.step("2.断言返回结果"):
            assert isinstance(response, list), f"响应应为数组类型，实际:{type(response)}"

    @allure.story("获取物种清单数据集")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_species_checklist_datasets(self):
        """
        获取物种清单数据集
        1.调用获取清单数据集接口
        2.断言返回数据集列表
        """
        with allure.step("1.调用获取清单数据集接口"):
            response = self.gbif_api.species_checklist_datasets(self.taxon_key)
            assert response, f"调用获取清单数据集接口报错:{response}"

        with allure.step("2.断言返回结果"):
            assert "count" in response, f"响应缺少count字段:{response}"
            assert "results" in response, f"响应缺少results字段:{response}"
            assert response["count"] > 0, f"数据集数量应大于0，实际:{response['count']}"

        with allure.step("3.断言数据集详情"):
            first_dataset = response["results"][0]
            assert "key" in first_dataset, f"数据集缺少key字段:{first_dataset}"
            assert "title" in first_dataset, f"数据集缺少title字段:{first_dataset}"

    @allure.story("获取物种出现数据集")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_species_occurrence_datasets(self):
        """
        获取物种出现数据集
        1.调用获取出现数据集接口
        2.断言返回数据集列表
        """
        with allure.step("1.调用获取出现数据集接口"):
            response = self.gbif_api.species_occurrence_datasets(self.taxon_key)
            assert response, f"调用获取出现数据集接口报错:{response}"

        with allure.step("2.断言返回结果"):
            assert "count" in response, f"响应缺少count字段:{response}"
            assert "results" in response, f"响应缺少results字段:{response}"
            assert response["count"] > 0, f"数据集数量应大于0，实际:{response['count']}"

    # ==================== 分类学相关 ====================

    @allure.story("获取分类详情")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_taxonomy_detail(self):
        """
        获取分类详情
        1.调用获取分类详情接口
        2.断言返回分类详细信息
        """
        with allure.step("1.调用获取分类详情接口"):
            response = self.gbif_api.taxonomy_detail(self.dataset_key, self.taxon_key)
            assert response, f"调用获取分类详情接口报错:{response}"

        with allure.step("2.断言返回结果"):
            assert "key" in response, f"响应缺少key字段:{response}"
            assert "scientificName" in response, f"响应缺少scientificName字段:{response}"
            assert "kingdom" in response, f"响应缺少kingdom字段:{response}"
            assert response.get("kingdom") == "Plantae", \
                f"kingdom应为Plantae，实际:{response.get('kingdom')}"
            assert response.get("scientificName") == "Bryophyta", \
                f"scientificName应为Bryophyta，实际:{response.get('scientificName')}"

    @allure.story("获取父分类链")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_taxonomy_parents(self):
        """
        获取父分类链
        1.调用获取父分类接口
        2.断言返回父分类列表
        """
        with allure.step("1.调用获取父分类接口"):
            response = self.gbif_api.taxonomy_parents(self.dataset_key, self.taxon_key)
            assert response is not None, "调用获取父分类接口返回None"

        with allure.step("2.断言返回结果"):
            assert isinstance(response, list), f"响应应为数组类型，实际:{type(response)}"
            assert len(response) > 0, "父分类列表不应为空"

        with allure.step("3.断言父分类详情"):
            parent = response[0]
            assert "key" in parent, f"父分类缺少key字段:{parent}"
            assert "rank" in parent, f"父分类缺少rank字段:{parent}"
            assert "scientificName" in parent, f"父分类缺少scientificName字段:{parent}"

    @allure.story("获取子分类列表")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_taxonomy_children(self):
        """
        获取子分类列表
        1.调用获取子分类接口
        2.断言返回子分类列表
        """
        with allure.step("1.调用获取子分类接口"):
            response = self.gbif_api.taxonomy_children(self.dataset_key, self.taxon_key)
            assert response, f"调用获取子分类接口报错:{response}"

        with allure.step("2.断言返回结果"):
            assert "results" in response, f"响应缺少results字段:{response}"
            results = response["results"]
            assert len(results) > 0, "子分类列表不应为空"

        with allure.step("3.断言子分类详情"):
            first_child = results[0]
            assert "key" in first_child, f"子分类缺少key字段:{first_child}"
            assert "scientificName" in first_child, f"子分类缺少scientificName字段:{first_child}"
            assert "rank" in first_child, f"子分类缺少rank字段:{first_child}"

    @allure.story("获取同义词列表")
    @allure.severity(allure.severity_level.NORMAL)
    def test_taxonomy_synonyms(self):
        """
        获取同义词列表
        1.调用获取同义词接口
        2.断言返回同义词列表（可能为空）
        """
        with allure.step("1.调用获取同义词接口"):
            response = self.gbif_api.taxonomy_synonyms(self.dataset_key, self.taxon_key)
            assert response, f"调用获取同义词接口报错:{response}"

        with allure.step("2.断言返回结果"):
            assert "results" in response, f"响应缺少results字段:{response}"
            # 同义词可能为空，不断言数量

    # ==================== 外部关联 ====================

    @allure.story("获取物种Wikidata信息")
    @allure.severity(allure.severity_level.NORMAL)
    def test_species_wikidata(self):
        """
        获取物种Wikidata信息
        1.调用获取Wikidata信息接口
        2.断言返回Wikidata关联信息（可能触发429限流）
        """
        with allure.step("1.调用获取Wikidata信息接口"):
            response = self.gbif_api.species_wikidata(self.taxon_key)
            assert response, f"调用获取Wikidata信息接口报错:{response}"

        with allure.step("2.断言返回结果"):
            # 检查是否触发限流
            if response.get("_rate_limited"):
                allure.attach(
                    f"接口触发429限流，建议等待 {response.get('retry_after', '60')} 秒后重试",
                    name="限流提示"
                )
                # 限流情况标记为跳过而非失败
                import pytest
                pytest.skip("Wikidata接口触发429限流，跳过此用例")
            else:
                assert "wikidataId" in response, f"响应缺少wikidataId字段:{response}"
                assert "wikidataUrl" in response, f"响应缺少wikidataUrl字段:{response}"
                assert response["wikidataId"] == "Q25347", \
                    f"wikidataId应为Q25347，实际:{response['wikidataId']}"
                assert "wikidata.org" in response["wikidataUrl"], \
                    f"wikidataUrl应包含wikidata.org，实际:{response['wikidataUrl']}"

    # ==================== 完整链路测试 ====================

    @allure.story("物种详情页完整加载链路")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_species_detail_full_flow(self):
        """
        物种详情页完整加载链路
        1.获取物种名称
        2.获取物种俗名
        3.获取所有俗名列表
        4.获取分类详情
        5.获取父分类链
        6.获取子分类列表
        7.获取同义词列表
        8.获取清单数据集
        9.获取出现数据集
        10.获取Wikidata信息
        """
        with allure.step("1.获取物种名称"):
            name_resp = self.gbif_api.species_name(self.taxon_key)
            assert name_resp, f"获取物种名称报错:{name_resp}"
            assert name_resp.get("n") == "Bryophyta", f"物种名称应为Bryophyta，实际:{name_resp.get('n')}"

        with allure.step("2.获取物种俗名"):
            vernacular_resp = self.gbif_api.species_vernacular_name(self.taxon_key)
            # 该接口可能返回 None（204 No Content），这是正常情况
            if vernacular_resp is not None:
                assert "vernacularName" in vernacular_resp, f"响应缺少vernacularName字段:{vernacular_resp}"
                allure.attach(f"俗名: {vernacular_resp.get('vernacularName')}", name="物种俗名")
            else:
                allure.attach("接口返回204 No Content，该物种无单独俗名数据", name="响应状态")

        with allure.step("3.获取所有俗名列表"):
            vernaculars_resp = self.gbif_api.species_vernacular_names(self.taxon_key)
            assert vernaculars_resp, f"获取所有俗名报错:{vernaculars_resp}"
            assert vernaculars_resp.get("count", 0) > 0, "俗名数量应大于0"

        with allure.step("4.获取分类详情"):
            taxonomy_resp = self.gbif_api.taxonomy_detail(self.dataset_key, self.taxon_key)
            assert taxonomy_resp, f"获取分类详情报错:{taxonomy_resp}"
            assert taxonomy_resp.get("kingdom") == "Plantae", "kingdom应为Plantae"

        with allure.step("5.获取父分类链"):
            parents_resp = self.gbif_api.taxonomy_parents(self.dataset_key, self.taxon_key)
            assert parents_resp is not None, "获取父分类返回None"
            assert isinstance(parents_resp, list), "父分类应为数组类型"
            assert len(parents_resp) > 0, "父分类列表不应为空"

        with allure.step("6.获取子分类列表"):
            children_resp = self.gbif_api.taxonomy_children(self.dataset_key, self.taxon_key)
            assert children_resp, f"获取子分类报错:{children_resp}"
            assert "results" in children_resp, "响应缺少results字段"
            assert len(children_resp["results"]) > 0, "子分类列表不应为空"

        with allure.step("7.获取同义词列表"):
            synonyms_resp = self.gbif_api.taxonomy_synonyms(self.dataset_key, self.taxon_key)
            assert synonyms_resp, f"获取同义词报错:{synonyms_resp}"
            assert "results" in synonyms_resp, "响应缺少results字段"

        with allure.step("8.获取清单数据集"):
            checklist_resp = self.gbif_api.species_checklist_datasets(self.taxon_key)
            assert checklist_resp, f"获取清单数据集报错:{checklist_resp}"
            assert checklist_resp.get("count", 0) > 0, "清单数据集数量应大于0"

        with allure.step("9.获取出现数据集"):
            occurrence_resp = self.gbif_api.species_occurrence_datasets(self.taxon_key)
            assert occurrence_resp, f"获取出现数据集报错:{occurrence_resp}"
            assert occurrence_resp.get("count", 0) > 0, "出现数据集数量应大于0"

        with allure.step("10.获取Wikidata信息"):
            wikidata_resp = self.gbif_api.species_wikidata(self.taxon_key)
            assert wikidata_resp, f"获取Wikidata信息报错:{wikidata_resp}"
            # 检查是否触发限流
            if wikidata_resp.get("_rate_limited"):
                allure.attach(
                    f"接口触发429限流，建议等待 {wikidata_resp.get('retry_after', '60')} 秒后重试",
                    name="限流提示"
                )
            else:
                assert "wikidataId" in wikidata_resp, "响应缺少wikidataId字段"
                allure.attach(f"Wikidata ID: {wikidata_resp.get('wikidataId')}", name="Wikidata信息")
