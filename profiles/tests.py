from decimal import Decimal

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import override_settings

from accounts.models import User

from .admin import EmployerProfileAdmin, SkillAdmin, StudentProfileAdmin
from .models import EmployerProfile, Skill, StudentProfile
from .validators import MAX_RESUME_SIZE

pytestmark = pytest.mark.django_db


def create_user(email, role):
    return User.objects.create_user(email, "password123", role=role)


def test_skill_normalizes_name_and_is_unique():
    skill = Skill.objects.create(name="  Python ")

    assert skill.name == "python"

    with pytest.raises(IntegrityError):
        Skill.objects.create(name="PYTHON")


def test_student_profile_stores_skills_and_valid_resume(tmp_path):
    student = create_user("student@example.com", User.Role.STUDENT)
    python = Skill.objects.create(name="Python")
    resume = SimpleUploadedFile(
        "resume.pdf", b"%PDF-1.7 resume", content_type="application/pdf"
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        profile = StudentProfile(
            user=student,
            full_name="Student Example",
            university="Example University",
            department="Computer Science",
            cgpa=Decimal("3.75"),
            resume=resume,
        )
        profile.full_clean()
        profile.save()
        profile.skills.add(python)

    assert list(profile.skills.all()) == [python]


@pytest.mark.parametrize("cgpa", [Decimal("-0.01"), Decimal("4.01")])
def test_student_profile_rejects_cgpa_outside_range(cgpa):
    student = create_user("student@example.com", User.Role.STUDENT)
    profile = StudentProfile(
        user=student,
        full_name="Student Example",
        university="Example University",
        department="Computer Science",
        cgpa=cgpa,
    )

    with pytest.raises(ValidationError):
        profile.full_clean()


def test_student_profile_rejects_non_pdf_resume():
    student = create_user("student@example.com", User.Role.STUDENT)
    profile = StudentProfile(
        user=student,
        full_name="Student Example",
        university="Example University",
        department="Computer Science",
        resume=SimpleUploadedFile(
            "resume.txt", b"not a PDF", content_type="text/plain"
        ),
    )

    with pytest.raises(ValidationError, match="PDF"):
        profile.full_clean()


def test_student_profile_rejects_resume_over_size_limit():
    student = create_user("student@example.com", User.Role.STUDENT)
    profile = StudentProfile(
        user=student,
        full_name="Student Example",
        university="Example University",
        department="Computer Science",
        resume=SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.7" + b"x" * MAX_RESUME_SIZE,
            content_type="application/pdf",
        ),
    )

    with pytest.raises(ValidationError, match="5 MB"):
        profile.full_clean()


def test_employer_profile_is_unverified_by_default():
    employer = create_user("employer@example.com", User.Role.EMPLOYER)
    profile = EmployerProfile.objects.create(
        user=employer, company_name="Example Company"
    )

    assert profile.is_verified is False


def test_profiles_are_registered_with_admin():
    assert isinstance(admin.site._registry[Skill], SkillAdmin)
    assert isinstance(admin.site._registry[StudentProfile], StudentProfileAdmin)
    assert isinstance(admin.site._registry[EmployerProfile], EmployerProfileAdmin)
