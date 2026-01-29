from django.contrib import admin

from .models import Candidate, CandidateExperience, Skill


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "city",
        "experience_years",
        "rating",
        "created_at",
    )
    list_filter = ("city", "rating", "is_archived")
    search_fields = ("first_name", "last_name", "email", "phone")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(CandidateExperience)
class CandidateExperienceAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "title", "company", "start_date", "end_date", "order")
    autocomplete_fields = ("candidate",)


# Register your models here.
