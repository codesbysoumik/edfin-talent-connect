from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from jobs.models import JobPost
from profiles.models import EmployerProfile

from .models import Application, ApplicationStatusHistory
from .services import (
    STATUS_TRANSITIONS,
    InvalidStatusTransition,
    create_application,
    transition_application_status,
)

pytestmark = pytest.mark.django_db


def make_student(email):
    return User.objects.create_user(email, "password123")


def make_employer(email):
    user = User.objects.create_user(
        email, "password123", role=User.Role.EMPLOYER
    )
    EmployerProfile.objects.create(
        user=user, company_name="Example Company", is_verified=True
    )
    return user


def make_job(employer, title="Job"):
    return JobPost.objects.create(
        employer=employer.employer_profile,
        title=title,
        description="Description",
        job_type=JobPost.JobType.FULL_TIME,
        location="Dhaka",
        deadline=timezone.now() + timedelta(days=7),
    )


def make_application(student, employer, title="Job", status=Application.Status.APPLIED):
    return Application.objects.create(
        student=student,
        job=make_job(employer, title),
        status=status,
    )


def test_student_can_apply_to_active_job_and_history_is_created():
    student = make_student("student@example.com")
    employer = make_employer("employer@example.com")
    job = make_job(employer)
    client = APIClient()
    client.force_authenticate(student)

    response = client.post(
        reverse("job-apply", args=[job.id]),
        {"cover_letter": "I would love this opportunity."},
        format="json",
    )

    assert response.status_code == 201
    application = Application.objects.get(student=student, job=job)
    history = ApplicationStatusHistory.objects.get(application=application)
    assert application.status == Application.Status.APPLIED
    assert history.from_status is None
    assert history.to_status == Application.Status.APPLIED


def test_duplicate_application_is_rejected():
    student = make_student("duplicate@example.com")
    employer = make_employer("duplicate-employer@example.com")
    job = make_job(employer)
    client = APIClient()
    client.force_authenticate(student)

    client.post(reverse("job-apply", args=[job.id]), {}, format="json")
    response = client.post(reverse("job-apply", args=[job.id]), {}, format="json")

    assert response.status_code == 400


def test_only_active_jobs_accept_applications():
    student = make_student("inactive-student@example.com")
    employer = make_employer("inactive-employer@example.com")
    job = make_job(employer)
    job.is_active = False
    job.save(update_fields=["is_active"])
    client = APIClient()
    client.force_authenticate(student)

    response = client.post(reverse("job-apply", args=[job.id]), {}, format="json")

    assert response.status_code == 400
    assert not Application.objects.filter(student=student, job=job).exists()


def test_employers_cannot_apply():
    employer = make_employer("applying-employer@example.com")
    other_employer = make_employer("job-owner@example.com")
    job = make_job(other_employer)
    client = APIClient()
    client.force_authenticate(employer)

    response = client.post(reverse("job-apply", args=[job.id]), {}, format="json")

    assert response.status_code == 403


def test_students_only_see_their_own_applications_and_employers_see_own_jobs():
    student_one = make_student("one@example.com")
    student_two = make_student("two@example.com")
    employer_one = make_employer("one-employer@example.com")
    employer_two = make_employer("two-employer@example.com")
    application_one = make_application(student_one, employer_one, "One Job")
    application_two = make_application(student_two, employer_two, "Two Job")
    client = APIClient()

    client.force_authenticate(student_one)
    student_list = client.get(reverse("application-list"))
    student_other = client.get(
        reverse("application-detail", args=[application_two.id])
    )

    client.force_authenticate(employer_one)
    employer_list = client.get(reverse("application-list"))
    employer_other = client.get(
        reverse("application-detail", args=[application_two.id])
    )

    assert [item["id"] for item in student_list.data] == [application_one.id]
    assert student_other.status_code == 404
    assert [item["id"] for item in employer_list.data] == [application_one.id]
    assert employer_other.status_code == 404


def test_student_cannot_change_status_but_can_withdraw():
    student = make_student("status-student@example.com")
    employer = make_employer("status-employer@example.com")
    application = create_application(student, make_job(employer))
    client = APIClient()
    client.force_authenticate(student)

    forbidden = client.patch(
        reverse("application-update-status", args=[application.id]),
        {"status": Application.Status.SHORTLISTED},
        format="json",
    )
    withdrawn = client.patch(
        reverse("application-update-status", args=[application.id]),
        {"status": Application.Status.WITHDRAWN},
        format="json",
    )

    assert forbidden.status_code == 403
    assert withdrawn.status_code == 200
    assert withdrawn.data["status"] == Application.Status.WITHDRAWN


def test_other_employer_cannot_change_application_status():
    student = make_student("other-status-student@example.com")
    owner = make_employer("status-owner@example.com")
    other = make_employer("status-other@example.com")
    application = make_application(student, owner)
    client = APIClient()
    client.force_authenticate(other)

    response = client.patch(
        reverse("application-update-status", args=[application.id]),
        {"status": Application.Status.SHORTLISTED},
        format="json",
    )

    assert response.status_code == 404


def test_history_endpoint_returns_every_status_change():
    student = make_student("history-student@example.com")
    employer = make_employer("history-employer@example.com")
    application = create_application(student, make_job(employer))
    client = APIClient()
    client.force_authenticate(employer)
    client.patch(
        reverse("application-update-status", args=[application.id]),
        {"status": Application.Status.SHORTLISTED},
        format="json",
    )

    response = client.get(
        reverse("application-history", args=[application.id])
    )

    assert response.status_code == 200
    assert [item["to_status"] for item in response.data] == [
        Application.Status.APPLIED,
        Application.Status.SHORTLISTED,
    ]


def test_every_valid_status_transition_is_allowed():
    for from_status, allowed_statuses in STATUS_TRANSITIONS.items():
        student = make_student(f"valid-{from_status}@example.com")
        employer = make_employer(f"valid-{from_status}-employer@example.com")
        application = make_application(
            student, employer, f"Valid {from_status}", from_status
        )
        for to_status in allowed_statuses:
            application.status = from_status
            application.save(update_fields=["status"])
            transition_application_status(application, to_status, employer)
            assert application.status == to_status


def test_every_invalid_status_transition_is_rejected():
    all_statuses = {choice[0] for choice in Application.Status.choices}
    for from_status, allowed_statuses in STATUS_TRANSITIONS.items():
        student = make_student(f"invalid-{from_status}@example.com")
        employer = make_employer(f"invalid-{from_status}-employer@example.com")
        application = make_application(
            student, employer, f"Invalid {from_status}", from_status
        )
        for to_status in all_statuses - allowed_statuses:
            with pytest.raises(InvalidStatusTransition):
                transition_application_status(application, to_status, employer)
