import django_filters as filters

from .models import Application


class ApplicationFilter(filters.FilterSet):
    project_id = filters.NumberFilter(field_name="project_id")
    candidate_id = filters.NumberFilter(field_name="candidate_id")
    stage_id = filters.NumberFilter(field_name="current_stage_id")
    is_archived = filters.BooleanFilter(field_name="is_archived")

    class Meta:
        model = Application
        fields = ["project_id", "candidate_id", "stage_id", "is_archived"]
