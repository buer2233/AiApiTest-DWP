from __future__ import annotations

from django.core.management.base import BaseCommand

from metrics.models import TestEnvironment


class Command(BaseCommand):
    help = "幂等写入 P2 默认测试环境。"

    def handle(self, *args, **options):
        environment, created = TestEnvironment.objects.update_or_create(
            env_key="mock-gbif",
            defaults={
                "env_name": "模拟测试环境",
                "base_url": "https://api.gbif.org",
                "is_active": True,
            },
        )
        action = "created" if created else "updated"
        self.stdout.write(f"seed_environment {action} id={environment.id}")
