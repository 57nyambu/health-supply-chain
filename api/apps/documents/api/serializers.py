from rest_framework import serializers

from apps.core.sensitivity import SensitiveCategory
from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer[Document]):
    filename = serializers.CharField(source="original_filename", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "patient",
            "category",
            "sensitivity",
            "content_type",
            "size",
            "filename",
            "storage_backend",
            "uploaded_by",
            "created_at",
            "superseded_by",
            "retention_until",
            "legal_hold",
        ]
        read_only_fields = fields


class UploadSerializer(serializers.Serializer[None]):
    file = serializers.FileField(
        error_messages={"required": "Attach a file (at most the configured upload size)."}
    )
    category = serializers.ChoiceField(choices=Document.Category.choices)
    patient = serializers.UUIDField(required=False, allow_null=True, default=None)
    sensitivity = serializers.ChoiceField(
        choices=SensitiveCategory.choices, required=False, default=SensitiveCategory.NORMAL
    )
    supersedes = serializers.UUIDField(required=False, allow_null=True, default=None)


class PatientDocumentsQuerySerializer(serializers.Serializer[None]):
    patient = serializers.UUIDField()
    purpose = serializers.CharField(required=False, default="care")
