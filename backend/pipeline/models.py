from core.models import TimeStampedModel
from django.conf import settings
from django.db import models


class Stage(TimeStampedModel):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="stages")

    name = models.CharField(max_length=100)
    system_key = models.CharField(max_length=50)
    order = models.PositiveSmallIntegerField(default=0)

    is_final = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "system_key"], name="uniq_stage_system_key_per_project"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.order}:{self.name}"


class Application(TimeStampedModel):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="applications"
    )
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="applications"
    )

    current_stage = models.ForeignKey(
        "pipeline.Stage", on_delete=models.PROTECT, related_name="applications"
    )

    # для сортування карток усередині колонки
    position_in_stage = models.PositiveIntegerField(default=0)

    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "candidate"], name="uniq_candidate_per_project"
            ),
        ]

    def __str__(self) -> str:
        return f"Application(project={self.project_id}, candidate={self.candidate_id})"


class StageChangeEvent(models.Model):
    application = models.ForeignKey(
        "pipeline.Application", on_delete=models.CASCADE, related_name="stage_changes"
    )

    from_stage = models.ForeignKey(
        "pipeline.Stage", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    to_stage = models.ForeignKey("pipeline.Stage", on_delete=models.PROTECT, related_name="+")

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"{self.application_id}:{self.from_stage_id}->{self.to_stage_id}"


# Create your models here.
