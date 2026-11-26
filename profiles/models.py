from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import User

from .validators import validate_pdf_file, validate_resume_size


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def save(self, *args, **kwargs):
        self.name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    full_name = models.CharField(max_length=255)
    university = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    cgpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
    )
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    bio = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name="students")
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    resume = models.FileField(
        upload_to="resumes/",
        blank=True,
        null=True,
        validators=[validate_pdf_file, validate_resume_size],
    )

    def __str__(self):
        return self.full_name


class EmployerProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employer_profile"
    )
    company_name = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.company_name
