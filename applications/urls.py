from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, ApplyView

router = DefaultRouter()
router.register("applications", ApplicationViewSet, basename="application")

urlpatterns = [
    path("jobs/<int:job_id>/apply/", ApplyView.as_view(), name="job-apply"),
    *router.urls,
]
