from django.contrib import admin

from .models import EmployerProfile, Skill, StudentProfile


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "university", "department", "cgpa")
    search_fields = ("full_name", "university", "department", "user__email")
    list_filter = ("university", "department")


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "location", "is_verified")
    search_fields = ("company_name", "location", "user__email")
    list_filter = ("is_verified",)
