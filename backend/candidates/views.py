# Create your views here.
from django.db import models
from django.db.models import OuterRef, Q, Subquery
from pipeline.models import Application
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import CandidateFilter
from .models import Candidate, Skill
from .permissions import CanWriteCandidates
from .serializers import (
    CandidateDetailSerializer,
    CandidateListSerializer,
    CandidateUpsertSerializer,
    SkillSerializer,
)


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    filterset_class = CandidateFilter
    search_fields = ["first_name", "last_name", "email", "phone", "city"]
    ordering_fields = ["created_at", "experience_years", "rating", "last_name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user

        qs = Candidate.objects.all().prefetch_related("skills", "experiences")

        # дефолт: не показуємо архів, якщо is_archived не передано
        if self.request.query_params.get("is_archived") is None:
            qs = qs.filter(is_archived=False)

        # annotate status/stage/submitted_at від Application
        project_id = self.request.query_params.get("project_id")
        app_qs = Application.objects.filter(candidate_id=OuterRef("pk"), is_archived=False)

        if project_id:
            try:
                app_qs = app_qs.filter(project_id=int(project_id))
            except ValueError:
                # некоректний project_id -> порожня підвибірка, статус буде null
                app_qs = app_qs.none()

        app_qs = app_qs.order_by("-updated_at")

        qs = qs.annotate(
            application_id=Subquery(app_qs.values("id")[:1]),
            status_project_id=Subquery(app_qs.values("project_id")[:1]),
            stage_system_key=Subquery(app_qs.values("current_stage__system_key")[:1]),
            stage_name=Subquery(app_qs.values("current_stage__name")[:1]),
            submitted_at=Subquery(
                app_qs.values("created_at")[:1], output_field=models.DateTimeField()
            ),
        )

        # Visibility scope (MVP):
        # ADMIN/HR -> бачать все
        # інші -> кандидати у їхніх проєктах + "unassigned" (без applications)
        if user.is_superuser or getattr(user, "role", None) in ("ADMIN", "HR_MANAGER"):
            return qs

        return qs.filter(
            Q(applications__project__memberships__user=user) | Q(applications__isnull=True)
        ).distinct()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "rate"):
            return [IsAuthenticated(), CanWriteCandidates()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CandidateUpsertSerializer
        if self.action == "retrieve":
            return CandidateDetailSerializer
        return CandidateListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = serializer.save()

        # повертаємо detail формат
        candidate = self.get_queryset().filter(id=candidate.id).first() or candidate
        return Response(CandidateDetailSerializer(candidate).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        candidate = serializer.save()

        candidate = self.get_queryset().filter(id=candidate.id).first() or candidate
        return Response(CandidateDetailSerializer(candidate).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete: замість фізичного видалення ставимо is_archived=True
        """
        instance = self.get_object()
        instance.is_archived = True
        instance.save(update_fields=["is_archived"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="rate")
    def rate(self, request, pk=None):
        """
        Швидке оновлення рейтингу (для UI зі зірками).
        body: {"rating": 0..5}
        """
        instance = self.get_object()
        try:
            rating = int(request.data.get("rating"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "rating must be integer 0..5"}, status=status.HTTP_400_BAD_REQUEST
            )

        if rating < 0 or rating > 5:
            return Response(
                {"detail": "rating must be in range 0..5"}, status=status.HTTP_400_BAD_REQUEST
            )

        instance.rating = rating
        instance.save(update_fields=["rating"])
        instance = self.get_queryset().filter(id=instance.id).first() or instance
        return Response(CandidateDetailSerializer(instance).data, status=status.HTTP_200_OK)


class SkillViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Skill.objects.all().order_by("name")
    serializer_class = SkillSerializer
    search_fields = ["name"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanWriteCandidates()]
        return [IsAuthenticated()]
