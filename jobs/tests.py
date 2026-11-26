from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from applications.models import Application
from profiles.models import EmployerProfile, Skill, StudentProfile

from .models import JobPost

pytestmark = pytest.mark.django_db


def make_employer(email, verified=True):
    user = User.objects.create_user(
        email, "A-strong-password-123!", role=User.Role.EMPLOYER
    )
    EmployerProfile.objects.create(
        user=user, company_name="Example Company", is_verified=verified
    )
    return user


def make_job(employer, **overrides):
    values = {
        "employer": employer.employer_profile,
        "title": "Backend Engineer",
        "description": "Build backend services.",
        "job_type": JobPost.JobType.FULL_TIME,
        "location": "Dhaka",
        "min_cgpa": Decimal("3.00"),
        "deadline": timezone.now() + timedelta(days=7),
    }
    values.update(overrides)
    return JobPost.objects.create(**values)


def make_student(email, skills=(), cgpa=Decimal("3.50")):
    user = User.objects.create_user(email, "password123")
    profile = StudentProfile.objects.create(
        user=user,
        full_name="Student",
        university="University",
        department="Department",
        cgpa=cgpa,
    )
    profile.skills.set(
        [Skill.objects.get_or_create(name=skill.lower())[0] for skill in skills]
    )
    return user


def test_verified_employer_can_create_job():
    employer = make_employer("verified@example.com")
    skill = Skill.objects.create(name="Python")
    client = APIClient()
    client.force_authenticate(employer)

    response = client.post(
        reverse("job-list"),
        {
            "title": "Python Intern",
            "description": "Learn and build.",
            "job_type": "internship",
            "location": "Dhaka",
            "required_skills": [skill.id],
            "min_cgpa": "3.25",
            "deadline": (timezone.now() + timedelta(days=7)).isoformat(),
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["employer"] == employer.employer_profile.id
    assert JobPost.objects.filter(title="Python Intern").exists()


def test_unverified_employer_cannot_create_job():
    employer = make_employer("unverified@example.com", verified=False)
    client = APIClient()
    client.force_authenticate(employer)

    response = client.post(
        reverse("job-list"),
        {
            "title": "Blocked Job",
            "description": "Should not be posted.",
            "job_type": "full_time",
            "location": "Dhaka",
            "deadline": (timezone.now() + timedelta(days=7)).isoformat(),
        },
        format="json",
    )

    assert response.status_code == 403
    assert not JobPost.objects.filter(title="Blocked Job").exists()


def test_student_cannot_create_job():
    student = User.objects.create_user("student@example.com", "password123")
    client = APIClient()
    client.force_authenticate(student)

    response = client.post(reverse("job-list"), {}, format="json")

    assert response.status_code == 403


def test_only_job_owner_can_update_and_delete():
    owner = make_employer("owner@example.com")
    other = make_employer("other@example.com")
    job = make_job(owner)
    client = APIClient()
    client.force_authenticate(other)

    update = client.patch(
        reverse("job-detail", args=[job.id]), {"title": "Changed"}, format="json"
    )
    delete = client.delete(reverse("job-detail", args=[job.id]))

    assert update.status_code == 403
    assert delete.status_code == 403

    client.force_authenticate(owner)
    assert client.patch(
        reverse("job-detail", args=[job.id]), {"title": "Changed"}, format="json"
    ).status_code == 200
    assert client.delete(reverse("job-detail", args=[job.id])).status_code == 204


def test_jobs_can_filter_search_order_and_paginate():
    employer = make_employer("listing@example.com")
    python = Skill.objects.create(name="Python")
    backend = make_job(employer, title="Backend Engineer", job_type="full_time")
    backend.required_skills.add(python)
    make_job(
        employer,
        title="Python Intern",
        job_type="internship",
        location="Chattogram",
    )
    make_job(employer, title="Data Analyst", job_type="part_time")
    JobPost.objects.create(
        employer=employer.employer_profile,
        title="Closed Role",
        description="Not public.",
        job_type="full_time",
        location="Dhaka",
        deadline=timezone.now() + timedelta(days=7),
        is_active=False,
    )
    client = APIClient()

    filtered = client.get(
        reverse("job-list"),
        {"job_type": "full_time", "location": "dhaka", "skill": "python"},
    )
    searched = client.get(reverse("job-list"), {"search": "Data"})
    ordered = client.get(reverse("job-list"), {"ordering": "title"})
    paginated = client.get(reverse("job-list"), {"page_size": 1})

    assert filtered.status_code == 200
    assert [job["id"] for job in filtered.data["results"]] == [backend.id]
    assert [job["title"] for job in searched.data["results"]] == ["Data Analyst"]
    assert ordered.data["results"][0]["title"] == "Backend Engineer"
    assert paginated.data["count"] == 3
    assert len(paginated.data["results"]) == 1


def test_job_detail_is_public():
    employer = make_employer("public@example.com")
    job = make_job(employer)

    response = APIClient().get(reverse("job-detail", args=[job.id]))

    assert response.status_code == 200
    assert response.data["id"] == job.id


def test_job_list_avoids_n_plus_one_queries(django_assert_num_queries):
    employer = make_employer("queries@example.com")
    skill = Skill.objects.create(name="Django")
    first = make_job(employer, title="First")
    second = make_job(employer, title="Second")
    first.required_skills.add(skill)
    second.required_skills.add(skill)

    with django_assert_num_queries(3):
        response = APIClient().get(reverse("job-list"))

    assert response.status_code == 200
    assert len(response.data["results"]) == 2


def test_recommended_jobs_are_ranked_with_explainable_match_data():
    employer = make_employer("recommended-employer@example.com")
    python = Skill.objects.create(name="Python")
    student = make_student("recommended-student@example.com", skills=("Python",))
    matching_job = make_job(employer, title="Matching Job")
    matching_job.required_skills.add(python)
    make_job(employer, title="No Skills Job")
    client = APIClient()
    client.force_authenticate(student)

    response = client.get(reverse("job-recommended"))

    assert response.status_code == 200
    assert [item["title"] for item in response.data] == [
        "Matching Job",
        "No Skills Job",
    ]
    assert response.data[0]["match_score"] == 1.0
    assert response.data[0]["matched_skills"] == ["python"]
    assert response.data[0]["missing_skills"] == []


def test_recommended_jobs_do_not_issue_n_plus_one_queries(django_assert_num_queries):
    employer = make_employer("recommended-query-employer@example.com")
    student = make_student("recommended-query-student@example.com", skills=("Python",))
    skill = Skill.objects.get(name="python")
    first = make_job(employer, title="First Recommended")
    second = make_job(employer, title="Second Recommended")
    first.required_skills.add(skill)
    second.required_skills.add(skill)
    client = APIClient()
    client.force_authenticate(student)

    with django_assert_num_queries(4):
        response = client.get(reverse("job-recommended"))

    assert response.status_code == 200
    assert len(response.data) == 2


def test_job_matches_rank_applicants_for_the_job_owner():
    employer = make_employer("matches-employer@example.com")
    python = Skill.objects.create(name="Python")
    first_student = make_student("first-matcher@example.com", skills=("Python",))
    second_student = make_student("second-matcher@example.com", skills=("Java",))
    job = make_job(employer, title="Matching Applicants")
    job.required_skills.add(python)
    Application.objects.create(student=second_student, job=job)
    Application.objects.create(student=first_student, job=job)
    client = APIClient()
    client.force_authenticate(employer)

    response = client.get(reverse("job-matches", args=[job.id]))

    assert response.status_code == 200
    assert [item["student_id"] for item in response.data] == [
        first_student.id,
        second_student.id,
    ]
    assert response.data[0]["match_score"] == 1.0
    assert response.data[1]["match_score"] == 0.0


def test_job_matches_do_not_issue_n_plus_one_queries(django_assert_num_queries):
    employer = make_employer("matches-query-employer@example.com")
    skill = Skill.objects.create(name="Python")
    first_student = make_student("first-query-matcher@example.com", skills=("Python",))
    second_student = make_student("second-query-matcher@example.com", skills=("Java",))
    job = make_job(employer, title="Query Matching Applicants")
    job.required_skills.add(skill)
    Application.objects.create(student=first_student, job=job)
    Application.objects.create(student=second_student, job=job)
    client = APIClient()
    client.force_authenticate(employer)

    with django_assert_num_queries(4):
        response = client.get(reverse("job-matches", args=[job.id]))

    assert response.status_code == 200
    assert len(response.data) == 2
