from django.db import transaction
from rest_framework import serializers

from .models import Candidate, CandidateExperience, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


class CandidateExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateExperience
        fields = [
            "id",
            "title",
            "company",
            "start_date",
            "end_date",
            "description",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CandidateListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    # annotated in queryset
    stage_system_key = serializers.CharField(read_only=True)
    stage_name = serializers.CharField(read_only=True)
    status_project_id = serializers.IntegerField(read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)

    status = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "city",
            "experience_years",
            "rating",
            "created_at",
            "stage_system_key",
            "stage_name",
            "status_project_id",
            "submitted_at",
            "status",
            "skills",
        ]

    def get_status(self, obj):
        return obj.stage_system_key or "unassigned"

    def get_skills(self, obj):
        # prefetch in queryset
        return [s.name for s in obj.skills.all()]


class CandidateDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    stage_system_key = serializers.CharField(read_only=True)
    stage_name = serializers.CharField(read_only=True)
    status_project_id = serializers.IntegerField(read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True)

    status = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    experiences = CandidateExperienceSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "city",
            "experience_years",
            "rating",
            "about",
            "is_archived",
            "created_at",
            "updated_at",
            "stage_system_key",
            "stage_name",
            "status_project_id",
            "submitted_at",
            "status",
            "skills",
            "experiences",
        ]

    def get_status(self, obj):
        return obj.stage_system_key or "unassigned"

    def get_skills(self, obj):
        return [s.name for s in obj.skills.all()]


class CandidateExperienceInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150)
    company = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    order = serializers.IntegerField(required=False, default=0)


class CandidateUpsertSerializer(serializers.ModelSerializer):
    """
    Приймає skills як список назв ["React", "TypeScript"] та experiences як список об'єктів.
    """

    skills = serializers.ListField(
        child=serializers.CharField(max_length=60),
        required=False,
        allow_empty=True,
    )
    experiences = CandidateExperienceInputSerializer(many=True, required=False)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "city",
            "experience_years",
            "rating",
            "about",
            "is_archived",
            "skills",
            "experiences",
        ]

    @transaction.atomic
    def create(self, validated_data):
        skills = validated_data.pop("skills", [])
        experiences = validated_data.pop("experiences", [])

        candidate = Candidate.objects.create(**validated_data)
        self._sync_skills(candidate, skills)
        self._sync_experiences(candidate, experiences)

        return candidate

    @transaction.atomic
    def update(self, instance, validated_data):
        skills = validated_data.pop("skills", None)
        experiences = validated_data.pop("experiences", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if skills is not None:
            self._sync_skills(instance, skills)
        if experiences is not None:
            self._sync_experiences(instance, experiences)

        return instance

    def _sync_skills(self, candidate: Candidate, skills: list[str]):
        cleaned = [s.strip() for s in skills if s and s.strip()]
        skill_objs = []
        for name in cleaned:
            obj, _ = Skill.objects.get_or_create(name=name)
            skill_objs.append(obj)
        candidate.skills.set(skill_objs)

    def _sync_experiences(self, candidate: Candidate, experiences: list[dict]):
        candidate.experiences.all().delete()
        for exp in experiences:
            CandidateExperience.objects.create(candidate=candidate, **exp)
