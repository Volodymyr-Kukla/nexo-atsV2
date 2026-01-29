from core.models import TimeStampedModel
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Project(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", _("В процесі")
        PENDING = "PENDING", _("Очікують")
        CLOSED = "CLOSED", _("Закриті")

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)

    location = models.CharField(max_length=200, blank=True, default="")
    is_remote = models.BooleanField(default=False)

    department = models.CharField(max_length=120, blank=True, default="")
    deadline = models.DateField(null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ProjectMember",
        related_name="projects",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class ProjectMember(TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "OWNER", _("Owner")
        RECRUITER = "RECRUITER", _("Recruiter")
        HIRING_MANAGER = "HIRING_MANAGER", _("Hiring Manager")
        VIEWER = "VIEWER", _("Viewer")

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECRUITER)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="uniq_project_member"),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.user_id}:{self.role}"


# Create your models here.
