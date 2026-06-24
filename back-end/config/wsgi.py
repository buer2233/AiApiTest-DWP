"""WSGI 应用入口。
用于 gunicorn、uWSGI 或 Django runserver 等 WSGI 环境加载后端应用。
"""

import os

from django.core.wsgi import get_wsgi_application


# 保证 WSGI 进程启动时加载本项目默认 settings。
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
