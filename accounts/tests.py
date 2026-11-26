import pytest
from django.db import IntegrityError

from accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_normalizes_email_and_defaults_to_student():
    user = User.objects.create_user("Student@Example.COM", "password123")

    assert user.email == "student@example.com"
    assert user.role == User.Role.STUDENT
    assert user.check_password("password123")


def test_create_superuser_sets_admin_permissions_and_role():
    user = User.objects.create_superuser("Admin@Example.COM", "password123")

    assert user.email == "admin@example.com"
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.role == User.Role.ADMIN


def test_email_is_required():
    with pytest.raises(ValueError, match="email"):
        User.objects.create_user("", "password123")


def test_duplicate_email_is_rejected():
    User.objects.create_user("duplicate@example.com", "password123")

    with pytest.raises(IntegrityError):
        User.objects.create_user("duplicate@example.com", "password123")


def test_email_is_normalized_on_save():
    user = User(email="Direct@Example.COM")
    user.set_password("password123")
    user.save()

    assert user.email == "direct@example.com"
