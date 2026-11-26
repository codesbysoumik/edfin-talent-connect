import django_filters

from .models import JobPost


class JobPostFilter(django_filters.FilterSet):
    location = django_filters.CharFilter(lookup_expr="icontains")
    skill = django_filters.CharFilter(
        field_name="required_skills__name", lookup_expr="iexact"
    )

    class Meta:
        model = JobPost
        fields = ("job_type", "location", "skill")
