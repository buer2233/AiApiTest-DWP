from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TestCaseItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("node_id", models.CharField(max_length=512, unique=True)),
                ("package_name", models.CharField(db_index=True, max_length=200)),
                ("module_name", models.CharField(db_index=True, max_length=200)),
                ("file_path", models.CharField(db_index=True, max_length=500)),
                ("class_name", models.CharField(blank=True, max_length=200)),
                ("function_name", models.CharField(db_index=True, max_length=200)),
                ("title", models.CharField(blank=True, max_length=300)),
                ("description", models.TextField(blank=True)),
                ("markers", models.JSONField(default=list)),
                ("sync_status", models.CharField(choices=[("synced", "Synced"), ("missing", "Missing")], db_index=True, default="synced", max_length=20)),
                ("last_synced_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "test_case_item", "ordering": ["package_name", "file_path", "function_name"]},
        ),
    ]
