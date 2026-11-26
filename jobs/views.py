from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter

from .filters import JobPostFilter
from .models import JobPost
from .pagination import JobPostPagination
from .permissions import IsEmployer, IsJobOwner
from .serializers import JobPostSerializer


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
        if self.action in ("list", "retrieve"):
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
