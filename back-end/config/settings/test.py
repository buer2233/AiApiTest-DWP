"""测试配置：SQLite 内存库 + 快速哈希，零外部依赖，供 pytest 使用。"""
from .base import *  # noqa: F401,F403

DEBUG = True

# 测试用 SQLite 内存库，不连 MySQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# 加速密码哈希（不影响 AUTH_PASSWORD_VALIDATORS 的弱密码校验）
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# 固定一个测试用 SECRET_KEY，避免依赖环境
SECRET_KEY = "test-only-secret-key"

# 邮件走内存后端（本需求暂不发邮件，预留）
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
