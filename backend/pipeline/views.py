# Create your views here.
from django.db import IntegrityError, transaction
from django.db.models import Max
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import ApplicationFilter
from .models import Application, Stage, StageChangeEvent
from .permissions import CanWriteProjectPipeline, IsProjectMemberOrAdminHR
from .serializers import (
    ApplicationCardSerializer,
    ApplicationCreateSerializer,
    ApplicationMoveSerializer,
)


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    filterset_class = ApplicationFilter
    ordering_fields = ["created_at", "updated_at", "position_in_stage"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Application.objects.all()
            .select_related("project", "candidate", "current_stage")
            .prefetch_related("candidate__skills")
        )

        # дефолт: не показуємо архів
        if self.request.query_params.get("is_archived") is None:
            qs = qs.filter(is_archived=False)

        # ADMIN/HR бачать все; інші — лише проєкти, де вони учасники
        if user.is_superuser or getattr(user, "role", None) in ("ADMIN", "HR_MANAGER"):
            return qs

        return qs.filter(project__memberships__user=user).distinct()

    def get_permissions(self):
        if self.action in ("create", "move", "destroy"):
            return [IsAuthenticated()]
        # list/retrieve також вимагає auth; object-level доступ контролюється queryset-ом + check below
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationCreateSerializer
        return ApplicationCardSerializer

    def retrieve(self, request, *args, **kwargs):
        app = self.get_object()
        # object permission (read)
        if not IsProjectMemberOrAdminHR().has_object_permission(request, self, app):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(ApplicationCardSerializer(app).data)

    def list(self, request, *args, **kwargs):
        # queryset already filtered by membership
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = serializer.validated_data["project"]
        candidate = serializer.validated_data["candidate"]
        stage = serializer.validated_data["stage"]

        # write permission
        if not CanWriteProjectPipeline().has_object_permission(request, self, project):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        # позиція: додаємо в кінець колонки
        max_pos = (
            Application.objects.filter(project=project, current_stage=stage, is_archived=False)
            .aggregate(Max("position_in_stage"))
            .get("position_in_stage__max")
            or 0
        )
        position = max_pos + 1

        try:
            with transaction.atomic():
                app = Application.objects.create(
                    project=project,
                    candidate=candidate,
                    current_stage=stage,
                    position_in_stage=position,
                )
                StageChangeEvent.objects.create(
                    application=app,
                    from_stage=None,
                    to_stage=stage,
                    changed_by=request.user,
                )
        except IntegrityError:
            return Response(
                {"detail": "Candidate already exists in this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app = (
            Application.objects.select_related("project", "candidate", "current_stage")
            .prefetch_related("candidate__skills")
            .get(id=app.id)
        )
        return Response(ApplicationCardSerializer(app).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        app = self.get_object()

        # read access check
        if not IsProjectMemberOrAdminHR().has_object_permission(request, self, app):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        # write access check
        if not CanWriteProjectPipeline().has_object_permission(request, self, app):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ApplicationMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_stage_id = serializer.validated_data["to_stage_id"]

        to_stage = Stage.objects.filter(project=app.project, id=to_stage_id).first()
        if not to_stage:
            return Response(
                {"detail": "Stage not found in this project"}, status=status.HTTP_400_BAD_REQUEST
            )

        from_stage = app.current_stage
        from_stage_id = getattr(from_stage, "id", None)

        if from_stage_id == to_stage.id:
            # no-op
            app = (
                Application.objects.select_related("project", "candidate", "current_stage")
                .prefetch_related("candidate__skills")
                .get(id=app.id)
            )
            return Response(ApplicationCardSerializer(app).data, status=status.HTTP_200_OK)

        max_pos = (
            Application.objects.filter(
                project=app.project, current_stage=to_stage, is_archived=False
            )
            .aggregate(Max("position_in_stage"))
            .get("position_in_stage__max")
            or 0
        )

        with transaction.atomic():
            app.current_stage = to_stage
            app.position_in_stage = max_pos + 1
            app.save()  # оновить updated_at

            StageChangeEvent.objects.create(
                application=app,
                from_stage=from_stage,
                to_stage=to_stage,
                changed_by=request.user,
            )

        app = (
            Application.objects.select_related("project", "candidate", "current_stage")
            .prefetch_related("candidate__skills")
            .get(id=app.id)
        )
        return Response(ApplicationCardSerializer(app).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        app = self.get_object()

        if not IsProjectMemberOrAdminHR().has_object_permission(request, self, app):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if not CanWriteProjectPipeline().has_object_permission(request, self, app):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        app.is_archived = True
        app.save(update_fields=["is_archived"])
        return Response(status=status.HTTP_204_NO_CONTENT)
