import django_filters as filters

from .models import Candidate


class CandidateFilter(filters.FilterSet):
    city = filters.CharFilter(field_name="city", lookup_expr="icontains")

    rating = filters.NumberFilter(field_name="rating")
    rating_min = filters.NumberFilter(field_name="rating", lookup_expr="gte")
    rating_max = filters.NumberFilter(field_name="rating", lookup_expr="lte")

    experience_min = filters.NumberFilter(field_name="experience_years", lookup_expr="gte")
    experience_max = filters.NumberFilter(field_name="experience_years", lookup_expr="lte")

    is_archived = filters.BooleanFilter(field_name="is_archived")

    # Похідний статус (анотація stage_system_key в queryset)
    status = filters.CharFilter(method="filter_status")

    # Показати кандидатів, які є у конкретному проєкті
    project_id = filters.NumberFilter(method="filter_project_id")

    # Навички: "React,TypeScript" (match ANY)
    skills = filters.CharFilter(method="filter_skills")

    def filter_status(self, queryset, name, value):
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(stage_system_key=value)

    def filter_project_id(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            applications__project_id=value, applications__is_archived=False
        ).distinct()

    def filter_skills(self, queryset, name, value):
        value = (value or "").strip()
        if not value:
            return queryset
        skills = [s.strip() for s in value.split(",") if s.strip()]
        if not skills:
            return queryset
        return queryset.filter(skills__name__in=skills).distinct()

    class Meta:
        model = Candidate
        fields = [
            "city",
            "rating",
            "rating_min",
            "rating_max",
            "experience_min",
            "experience_max",
            "is_archived",
            "status",
            "project_id",
            "skills",
        ]
