from rest_framework.permissions import BasePermission

from accounts.models import User


class IsStudent(BasePermission):
    message = "Only students can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.STUDENT
        )


class IsApplicationParticipant(BasePermission):
    message = "You do not have access to this application."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.STUDENT, User.Role.EMPLOYER)
        )

    def has_object_permission(self, request, view, obj):
        return obj.student_id == request.user.id or obj.job.employer.user_id == request.user.id
