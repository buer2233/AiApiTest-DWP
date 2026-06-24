"""accounts 用户管理器迁移。
本迁移把 User.objects 切换为平台自定义 UserManager，用于保证 create_superuser 默认角色为 admin。
"""

# Generated for Stage 5 custom user manager.

import django.contrib.auth.models
from django.db import migrations

import apps.accounts.models


class Migration(migrations.Migration):
    """切换 User 模型 manager 的迁移。"""

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", apps.accounts.models.UserManager()),
            ],
        ),
    ]
