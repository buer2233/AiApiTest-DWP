"""ASGI 应用入口。
用于异步服务器或支持 ASGI 的部署环境加载 Django 后端应用。
"""

import os

from django.core.asgi import get_asgi_application


# 保证 ASGI 进程启动时加载本项目默认 settings。
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
