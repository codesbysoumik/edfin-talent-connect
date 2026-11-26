from django.contrib import admin

from .models import JobPost


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "job_type", "location", "is_active", "deadline")
    search_fields = ("title", "description", "location")
    list_filter = ("job_type", "is_active", "location")
