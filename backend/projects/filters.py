import django_filters as filters

from .models import Project


class ProjectFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    department = filters.CharFilter(field_name="department", lookup_expr="icontains")
    location = filters.CharFilter(field_name="location", lookup_expr="icontains")
    is_remote = filters.BooleanFilter(field_name="is_remote")
    owner_id = filters.NumberFilter(field_name="owner_id")

    mine = filters.BooleanFilter(method="filter_mine")

    def filter_mine(self, queryset, name, value):
        if not value:
            return queryset
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return queryset.none()
        return queryset.filter(memberships__user=user).distinct()

    class Meta:
        model = Project
        fields = ["status", "department", "location", "is_remote", "owner_id", "mine"]
