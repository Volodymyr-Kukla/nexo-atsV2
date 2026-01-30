from django.contrib.auth import get_user_model
from django.db import transaction
from pipeline.models import Stage
from rest_framework import serializers

from .models import Project, ProjectMember

User = get_user_model()


class ProjectOwnerSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "role", "position", "avatar_url"]


class ProjectListSerializer(serializers.ModelSerializer):
    owner = ProjectOwnerSerializer(read_only=True)

    candidates_count = serializers.IntegerField(read_only=True)
    new_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "status",
            "location",
            "is_remote",
            "department",
            "deadline",
            "owner",
            "created_at",
            "updated_at",
            "candidates_count",
            "new_count",
        ]


class ProjectDetailSerializer(serializers.ModelSerializer):
    owner = ProjectOwnerSerializer(read_only=True)

    candidates_count = serializers.IntegerField(read_only=True)
    new_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "status",
            "location",
            "is_remote",
            "department",
            "deadline",
            "owner",
            "created_at",
            "updated_at",
            "candidates_count",
            "new_count",
        ]


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    # ADMIN/HR можуть передати owner_id, інші — ігноруємо (owner = request.user)
    owner_id = serializers.IntegerField(required=False)

    # опційно додати учасників одразу при створенні (будуть RECRUITER)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "status",
            "location",
            "is_remote",
            "department",
            "deadline",
            "owner_id",
            "member_ids",
        ]

    def validate_owner_id(self, value: int):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Owner user not found.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        member_ids = validated_data.pop("member_ids", [])
        owner_id = validated_data.pop("owner_id", None)

        # визначаємо owner
        owner = request.user
        if request.user.is_superuser or getattr(request.user, "role", None) in (
            "ADMIN",
            "HR_MANAGER",
        ):
            if owner_id is not None:
                owner = User.objects.get(id=owner_id)

        project = Project.objects.create(owner=owner, **validated_data)

        # signals вже створять owner membership + default stages
        # додаткові учасники:
        for uid in member_ids:
            if uid == owner.id:
                continue
            user = User.objects.filter(id=uid).first()
            if not user:
                continue
            ProjectMember.objects.get_or_create(
                project=project,
                user=user,
                defaults={"role": ProjectMember.Role.RECRUITER},
            )

        return project

    @transaction.atomic
    def update(self, instance, validated_data):
        # оновлюємо тільки поля проєкту
        validated_data.pop("member_ids", None)
        validated_data.pop("owner_id", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProjectMemberUserSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "role", "position", "avatar_url"]


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = ProjectMemberUserSerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ["id", "user", "role", "created_at", "updated_at"]


class ProjectMemberCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=ProjectMember.Role.choices, required=False)

    def validate_user_id(self, value: int):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found.")
        return value


class StageSummarySerializer(serializers.ModelSerializer):
    candidates_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Stage
        fields = ["id", "name", "system_key", "order", "is_final", "candidates_count"]
