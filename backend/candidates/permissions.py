from rest_framework.permissions import BasePermission


class CanWriteCandidates(BasePermission):
    """
    Забороняємо створення/редагування/архівацію для VIEWER.
    Дозволяємо ADMIN/HR_MANAGER/RECRUITER (+ superuser).
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return getattr(user, "role", None) in ("ADMIN", "HR_MANAGER", "RECRUITER")
