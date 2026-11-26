import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from profiles.models import EmployerProfile, StudentProfile

pytestmark = pytest.mark.django_db


def strong_password():
    return "A-strong-password-123!"


@pytest.mark.parametrize(
    ("role", "profile_model"),
    [
        (User.Role.STUDENT, StudentProfile),
        (User.Role.EMPLOYER, EmployerProfile),
    ],
)
def test_register_creates_user_and_matching_profile(role, profile_model):
    client = APIClient()
    response = client.post(
        reverse("auth-register"),
        {
            "email": f"{role}@example.com",
            "password": strong_password(),
            "role": role,
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email=f"{role}@example.com")
    assert user.role == role
    assert profile_model.objects.filter(user=user).exists()


def test_register_rejects_admin_role():
    client = APIClient()

    response = client.post(
        reverse("auth-register"),
        {
            "email": "admin-register@example.com",
            "password": strong_password(),
            "role": User.Role.ADMIN,
        },
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="admin-register@example.com").exists()


def test_login_returns_access_and_refresh_tokens():
    User.objects.create_user("login@example.com", strong_password())
    client = APIClient()

    response = client.post(
        reverse("auth-login"),
        {"email": "login@example.com", "password": strong_password()},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_refresh_returns_new_access_token():
    User.objects.create_user("refresh@example.com", strong_password())
    client = APIClient()
    login = client.post(
        reverse("auth-login"),
        {"email": "refresh@example.com", "password": strong_password()},
        format="json",
    )

    response = client.post(
        reverse("auth-refresh"), {"refresh": login.data["refresh"]}, format="json"
    )

    assert response.status_code == 200
    assert "access" in response.data


def test_me_requires_authentication():
    client = APIClient()

    response = client.get(reverse("auth-me"))

    assert response.status_code == 401


def test_me_returns_authenticated_user():
    user = User.objects.create_user("me@example.com", strong_password())
    client = APIClient()
    login = client.post(
        reverse("auth-login"),
        {"email": user.email, "password": strong_password()},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = client.get(reverse("auth-me"))

    assert response.status_code == 200
    assert response.data == {"id": user.id, "email": user.email, "role": user.role}
