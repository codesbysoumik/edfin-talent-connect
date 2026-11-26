from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from profiles.models import EmployerProfile, StudentProfile

from .serializers import MeSerializer, RegisterSerializer

User = get_user_model()


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


@extend_schema(
    summary="Register a student or employer",
    request=RegisterSerializer,
    responses={201: RegisterSerializer},
    tags=["auth"],
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    @transaction.atomic
    def perform_create(self, serializer):
        user = serializer.save()
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user, full_name=user.email)
        else:
            EmployerProfile.objects.create(user=user, company_name=user.email)


@extend_schema(
    summary="Obtain JWT access and refresh tokens",
    request=TokenObtainPairSerializer,
    responses=TokenObtainPairSerializer,
    tags=["auth"],
)
class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)


@extend_schema(
    summary="Refresh an access token",
    request=TokenRefreshSerializer,
    responses=TokenRefreshSerializer,
    tags=["auth"],
)
class RefreshView(TokenRefreshView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)


@extend_schema(
    summary="Return the authenticated user",
    responses=MeSerializer,
    tags=["auth"],
)
class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = (AuthRateThrottle,)

    def get_object(self):
        return self.request.user
