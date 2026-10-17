from typing import Any

from rest_framework import serializers

from apps.insurance import selectors
from apps.insurance.models import Coverage, Payer, Scheme


class PayerSummarySerializer(serializers.ModelSerializer[Payer]):
    class Meta:
        model = Payer
        fields = ["id", "code", "name", "kind", "gateway"]
        read_only_fields = fields


class SchemeSerializer(serializers.ModelSerializer[Scheme]):
    payer = PayerSummarySerializer(read_only=True)

    class Meta:
        model = Scheme
        fields = ["id", "code", "name", "kind", "payer"]
        read_only_fields = fields


class CoverageSerializer(serializers.ModelSerializer[Coverage]):
    """Member numbers are masked; the full number never leaves the server here."""

    scheme = SchemeSerializer(read_only=True)
    member_number = serializers.SerializerMethodField()
    current = serializers.SerializerMethodField()

    class Meta:
        model = Coverage
        fields = [
            "id",
            "patient",
            "scheme",
            "member_number",
            "relationship",
            "valid_from",
            "valid_to",
            "verification",
            "verified_at",
            "active",
            "current",
            "version",
        ]
        read_only_fields = fields

    def get_member_number(self, obj: Coverage) -> str:
        return selectors.masked_member_number(obj)

    def get_current(self, obj: Coverage) -> bool:
        return selectors.is_current(obj)


class CoverageQuerySerializer(serializers.Serializer[Any]):
    patient = serializers.UUIDField()
    purpose = serializers.ChoiceField(
        choices=["registration", "billing", "care"], required=False, default="registration"
    )


class CoverageCreateSerializer(serializers.Serializer[Any]):
    patient = serializers.UUIDField()
    scheme = serializers.UUIDField()
    member_number = serializers.CharField(max_length=40)
    relationship = serializers.ChoiceField(
        choices=Coverage.Relationship.choices, required=False, default="principal"
    )
    valid_from = serializers.DateField(required=False, allow_null=True, default=None)
    valid_to = serializers.DateField(required=False, allow_null=True, default=None)


class EndCoverageSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(max_length=255)
