from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import generics, permissions
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from profiles.models import EmployerProfile, StudentProfile

from .serializers import MeSerializer, RegisterSerializer

User = get_user_model()


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


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


class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)


class RefreshView(TokenRefreshView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)


class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = (AuthRateThrottle,)

    def get_object(self):
        return self.request.user
