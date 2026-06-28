import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user(db):
    from django.contrib.auth import get_user_model

    def _create_user(**kwargs):
        defaults = {
            "username": "member001",
            "email": "member001@example.com",
            "password": "StrongPass123",
            "role": "member",
            "status": "active",
        }
        defaults.update(kwargs)
        password = defaults.pop("password")
        return get_user_model().objects.create_user(password=password, **defaults)

    return _create_user


@pytest.fixture
def admin_user(create_user):
    return create_user(
        username="admin",
        email="admin@example.com",
        role="admin",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def member_user(create_user):
    return create_user()


@pytest.fixture
def auth_client(api_client):
    def _auth_client(user):
        from rest_framework.authtoken.models import Token

        token, _ = Token.objects.get_or_create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return api_client

    return _auth_client
