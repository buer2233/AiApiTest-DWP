import os


# pytest 必须与根目录私有 Jenkins 配置隔离，避免测试误连本地或真实服务。
for key in (
    "JENKINS_API_BASE_URL",
    "JENKINS_PUBLIC_BASE_URL",
    "JENKINS_USERNAME",
    "JENKINS_API_TOKEN",
):
    os.environ[key] = ""

from .base import *  # noqa: F401,F403


DEBUG = True
# 即使根私有配置存在，pytest 也不会把真实 Jenkins 作为测试依赖。
JENKINS_API_BASE_URL = ""
JENKINS_PUBLIC_BASE_URL = ""
JENKINS_USERNAME = ""
JENKINS_API_TOKEN = ""
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


class DisableMigrations:
    def __contains__(self, item: str) -> bool:
        return True

    def __getitem__(self, item: str) -> None:
        return None


MIGRATION_MODULES = DisableMigrations()
