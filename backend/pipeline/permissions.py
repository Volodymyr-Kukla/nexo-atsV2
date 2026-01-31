from projects.models import ProjectMember
from rest_framework.permissions import BasePermission


class IsProjectMemberOrAdminHR(BasePermission):
    """
    Доступ до читання: учасник проєкту або ADMIN/HR/superuser.
    Працює для obj=Project або obj=Application (де є .project).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or getattr(user, "role", None) in ("ADMIN", "HR_MANAGER"):
            return True

        project = getattr(obj, "project", obj)
        return ProjectMember.objects.filter(project=project, user=user).exists()


class CanWriteProjectPipeline(BasePermission):
    """
    Доступ до змін пайплайна: ADMIN/HR/superuser або учасник проєкту з role != VIEWER.
    Працює для obj=Project або obj=Application.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or getattr(user, "role", None) in ("ADMIN", "HR_MANAGER"):
            return True

        project = getattr(obj, "project", obj)
        return (
            ProjectMember.objects.filter(project=project, user=user)
            .exclude(role=ProjectMember.Role.VIEWER)
            .exists()
        )
