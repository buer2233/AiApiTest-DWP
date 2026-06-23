# Generated for Stage 5 custom user manager.

import django.contrib.auth.models
from django.db import migrations

import apps.accounts.models


class Migration(migrations.Migration):
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
