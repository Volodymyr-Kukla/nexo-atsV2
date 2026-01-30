from rest_framework.permissions import BasePermission


class CanCreateProject(BasePermission):
    """
    Забороняємо створення для VIEWER.
    Дозволяємо ADMIN/HR_MANAGER/RECRUITER (+ superuser).
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return getattr(user, "role", None) in ("ADMIN", "HR_MANAGER", "RECRUITER")


class IsProjectMemberOrAdminHR(BasePermission):
    """
    Доступ до перегляду проєкту: учасник проєкту або ADMIN/HR/superuser.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or getattr(user, "role", None) in ("ADMIN", "HR_MANAGER"):
            return True
        return obj.memberships.filter(user=user).exists()


class IsProjectOwnerOrAdminHR(BasePermission):
    """
    Редагування/видалення/керування учасниками: owner або ADMIN/HR/superuser.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or getattr(user, "role", None) in ("ADMIN", "HR_MANAGER"):
            return True
        return obj.owner_id == user.id
