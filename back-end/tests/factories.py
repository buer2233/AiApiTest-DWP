"""factory_boy 工厂：构造测试用户。"""
import factory
from django.contrib.auth import get_user_model

User = get_user_model()

# 测试统一示例密码（满足 Django 密码校验；非真实凭据）
TEST_PASSWORD = "Hermes#Test2026"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.test")
    status = User.STATUS_ACTIVE
    role = User.ROLE_MEMBER
    # 直接写入哈希后的密码，使 check_password 可用
    password = factory.django.Password(TEST_PASSWORD)
