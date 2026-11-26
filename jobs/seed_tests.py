import io

import pytest
from django.core.management import call_command

from accounts.models import User
from applications.models import Application
from jobs.models import JobPost
from profiles.models import EmployerProfile, StudentProfile

pytestmark = pytest.mark.django_db


def test_seed_demo_data_is_idempotent_and_creates_fixed_logins():
    call_command("seed_demo_data", stdout=io.StringIO())
    first_counts = (
        User.objects.filter(role=User.Role.STUDENT).count(),
        User.objects.filter(role=User.Role.EMPLOYER).count(),
        StudentProfile.objects.count(),
        EmployerProfile.objects.count(),
        JobPost.objects.filter(title__startswith="Demo ").count(),
        Application.objects.count(),
    )

    call_command("seed_demo_data", stdout=io.StringIO())
    second_counts = (
        User.objects.filter(role=User.Role.STUDENT).count(),
        User.objects.filter(role=User.Role.EMPLOYER).count(),
        StudentProfile.objects.count(),
        EmployerProfile.objects.count(),
        JobPost.objects.filter(title__startswith="Demo ").count(),
        Application.objects.count(),
    )

    assert first_counts == (30, 8, 30, 8, 40, 150)
    assert second_counts == first_counts
    assert User.objects.get(email="student@demo.com").check_password("DemoPass123!")
    assert User.objects.get(email="employer@demo.com").check_password("DemoPass123!")
    assert User.objects.get(email="admin@demo.com").is_superuser is True
    assert not EmployerProfile.objects.filter(
        user__email__endswith="@demo.com", is_verified=False
    ).exists()
