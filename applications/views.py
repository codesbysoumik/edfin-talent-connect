from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import User
from jobs.models import JobPost

from .models import Application
from .permissions import IsApplicationParticipant, IsStudent
from .serializers import (
    ApplicationSerializer,
    ApplicationStatusHistorySerializer,
    ApplicationStatusSerializer,
    ApplySerializer,
)
from .services import (
    DuplicateApplication,
    InvalidStatusTransition,
    create_application,
    transition_application_status,
)


class ApplyView(generics.CreateAPIView):
    serializer_class = ApplySerializer
    permission_classes = (IsStudent,)

    def create(self, request, *args, **kwargs):
        job = get_object_or_404(JobPost, pk=kwargs["job_id"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = create_application(
                request.user, job, serializer.validated_data.get("cover_letter", "")
            )
        except DuplicateApplication as error:
            raise ValidationError(str(error)) from error
        except ValueError as error:
            raise ValidationError(str(error)) from error

        return Response(
            ApplicationSerializer(application).data, status=status.HTTP_201_CREATED
        )


class ApplicationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ApplicationSerializer
    permission_classes = (IsApplicationParticipant,)

    def get_queryset(self):
        queryset = Application.objects.select_related(
            "student", "job", "job__employer", "job__employer__user"
        ).prefetch_related("history__changed_by")
        if self.request.user.role == User.Role.STUDENT:
            return queryset.filter(student=self.request.user)
        if self.request.user.role == User.Role.EMPLOYER:
            return queryset.filter(job__employer__user=self.request.user)
        return queryset.none()

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, *args, **kwargs):
        application = self.get_object()
        serializer = ApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_status = serializer.validated_data["status"]

        if request.user.role == User.Role.STUDENT:
            if application.student_id != request.user.id:
                raise PermissionDenied("Only the applicant can withdraw this application.")
            if to_status != Application.Status.WITHDRAWN:
                raise PermissionDenied("Students can only withdraw applications.")
        elif to_status == Application.Status.WITHDRAWN:
            raise PermissionDenied("Employers cannot withdraw applications.")

        try:
            application = transition_application_status(
                application, to_status, request.user
            )
        except InvalidStatusTransition as error:
            raise ValidationError(str(error)) from error
        return Response(ApplicationSerializer(application).data)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, *args, **kwargs):
        application = self.get_object()
        history = application.history.select_related("changed_by").all()
        serializer = ApplicationStatusHistorySerializer(history, many=True)
        return Response(serializer.data)
