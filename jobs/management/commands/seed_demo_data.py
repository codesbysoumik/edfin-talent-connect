from datetime import timedelta
from random import Random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from accounts.models import User
from applications.models import Application, ApplicationStatusHistory
from applications.services import transition_application_status
from jobs.models import JobPost
from profiles.models import EmployerProfile, Skill, StudentProfile

DEMO_PASSWORD = "DemoPass123!"
STUDENT_COUNT = 30
EMPLOYER_COUNT = 8
JOB_COUNT = 40
APPLICATION_COUNT = 150

SKILL_POOL = (
    "Python",
    "Django",
    "REST API",
    "JavaScript",
    "React",
    "SQL",
    "PostgreSQL",
    "Git",
    "Docker",
    "Data Analysis",
    "Excel",
    "Machine Learning",
    "Communication",
    "Project Management",
    "Figma",
    "Linux",
    "Testing",
    "Cybersecurity",
    "Financial Modeling",
    "Research",
)
LOCATIONS = ("Dhaka", "Chattogram", "Sylhet", "Rajshahi", "Remote")
DEPARTMENTS = (
    "Computer Science",
    "Business Administration",
    "Electrical Engineering",
    "Economics",
    "Finance",
)
JOB_TITLES = (
    "Backend Engineering Intern",
    "Data Analyst",
    "Financial Research Assistant",
    "Frontend Developer",
    "Product Operations Associate",
    "Software Engineer",
    "Business Intelligence Intern",
    "Cybersecurity Analyst",
)
JOB_TYPES = tuple(JobPost.JobType.values)
APPLICATION_TARGETS = (
    Application.Status.APPLIED,
    Application.Status.SHORTLISTED,
    Application.Status.INTERVIEW,
    Application.Status.OFFERED,
    Application.Status.HIRED,
    Application.Status.REJECTED,
    Application.Status.WITHDRAWN,
)


class Command(BaseCommand):
    help = "Create or update deterministic demo data for local development."

    @transaction.atomic
    def handle(self, *args, **options):
        fake = Faker("en_US")
        fake.seed_instance(2026)
        rng = Random(2026)

        skills = {
            name.lower(): Skill.objects.get_or_create(name=name.lower())[0]
            for name in SKILL_POOL
        }
        skill_values = list(skills.values())
        students = self._seed_students(fake, rng, skill_values)
        employers = self._seed_employers(fake)
        jobs = self._seed_jobs(fake, rng, employers, skill_values)
        self._seed_applications(fake, rng, students, jobs)
        self._seed_admin()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(students)} students, {len(employers)} employers, "
                f"{len(jobs)} jobs, and {APPLICATION_COUNT} applications."
            )
        )

    def _save_demo_user(self, user, role, *, is_staff=False, is_superuser=False):
        user.role = role
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_active = True
        user.set_password(DEMO_PASSWORD)
        user.save(
            update_fields=[
                "password",
                "role",
                "is_staff",
                "is_superuser",
                "is_active",
            ]
        )

    def _seed_students(self, fake, rng, skill_values):
        students = []
        for index in range(STUDENT_COUNT):
            email = "student@demo.com" if index == 0 else f"student{index:02d}@demo.com"
            user, _ = User.objects.get_or_create(
                email=email, defaults={"role": User.Role.STUDENT}
            )
            self._save_demo_user(user, User.Role.STUDENT)
            profile, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": fake.name(),
                    "university": f"University {index + 1}",
                    "department": DEPARTMENTS[index % len(DEPARTMENTS)],
                },
            )
            profile.full_name = "Demo Student" if index == 0 else fake.name()
            profile.university = f"University {index + 1}"
            profile.department = DEPARTMENTS[index % len(DEPARTMENTS)]
            profile.cgpa = 2.75 + (index % 13) / 10
            profile.save()
            profile.skills.set(rng.sample(skill_values, rng.randint(3, 7)))
            students.append(user)
        return students

    def _seed_employers(self, fake):
        employers = []
        for index in range(EMPLOYER_COUNT):
            email = "employer@demo.com" if index == 0 else f"employer{index:02d}@demo.com"
            user, _ = User.objects.get_or_create(
                email=email, defaults={"role": User.Role.EMPLOYER}
            )
            self._save_demo_user(user, User.Role.EMPLOYER)
            profile, _ = EmployerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": "Demo Financial Talent" if index == 0 else fake.company(),
                    "location": LOCATIONS[index % len(LOCATIONS)],
                },
            )
            profile.company_name = (
                "Demo Financial Talent" if index == 0 else fake.company()
            )
            profile.location = LOCATIONS[index % len(LOCATIONS)]
            profile.is_verified = True
            profile.save()
            employers.append(user)
        return employers

    def _seed_jobs(self, fake, rng, employers, skill_values):
        jobs = []
        for index in range(JOB_COUNT):
            employer = employers[index % len(employers)]
            title = f"Demo {JOB_TITLES[index % len(JOB_TITLES)]} {index + 1:02d}"
            job, _ = JobPost.objects.get_or_create(
                employer=employer.employer_profile,
                title=title,
                defaults={
                    "description": fake.paragraph(nb_sentences=3),
                    "job_type": JOB_TYPES[index % len(JOB_TYPES)],
                    "location": LOCATIONS[index % len(LOCATIONS)],
                    "min_cgpa": 2.5 + (index % 10) / 10,
                    "deadline": timezone.now() + timedelta(days=30 + index),
                },
            )
            job.description = fake.paragraph(nb_sentences=3)
            job.job_type = JOB_TYPES[index % len(JOB_TYPES)]
            job.location = LOCATIONS[index % len(LOCATIONS)]
            job.min_cgpa = 2.5 + (index % 10) / 10
            job.deadline = timezone.now() + timedelta(days=30 + index)
            job.is_active = True
            job.save()
            job.required_skills.set(rng.sample(skill_values, rng.randint(2, 5)))
            jobs.append(job)
        return jobs

    def _seed_applications(self, fake, rng, students, jobs):
        pairs = [(student, job) for student in students for job in jobs]
        rng.shuffle(pairs)
        for index, (student, job) in enumerate(pairs[:APPLICATION_COUNT]):
            target_status = APPLICATION_TARGETS[index % len(APPLICATION_TARGETS)]
            application, created = Application.objects.get_or_create(
                student=student,
                job=job,
                defaults={"cover_letter": fake.paragraph(nb_sentences=2)},
            )
            if not created:
                continue

            ApplicationStatusHistory.objects.create(
                application=application,
                changed_by=student,
                from_status=None,
                to_status=Application.Status.APPLIED,
            )
            status_path = {
                Application.Status.APPLIED: (),
                Application.Status.SHORTLISTED: (Application.Status.SHORTLISTED,),
                Application.Status.INTERVIEW: (
                    Application.Status.SHORTLISTED,
                    Application.Status.INTERVIEW,
                ),
                Application.Status.OFFERED: (
                    Application.Status.SHORTLISTED,
                    Application.Status.INTERVIEW,
                    Application.Status.OFFERED,
                ),
                Application.Status.HIRED: (
                    Application.Status.SHORTLISTED,
                    Application.Status.INTERVIEW,
                    Application.Status.OFFERED,
                    Application.Status.HIRED,
                ),
                Application.Status.REJECTED: (Application.Status.REJECTED,),
                Application.Status.WITHDRAWN: (Application.Status.WITHDRAWN,),
            }[target_status]
            for next_status in status_path:
                transition_application_status(
                    application, next_status, job.employer.user
                )

    def _seed_admin(self):
        admin, _ = User.objects.get_or_create(
            email="admin@demo.com", defaults={"role": User.Role.ADMIN}
        )
        self._save_demo_user(
            admin, User.Role.ADMIN, is_staff=True, is_superuser=True
        )
