from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from accounts.models import User
from jobs.models import JobPost
from profiles.models import EmployerProfile, Skill, StudentProfile

from .services import calculate_match

pytestmark = pytest.mark.django_db


def make_match_data(student_skills, required_skills, cgpa="3.50", min_cgpa=None):
    student = User.objects.create_user(
        f"student-{len(student_skills)}@example.com", "password123"
    )
    student_profile = StudentProfile.objects.create(
        user=student,
        full_name="Student",
        university="University",
        department="Department",
        cgpa=Decimal(cgpa) if cgpa is not None else None,
    )
    skill_map = {
        skill.lower(): Skill.objects.create(name=skill)
        for skill in set(student_skills + required_skills)
    }
    student_profile.skills.set(
        [skill_map[skill.lower()] for skill in student_skills]
    )
    employer = User.objects.create_user(
        f"employer-{len(required_skills)}@example.com",
        "password123",
        role=User.Role.EMPLOYER,
    )
    employer_profile = EmployerProfile.objects.create(
        user=employer, company_name="Company", is_verified=True
    )
    job = JobPost.objects.create(
        employer=employer_profile,
        title="Job",
        description="Description",
        job_type=JobPost.JobType.FULL_TIME,
        location="Dhaka",
        min_cgpa=min_cgpa,
        deadline=timezone.now() + timedelta(days=7),
    )
    job.required_skills.set(
        [skill_map[skill.lower()] for skill in required_skills]
    )
    return student_profile, job


def test_full_skill_match():
    profile, job = make_match_data(["python", "django"], ["python", "django"])

    assert calculate_match(profile, job) == {
        "match_score": 100.0,
        "matched_skills": ["django", "python"],
        "missing_skills": [],
    }


def test_partial_skill_match_uses_required_skill_coverage():
    profile, job = make_match_data(["python", "sql"], ["python", "django"])

    assert calculate_match(profile, job) == {
        "match_score": 50.0,
        "matched_skills": ["python"],
        "missing_skills": ["django"],
    }


def test_extra_student_skills_do_not_reduce_full_coverage():
    profile, job = make_match_data(
        ["python", "django", "sql", "docker", "git"], ["python", "django"]
    )

    assert calculate_match(profile, job)["match_score"] == 100.0


def test_zero_skill_overlap():
    profile, job = make_match_data(["javascript"], ["python", "django"])

    assert calculate_match(profile, job) == {
        "match_score": 0.0,
        "matched_skills": [],
        "missing_skills": ["django", "python"],
    }


def test_below_cgpa_gate_has_zero_score():
    profile, job = make_match_data(
        ["python"], ["python"], cgpa="2.50", min_cgpa=Decimal("3.00")
    )

    result = calculate_match(profile, job)

    assert result["match_score"] == 0.0
    assert result["matched_skills"] == ["python"]


def test_job_with_no_required_skills_is_fully_eligible():
    profile, job = make_match_data(["python"], [])

    assert calculate_match(profile, job) == {
        "match_score": 100.0,
        "matched_skills": [],
        "missing_skills": [],
    }
