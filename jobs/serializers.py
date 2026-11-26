from django.utils import timezone
from rest_framework import serializers

from profiles.models import Skill

from .models import JobPost


class JobPostSerializer(serializers.ModelSerializer):
    employer = serializers.PrimaryKeyRelatedField(read_only=True)
    required_skills = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Skill.objects.all(), required=False
    )

    class Meta:
        model = JobPost
        fields = (
            "id",
            "employer",
            "title",
            "description",
            "job_type",
            "location",
            "required_skills",
            "min_cgpa",
            "deadline",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "employer", "created_at")

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Deadline must be in the future.")
        return value

    def validate_min_cgpa(self, value):
        if value is not None and not 0 <= value <= 4:
            raise serializers.ValidationError("Minimum CGPA must be between 0 and 4.")
        return value


class RecommendedJobSerializer(serializers.Serializer):
    job_id = serializers.IntegerField()
    title = serializers.CharField()
    job_type = serializers.CharField()
    location = serializers.CharField()
    match_score = serializers.FloatField()
    matched_skills = serializers.ListField(child=serializers.CharField())
    missing_skills = serializers.ListField(child=serializers.CharField())


class JobMatchSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    match_score = serializers.FloatField()
    matched_skills = serializers.ListField(child=serializers.CharField())
    missing_skills = serializers.ListField(child=serializers.CharField())
