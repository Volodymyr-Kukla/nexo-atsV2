from candidates.models import Candidate
from projects.models import Project
from rest_framework import serializers

from .models import Application, Stage


class CandidateCardSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    skills = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "city",
            "experience_years",
            "rating",
            "skills",
        ]

    def get_skills(self, obj):
        return [s.name for s in obj.skills.all()]


class ApplicationCardSerializer(serializers.ModelSerializer):
    candidate = CandidateCardSerializer(read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "project_id",
            "candidate",
            "current_stage_id",
            "position_in_stage",
            "created_at",
            "updated_at",
            "is_archived",
        ]


class ApplicationCreateSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    candidate_id = serializers.IntegerField()
    stage_id = serializers.IntegerField(required=False)
    stage_system_key = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        project_id = attrs.get("project_id")
        candidate_id = attrs.get("candidate_id")
        stage_id = attrs.get("stage_id")
        stage_system_key = (attrs.get("stage_system_key") or "").strip()

        project = Project.objects.filter(id=project_id).first()
        if not project:
            raise serializers.ValidationError({"project_id": "Project not found"})

        candidate = Candidate.objects.filter(id=candidate_id).first()
        if not candidate:
            raise serializers.ValidationError({"candidate_id": "Candidate not found"})

        stage = None
        if stage_id:
            stage = Stage.objects.filter(id=stage_id, project=project).first()
            if not stage:
                raise serializers.ValidationError({"stage_id": "Stage not found in this project"})
        elif stage_system_key:
            stage = Stage.objects.filter(project=project, system_key=stage_system_key).first()
            if not stage:
                raise serializers.ValidationError(
                    {"stage_system_key": "Stage not found in this project"}
                )
        else:
            # default: "new" або перша за order
            stage = (
                Stage.objects.filter(project=project, system_key="new").first()
                or Stage.objects.filter(project=project).order_by("order", "id").first()
            )

        if not stage:
            raise serializers.ValidationError({"stage": "Project has no stages configured"})

        attrs["project"] = project
        attrs["candidate"] = candidate
        attrs["stage"] = stage
        return attrs


class ApplicationMoveSerializer(serializers.Serializer):
    to_stage_id = serializers.IntegerField()


class KanbanReorderSerializer(serializers.Serializer):
    stage_id = serializers.IntegerField()
    ordered_application_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
    )
