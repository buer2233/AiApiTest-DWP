from __future__ import annotations

import os

from django.core.management.base import BaseCommand, CommandError

from accounts.models import UserAccount


class Command(BaseCommand):
    help = "从环境变量初始化首个管理人员账号。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--bootstrap-only",
            action="store_true",
            help="仅在账号表为空时初始化首个管理人员账号。",
        )

    def handle(self, *args, **options):
        if options["bootstrap_only"] and UserAccount.objects.exists():
            # 首装幂等短路必须发生在读取私有变量之前，绝不修改既有账号。
            self.stdout.write("初始化管理人员已跳过：账号表已有记录。")
            return

        required = ["INITIAL_ADMIN_USERNAME", "INITIAL_ADMIN_DISPLAY_NAME", "INITIAL_ADMIN_PASSWORD"]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise CommandError(", ".join(missing))

        username = os.environ["INITIAL_ADMIN_USERNAME"]
        display_name = os.environ["INITIAL_ADMIN_DISPLAY_NAME"]
        password = os.environ["INITIAL_ADMIN_PASSWORD"]
        if len(password) < 8 or not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
            raise CommandError("INITIAL_ADMIN_PASSWORD 不满足复杂度要求。")

        user = UserAccount.objects.filter(username=username).first()
        if user is None:
            UserAccount.objects.create_user(
                username=username,
                display_name=display_name,
                password=password,
                role=UserAccount.Role.ADMIN,
            )
            self.stdout.write(self.style.SUCCESS("初始化管理人员已创建。"))
            return

        updated_fields: list[str] = []
        if user.display_name != display_name:
            user.display_name = display_name
            updated_fields.append("display_name")
        if user.role != UserAccount.Role.ADMIN:
            user.role = UserAccount.Role.ADMIN
            updated_fields.append("role")
        if updated_fields:
            updated_fields.append("updated_at")
            user.save(update_fields=updated_fields)
            self.stdout.write(self.style.SUCCESS("初始化管理人员已更新。"))
        else:
            self.stdout.write("初始化管理人员已存在。")
