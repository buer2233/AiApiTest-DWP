# Generated for Phase 11 MySQL compatibility regression.
from __future__ import annotations

import hashlib

from django.db import migrations, models


def apply_legacy_mysql_schema_changes(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    table_name = "test_case_result"
    column_name = "current_node_key"
    quoted_table = schema_editor.quote_name(table_name)
    quoted_column = schema_editor.quote_name(column_name)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CHARACTER_MAXIMUM_LENGTH
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            """,
            [table_name, column_name],
        )
        row = cursor.fetchone()
        if row and row[0] and int(row[0]) > 64:
            schema_editor.execute(f"ALTER TABLE {quoted_table} MODIFY {quoted_column} varchar(64) NULL")

        constraints = schema_editor.connection.introspection.get_constraints(cursor, table_name)
        for index_name, constraint in constraints.items():
            # 兼容已执行旧 0002 的 MySQL 库：移除 node_id 单列索引，保留当前用例唯一约束。
            if (
                constraint.get("columns") == ["node_id"]
                and constraint.get("index")
                and not constraint.get("unique")
                and not constraint.get("primary_key")
                and not constraint.get("foreign_key")
            ):
                schema_editor.execute(f"ALTER TABLE {quoted_table} DROP INDEX {schema_editor.quote_name(index_name)}")


def hash_existing_current_node_keys(apps, schema_editor):
    TestCaseResult = apps.get_model("metrics", "TestCaseResult")
    for case_result in TestCaseResult.objects.only("id", "node_id", "is_current", "current_node_key").iterator():
        next_key = hashlib.sha256(case_result.node_id.encode("utf-8")).hexdigest() if case_result.is_current else None
        if case_result.current_node_key != next_key:
            TestCaseResult.objects.filter(pk=case_result.pk).update(current_node_key=next_key)


class Migration(migrations.Migration):
    dependencies = [
        ("metrics", "0003_p5_jenkins_execution_loop"),
    ]

    operations = [
        migrations.RunPython(hash_existing_current_node_keys, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(apply_legacy_mysql_schema_changes, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="testcaseresult",
            name="current_node_key",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="testcaseresult",
            name="node_id",
            field=models.CharField(max_length=1024),
        ),
    ]
