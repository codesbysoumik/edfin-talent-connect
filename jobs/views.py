from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from applications.models import Application
from applications.permissions import IsStudent
from matching.services import calculate_match
from profiles.models import StudentProfile

from .filters import JobPostFilter
from .models import JobPost
from .pagination import JobPostPagination
from .permissions import IsEmployer, IsJobOwner
from .serializers import (
    JobMatchSerializer,
    JobPostSerializer,
    RecommendedJobSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List active jobs",
        responses=JobPostSerializer(many=True),
        tags=["jobs"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a job",
        responses=JobPostSerializer,
        tags=["jobs"],
    ),
    create=extend_schema(
        summary="Create a job as a verified employer",
        request=JobPostSerializer,
        responses={201: JobPostSerializer},
        tags=["jobs"],
    ),
    update=extend_schema(
        summary="Replace an owned job",
        request=JobPostSerializer,
        responses=JobPostSerializer,
        tags=["jobs"],
    ),
    partial_update=extend_schema(
        summary="Update an owned job",
        request=JobPostSerializer,
        responses=JobPostSerializer,
        tags=["jobs"],
    ),
    destroy=extend_schema(
        summary="Delete an owned job",
        responses={204: None},
        tags=["jobs"],
    ),
    recommended=extend_schema(
        summary="List jobs recommended for the student",
        responses=RecommendedJobSerializer(many=True),
        tags=["matching"],
    ),
    matches=extend_schema(
        summary="Rank applicants for an owned job",
        responses=JobMatchSerializer(many=True),
        tags=["matching"],
    ),
)
class JobPostViewSet(viewsets.ModelViewSet):
    queryset = JobPost.objects.select_related(
        "employer", "employer__user"
    ).prefetch_related("required_skills")
    serializer_class = JobPostSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = JobPostFilter
    search_fields = ("title",)
    ordering_fields = ("title", "created_at", "deadline", "min_cgpa")
    ordering = ("-created_at",)
    pagination_class = JobPostPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            return queryset.filter(is_active=True)
        return queryset

    def get_permissions(self):
        if self.action == "recommended":
            permission_classes = (IsStudent,)
        elif self.action == "matches":
            permission_classes = (IsEmployer, IsJobOwner)
        elif self.action in ("list", "retrieve"):
            permission_classes = (permissions.AllowAny,)
        elif self.action == "create":
            permission_classes = (IsEmployer,)
        else:
            permission_classes = (IsEmployer, IsJobOwner)
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        try:
            employer = self.request.user.employer_profile
        except AttributeError as error:
            raise PermissionDenied("Employer profile is required.") from error
        if not employer.is_verified:
            raise PermissionDenied("Only verified employers can post jobs.")
        serializer.save(employer=employer)

    @action(
        detail=False,
        methods=["get"],
        url_path="recommended",
        permission_classes=(IsStudent,),
    )
    def recommended(self, request):
        try:
            student_profile = (
                StudentProfile.objects.prefetch_related("skills")
                .get(user=request.user)
            )
        except StudentProfile.DoesNotExist as error:
            raise ValidationError("Student profile is required.") from error

        jobs = self.get_queryset().filter(is_active=True)
        results = []
        for job in jobs:
            result = calculate_match(student_profile, job)
            results.append(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "job_type": job.job_type,
                    "location": job.location,
                    **result,
                }
            )
        results.sort(key=lambda item: (-item["match_score"], item["title"]))
        return Response(results)

    @action(
        detail=True,
        methods=["get"],
        url_path="matches",
        permission_classes=(permissions.IsAuthenticated, IsEmployer, IsJobOwner),
    )
    def matches(self, request, *args, **kwargs):
        job = self.get_object()
        applications = (
            Application.objects.filter(job=job)
            .select_related("student", "student__student_profile")
            .prefetch_related("student__student_profile__skills")
        )
        results = []
        for application in applications:
            try:
                student_profile = application.student.student_profile
            except AttributeError:
                continue
            result = calculate_match(student_profile, job)
            results.append(
                {
                    "application_id": application.id,
                    "student_id": application.student_id,
                    **result,
                }
            )
        results.sort(key=lambda item: -item["match_score"])
        return Response(results)
