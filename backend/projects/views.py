# Create your views here.
import csv
from datetime import datetime
from io import StringIO

from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from pipeline.models import Application, Stage
from pipeline.permissions import CanWriteProjectPipeline
from pipeline.serializers import ApplicationCardSerializer, KanbanReorderSerializer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import ProjectFilter
from .models import Project, ProjectMember
from .permissions import CanCreateProject, IsProjectMemberOrAdminHR, IsProjectOwnerOrAdminHR
from .serializers import (
    ProjectCreateUpdateSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectMemberCreateSerializer,
    ProjectMemberSerializer,
    StageSummarySerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    filterset_class = ProjectFilter
    search_fields = ["title", "description", "location", "department"]
    ordering_fields = ["created_at", "deadline", "title", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user

        qs = (
            Project.objects.all()
            .select_related("owner")
            .annotate(
                candidates_count=Count(
                    "applications",
                    filter=Q(applications__is_archived=False),
                    distinct=True,
                ),
                new_count=Count(
                    "applications",
                    filter=Q(
                        applications__is_archived=False,
                        applications__current_stage__system_key="new",
                    ),
                    distinct=True,
                ),
            )
        )

        # ADMIN/HR бачать все, інші — тільки свої (учасник)
        if user.is_superuser or getattr(user, "role", None) in ("ADMIN", "HR_MANAGER"):
            return qs

        return qs.filter(memberships__user=user).distinct()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanCreateProject()]

        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsProjectOwnerOrAdminHR()]

        if self.action in ("retrieve", "summary", "members"):
            return [IsAuthenticated(), IsProjectMemberOrAdminHR()]

        # list, stats, export, import — фільтруються queryset-ом; доступ лише authenticated
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProjectCreateUpdateSerializer
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectListSerializer

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        Для верхніх карточок на сторінці Проекти:
        total / in_progress / pending / closed
        Повертає для поточного видимого scope (з урахуванням прав).
        """
        qs = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "total": qs.count(),
                "in_progress": qs.filter(status=Project.Status.IN_PROGRESS).count(),
                "pending": qs.filter(status=Project.Status.PENDING).count(),
                "closed": qs.filter(status=Project.Status.CLOSED).count(),
            }
        )

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """
        Для верхнього рядка в Project view: кількість кандидатів у кожній стадії.
        """
        project = self.get_object()

        stages = (
            Stage.objects.filter(project=project)
            .annotate(
                candidates_count=Count(
                    "applications",
                    filter=Q(applications__is_archived=False),
                    distinct=True,
                )
            )
            .order_by("order", "id")
        )

        data = {
            "project_id": project.id,
            "stages": StageSummarySerializer(stages, many=True).data,
            "total_candidates": project.applications.filter(is_archived=False).count(),
        }
        return Response(data)

    @action(detail=True, methods=["get"], url_path="kanban")
    def kanban(self, request, pk=None):
        """
        Повертає дані для Kanban дошки:
        stages[] + applications[] у кожній колонці.
        """
        project = self.get_object()

        stages = Stage.objects.filter(project=project).order_by("order", "id")
        apps = (
            Application.objects.filter(project=project, is_archived=False)
            .select_related("candidate", "current_stage")
            .prefetch_related("candidate__skills")
            .order_by("current_stage__order", "position_in_stage", "-updated_at", "id")
        )

        stage_map = {s.id: [] for s in stages}
        for app in apps:
            stage_map.setdefault(app.current_stage_id, []).append(app)

        result_stages = []
        for stage in stages:
            items = stage_map.get(stage.id, [])
            result_stages.append(
                {
                    "id": stage.id,
                    "name": stage.name,
                    "system_key": stage.system_key,
                    "order": stage.order,
                    "is_final": stage.is_final,
                    "candidates_count": len(items),
                    "applications": ApplicationCardSerializer(items, many=True).data,
                }
            )

        return Response({"project_id": project.id, "stages": result_stages})

    @action(detail=True, methods=["post"], url_path=r"kanban/reorder")
    def kanban_reorder(self, request, pk=None):
        """
        Оновлює position_in_stage для карток у конкретній колонці.
        body: { "stage_id": <id>, "ordered_application_ids": [..] }
        """
        project = self.get_object()

        # write permission
        if not CanWriteProjectPipeline().has_object_permission(request, self, project):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = KanbanReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stage_id = serializer.validated_data["stage_id"]
        ordered_ids = serializer.validated_data["ordered_application_ids"]

        stage = Stage.objects.filter(project=project, id=stage_id).first()
        if not stage:
            return Response(
                {"detail": "Stage not found in this project"}, status=status.HTTP_404_NOT_FOUND
            )

        qs = Application.objects.filter(
            project=project, current_stage=stage, is_archived=False
        ).order_by("position_in_stage", "id")
        apps = list(qs)
        apps_by_id = {a.id: a for a in apps}

        # validate ids belong to this stage
        invalid = [aid for aid in ordered_ids if aid not in apps_by_id]
        if invalid:
            return Response(
                {
                    "detail": "Some application ids do not belong to this stage",
                    "invalid_ids": invalid,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ensure uniqueness
        seen = set()
        unique_ordered = []
        for aid in ordered_ids:
            if aid in seen:
                continue
            seen.add(aid)
            unique_ordered.append(aid)

        remaining = [a.id for a in apps if a.id not in seen]
        final_ids = unique_ordered + remaining

        with transaction.atomic():
            for idx, aid in enumerate(final_ids, start=1):
                Application.objects.filter(id=aid).update(position_in_stage=idx)

        return Response(
            {"stage_id": stage.id, "ordered_application_ids": final_ids}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        """
        GET  /projects/{id}/members/  -> список учасників
        POST /projects/{id}/members/  -> додати учасника (owner/admin/hr only)
        """
        project = self.get_object()

        if request.method == "GET":
            memberships = (
                ProjectMember.objects.filter(project=project).select_related("user").order_by("id")
            )
            return Response(ProjectMemberSerializer(memberships, many=True).data)

        # POST
        # Тільки owner/admin/hr
        if not IsProjectOwnerOrAdminHR().has_object_permission(request, self, project):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        role = serializer.validated_data.get("role", ProjectMember.Role.RECRUITER)

        # не даємо додати owner вдруге
        member, created = ProjectMember.objects.get_or_create(
            project=project,
            user_id=user_id,
            defaults={"role": role},
        )
        if not created:
            # якщо існує — оновимо роль
            member.role = role
            member.save()

        return Response(ProjectMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path=r"members/(?P<member_id>\d+)")
    def member_detail(self, request, pk=None, member_id=None):
        """
        PATCH  /projects/{id}/members/{member_id}/  -> змінити роль
        DELETE /projects/{id}/members/{member_id}/  -> видалити учасника
        """
        project = self.get_object()

        # тільки owner/admin/hr
        if not IsProjectOwnerOrAdminHR().has_object_permission(request, self, project):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        membership = (
            ProjectMember.objects.filter(project=project, id=member_id)
            .select_related("user")
            .first()
        )
        if not membership:
            return Response({"detail": "Member not found"}, status=status.HTTP_404_NOT_FOUND)

        # не дозволяємо видалити owner membership
        if membership.user_id == project.owner_id and membership.role == ProjectMember.Role.OWNER:
            return Response(
                {"detail": "Cannot modify project owner membership"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "DELETE":
            membership.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH: оновити роль
        role = request.data.get("role")
        if role not in dict(ProjectMember.Role.choices):
            return Response({"detail": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

        membership.role = role
        membership.save()
        return Response(ProjectMemberSerializer(membership).data)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """
        CSV export проєктів (з урахуванням прав і фільтрів).
        """
        qs = self.filter_queryset(self.get_queryset()).order_by("id")

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "title",
                "status",
                "location",
                "is_remote",
                "department",
                "deadline",
                "owner_email",
                "created_at",
            ]
        )

        for p in qs:
            writer.writerow(
                [
                    p.id,
                    p.title,
                    p.status,
                    p.location,
                    "1" if p.is_remote else "0",
                    p.department,
                    p.deadline.isoformat() if p.deadline else "",
                    p.owner.email if p.owner_id else "",
                    p.created_at.isoformat() if p.created_at else "",
                ]
            )

        resp = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="projects.csv"'
        return resp

    @action(detail=False, methods=["post"], url_path="import")
    def import_projects(self, request):
        """
        Мінімальний CSV import.
        Очікує multipart/form-data з файлом у полі "file".
        """
        if "file" not in request.FILES:
            return Response(
                {"detail": 'Provide file in "file" field.'}, status=status.HTTP_400_BAD_REQUEST
            )

        # лише ADMIN/HR/RECRUITER (не VIEWER)
        if not CanCreateProject().has_permission(request, self):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        f = request.FILES["file"]
        content = f.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(StringIO(content))

        status_map = {
            "IN_PROGRESS": Project.Status.IN_PROGRESS,
            "PENDING": Project.Status.PENDING,
            "CLOSED": Project.Status.CLOSED,
            "В процесі": Project.Status.IN_PROGRESS,
            "Очікують": Project.Status.PENDING,
            "Закриті": Project.Status.CLOSED,
        }

        created = 0
        errors = []

        for idx, row in enumerate(reader, start=2):  # 1 — header
            title = (row.get("title") or "").strip()
            if not title:
                errors.append({"row": idx, "error": "Missing title"})
                continue

            status_val = (row.get("status") or Project.Status.IN_PROGRESS).strip()
            status_val = status_map.get(status_val, Project.Status.IN_PROGRESS)

            deadline_raw = (row.get("deadline") or "").strip()
            deadline = None
            if deadline_raw:
                try:
                    deadline = datetime.strptime(deadline_raw, "%Y-%m-%d").date()
                except ValueError:
                    errors.append(
                        {
                            "row": idx,
                            "error": f"Invalid deadline format: {deadline_raw} (use YYYY-MM-DD)",
                        }
                    )
                    continue

            Project.objects.create(
                title=title,
                description=(row.get("description") or "").strip(),
                status=status_val,
                location=(row.get("location") or "").strip(),
                is_remote=(row.get("is_remote") or "").strip()
                in ("1", "true", "True", "yes", "так"),
                department=(row.get("department") or "").strip(),
                deadline=deadline,
                owner=request.user,
            )
            created += 1

        return Response({"created": created, "errors": errors}, status=status.HTTP_200_OK)
