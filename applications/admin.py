from django.contrib import admin

from .models import Application, ApplicationStatusHistory


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("student", "job", "status", "applied_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("student__email", "job__title")


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "from_status",
        "to_status",
        "changed_by",
        "changed_at",
    )
    list_filter = ("from_status", "to_status")
