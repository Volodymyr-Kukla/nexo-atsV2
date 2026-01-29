from django.contrib import admin

from .models import Project, ProjectMember


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "status",
        "department",
        "location",
        "is_remote",
        "deadline",
        "owner",
        "created_at",
    )
    list_filter = ("status", "department", "is_remote")
    search_fields = ("title", "description", "location", "department")
    autocomplete_fields = ("owner",)


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "user", "role", "created_at")
    list_filter = ("role",)
    autocomplete_fields = ("project", "user")


# Register your models here.
