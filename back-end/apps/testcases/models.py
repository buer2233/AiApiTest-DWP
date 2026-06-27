"""testcases 数据模型：api-test 用例静态解析快照。"""
from django.db import models


class TestCaseSnapshot(models.Model):
    """保存 api-test/test_case 静态解析得到的用例清单快照，供前端只读展示。

    - 按 node_id upsert；本次未扫描到的旧用例置 is_active=False（软删）。
    """

    # 类名以 Test 开头，显式声明避免被 pytest 误当测试类收集
    __test__ = False

    module_key = models.CharField("模块标识", max_length=128, db_index=True)
    module_name = models.CharField("模块展示名", max_length=255)
    case_path = models.CharField("用例文件路径", max_length=512)
    node_id = models.CharField("pytest node id", max_length=512, unique=True)
    function_name = models.CharField("测试函数名", max_length=255)
    class_name = models.CharField("测试类名", max_length=255, null=True, blank=True)
    case_title = models.CharField("用例标题", max_length=512, blank=True, default="")
    story = models.CharField("story", max_length=255, blank=True, default="")
    severity = models.CharField("severity", max_length=32, blank=True, default="")
    is_active = models.BooleanField("是否启用", default=True, db_index=True)
    synced_at = models.DateTimeField("最近同步时间")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "testcases_testcasesnapshot"
        verbose_name = "用例快照"
        verbose_name_plural = "用例快照"
        ordering = ["module_key", "node_id"]

    def __str__(self):
        return self.node_id
