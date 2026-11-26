from typing import ClassVar

from django.db import models

from accounts.models import User
from jobs.models import JobPost


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        OFFERED = "offered", "Offered"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="applications"
    )
    job = models.ForeignKey(
        JobPost, on_delete=models.CASCADE, related_name="applications"
    )
    cover_letter = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.APPLIED
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["student", "job"], name="unique_student_job_application"
            )
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["job", "status"]),
        ]
        ordering: ClassVar[list[str]] = ["-applied_at"]

    def __str__(self):
        return f"{self.student.email} - {self.job.title}"


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="history"
    )
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    from_status = models.CharField(
        max_length=20, choices=Application.Status.choices, blank=True, null=True
    )
    to_status = models.CharField(max_length=20, choices=Application.Status.choices)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["changed_at", "id"]

    def __str__(self):
        return f"{self.application_id}: {self.from_status} -> {self.to_status}"
