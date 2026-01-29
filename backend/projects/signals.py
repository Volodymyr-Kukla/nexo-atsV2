from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver
from pipeline.defaults import DEFAULT_STAGES

from .models import Project, ProjectMember


@receiver(post_save, sender=Project)
def create_default_pipeline_and_owner_membership(
    sender, instance: Project, created: bool, **kwargs
):
    if not created:
        return

    # ensure owner membership
    ProjectMember.objects.get_or_create(
        project=instance,
        user=instance.owner,
        defaults={"role": ProjectMember.Role.OWNER},
    )

    Stage = apps.get_model("pipeline", "Stage")

    # create default stages
    for idx, stage_def in enumerate(DEFAULT_STAGES, start=1):
        Stage.objects.get_or_create(
            project=instance,
            system_key=stage_def["system_key"],
            defaults={
                "name": stage_def["name"],
                "order": idx,
                "is_final": stage_def.get("is_final", False),
            },
        )
