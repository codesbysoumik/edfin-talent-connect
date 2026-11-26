from rest_framework.permissions import BasePermission

from accounts.models import User


class IsEmployer(BasePermission):
    message = "Only employers can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.EMPLOYER
        )


class IsJobOwner(BasePermission):
    message = "Only the job owner can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.employer.user_id == request.user.id
