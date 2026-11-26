from rest_framework import serializers

from .models import Application, ApplicationStatusHistory


class ApplySerializer(serializers.Serializer):
    cover_letter = serializers.CharField(required=False, allow_blank=True)


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = (
            "id",
            "student",
            "job",
            "cover_letter",
            "status",
            "applied_at",
            "updated_at",
        )
        read_only_fields = fields


class ApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Application.Status.choices)


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(
        source="changed_by.email", read_only=True
    )

    class Meta:
        model = ApplicationStatusHistory
        fields = (
            "id",
            "application",
            "from_status",
            "to_status",
            "changed_by",
            "changed_by_email",
            "changed_at",
        )
