from typing import ClassVar

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from profiles.models import EmployerProfile, Skill


class JobPost(models.Model):
    class JobType(models.TextChoices):
        INTERNSHIP = "internship", "Internship"
        PART_TIME = "part_time", "Part time"
        FULL_TIME = "full_time", "Full time"
        REMOTE = "remote", "Remote"

    employer = models.ForeignKey(
        EmployerProfile, on_delete=models.CASCADE, related_name="job_posts"
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    job_type = models.CharField(max_length=20, choices=JobType.choices)
    location = models.CharField(max_length=255)
    required_skills = models.ManyToManyField(Skill, related_name="job_posts", blank=True)
    min_cgpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
    )
    deadline = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["job_type"]),
            models.Index(fields=["location"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["deadline"]),
        ]
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self):
        return self.title
