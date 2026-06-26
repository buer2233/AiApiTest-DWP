# -*- coding: utf-8 -*-

import pytest
import allure
import config
from page_api.gbif.gbif_api import GbifAPI


@allure.epic(f"{config.get_website_name()}-接口自动化")
@allure.feature("GBIF物种数据接口- 模块2")
class TestGbifModule2API:
    """
    GBIF API 接口测试 - 模块2
    公开的可用于接口测试的网站：https://api.gbif.org
    """
    # Module Name: 物种数据2
    # Auth Name: 李四

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
            assert "scientificName" in response, f"响应缺少scientificName字段:{response}"
            assert response["scientificName"] == "Bryophyta", \
                f"物种名称应为Bryophyta，实际:{response['scientificName']}"

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
            # 该接口可能没有俗名结果，这是正常情况
            if response is not None:
                assert "vernacularName" in response, f"响应缺少vernacularName字段:{response}"
                assert "language" in response, f"响应缺少language字段:{response}"
                assert response.get("taxonKey") == self.taxon_key, \
                    f"taxonKey应为{self.taxon_key}，实际:{response.get('taxonKey')}"
                allure.attach(f"俗名: {response.get('vernacularName')}", name="物种俗名")
            else:
                allure.attach("该物种无俗名数据", name="响应状态")

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
            assert "results" in response, f"响应缺少results字段:{response}"
            assert len(response["results"]) > 0, f"俗名列表不应为空:{response}"

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
            assert "results" in response, f"响应缺少results字段:{response}"
            assert isinstance(response["results"], list), \
                f"results应为数组类型，实际:{type(response['results'])}"

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

    @pytest.mark.skipif(True, reason="固定跳过用例！")
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
            assert "facets" in response, f"响应缺少facets字段:{response}"
            assert response["count"] > 0, f"出现记录数量应大于0，实际:{response['count']}"
            assert response["facets"], f"出现数据集分面不应为空:{response}"
            first_facet = response["facets"][0]
            assert first_facet.get("field") == "DATASET_KEY", \
                f"分面字段应为DATASET_KEY，实际:{first_facet.get('field')}"
            assert first_facet.get("counts"), f"数据集分面计数不应为空:{first_facet}"

    # ==================== 断言失败测试 ====================

    @allure.story("断言失败验证")
    @allure.title("故意失败的断言测试-验证Allure报告捕获断言失败")
    @allure.description("此用例故意设置不相等的断言，用于验证Allure报告能否正确展示断言失败的情况")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_deliberate_assertion_failure(self):
        """
        故意失败的断言测试用例

        用途说明：
        - 验证Allure报告能否正确捕获和展示断言失败
        - 用于测试失败重试执行器的断言失败处理逻辑
        - 作为示例展示断言失败时的错误信息格式

        预期结果：
        - 此用例必然失败，失败原因为断言错误（AssertionError）
        - 断言信息：期望值与实际值不相等

        失败原因：
        - 故意设置 1 != 2 的断言，确保用例必然失败
        """
        with allure.step("1.设置期望值和实际值"):
            # 期望值为 2，实际值为 1，两者必然不相等
            expected_value = 2
            actual_value = 1
            allure.attach(f"期望值: {expected_value}, 实际值: {actual_value}", name="断言参数")

        with allure.step("2.执行断言-必然失败"):
            # 执行断言，必然失败并输出详细的错误信息
            # 此断言用于验证Allure报告的断言失败展示功能
            assert actual_value == expected_value, (
                f"故意失败的断言测试：期望值 {expected_value} 与实际值 {actual_value} 不相等。"
                f"此用例用于验证Allure报告的断言失败展示功能。"
            )
