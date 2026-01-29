from django.contrib import admin

from .models import Application, Stage, StageChangeEvent


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "order", "name", "system_key", "is_final")
    list_filter = ("is_final", "system_key")
    search_fields = ("name", "system_key")
    autocomplete_fields = ("project",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "candidate",
        "current_stage",
        "position_in_stage",
        "created_at",
        "is_archived",
    )
    list_filter = ("is_archived",)
    search_fields = ("project__name", "candidate__full_name", "current_stage__name")
    autocomplete_fields = ("project", "candidate", "current_stage")


@admin.register(StageChangeEvent)
class StageChangeEventAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "from_stage", "to_stage", "changed_by", "changed_at")
    autocomplete_fields = ("application", "from_stage", "to_stage", "changed_by")


# Register your models here.
