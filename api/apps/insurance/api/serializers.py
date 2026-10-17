from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.insurance import selectors
from apps.insurance.models import Coverage, EligibilityCheck, Payer, PayerConsent, Scheme


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


# --- Phase 3: eligibility and consent ---------------------------------------------------------


class SchemeAnswerSerializer(serializers.Serializer[Any]):
    name = serializers.CharField()
    status = serializers.CharField()
    active = serializers.BooleanField()
    valid_from = serializers.DateField(allow_null=True)
    valid_to = serializers.DateField(allow_null=True)
    reason = serializers.CharField(allow_blank=True)


class EligibilityCheckSerializer(serializers.ModelSerializer[EligibilityCheck]):
    """An eligibility snapshot. The member reference (CR ID) never leaves the server."""

    checked_at = serializers.DateTimeField(source="created_at", read_only=True)
    schemes = serializers.SerializerMethodField()
    otp_allowed = serializers.SerializerMethodField()
    biometrics_enforced = serializers.SerializerMethodField()
    verification = serializers.CharField(source="coverage.verification", read_only=True)

    class Meta:
        model = EligibilityCheck
        fields = [
            "id",
            "coverage",
            "status",
            "message",
            "checked_on",
            "checked_at",
            "gateway",
            "mode",
            "schemes",
            "otp_allowed",
            "biometrics_enforced",
            "verification",
        ]
        read_only_fields = fields

    def _details(self, obj: EligibilityCheck) -> dict[str, Any]:
        from apps.insurance.eligibility import snapshot_details

        return snapshot_details(obj)

    @extend_schema_field(SchemeAnswerSerializer(many=True))
    def get_schemes(self, obj: EligibilityCheck) -> list[dict[str, Any]]:
        rows = self._details(obj).get("schemes") or []
        return [
            {
                "name": row.get("name", ""),
                "status": row.get("status", ""),
                "active": bool(row.get("active")),
                "valid_from": row.get("from"),
                "valid_to": row.get("to"),
                "reason": row.get("reason", ""),
            }
            for row in rows
        ]

    def get_otp_allowed(self, obj: EligibilityCheck) -> bool:
        return bool(self._details(obj).get("otp_allowed", True))

    def get_biometrics_enforced(self, obj: EligibilityCheck) -> bool:
        return bool(self._details(obj).get("biometrics_enforced", False))


class PayerServiceCodeSerializer(serializers.Serializer[Any]):
    code = serializers.CharField()
    name = serializers.CharField()
    fund = serializers.CharField()
    sub_benefit_code = serializers.CharField()
    access_point = serializers.CharField()
    payment_mechanism = serializers.CharField()
    needs_preauth = serializers.BooleanField()
    needs_manual_preauth_approval = serializers.BooleanField()
    needs_doctor_authorization = serializers.BooleanField()
    # A decimal string, or null when the payer publishes no rate (never 0, KE-SHA-08).
    tariff = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)


class BiometricContextSerializer(serializers.Serializer[Any]):
    agent_id = serializers.CharField(max_length=40)
    device_os = serializers.ChoiceField(choices=["windows", "android"])
    ekyc_provider_id = serializers.CharField(max_length=100)
    work_station_id = serializers.CharField(max_length=120)


class ConsentStartSerializer(serializers.Serializer[Any]):
    coverage = serializers.UUIDField()
    service_type = serializers.ChoiceField(
        choices=["outpatient", "inpatient", "capitation", "emergency"]
    )
    codes = serializers.ListField(
        child=serializers.CharField(max_length=40), min_length=1, max_length=20
    )
    method = serializers.ChoiceField(choices=["otp", "biometric", "card_or_code"])
    contact_id = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    visit = serializers.UUIDField(required=False, allow_null=True, default=None)
    biometric = BiometricContextSerializer(required=False, allow_null=True, default=None)


class MaskedContactSerializer(serializers.Serializer[Any]):
    contact_id = serializers.CharField()
    masked = serializers.CharField()
    confirmed = serializers.BooleanField()


class PayerConsentSerializer(serializers.ModelSerializer[PayerConsent]):
    """Never includes the consent token — only whether one is held."""

    has_token = serializers.BooleanField(read_only=True)
    service_codes = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = PayerConsent
        fields = [
            "id",
            "coverage",
            "visit_id",
            "gateway",
            "method",
            "status",
            "service_type",
            "service_codes",
            "reason",
            "attempts",
            "expires_at",
            "authorized_at",
            "has_token",
            "version",
        ]
        read_only_fields = fields


class ConsentStepSerializer(serializers.Serializer[Any]):
    status = serializers.CharField()
    consent = PayerConsentSerializer(allow_null=True)
    contacts = MaskedContactSerializer(many=True)
    capture_url = serializers.CharField(allow_blank=True)
    reason = serializers.CharField(allow_blank=True)
    otp_fallback = serializers.BooleanField()


class ConsentCompleteSerializer(serializers.Serializer[Any]):
    otp = serializers.CharField(max_length=12, required=False, allow_blank=True, default="")
    member_code = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")


class PendingAuthorisationsSerializer(serializers.Serializer[Any]):
    pending = serializers.IntegerField()
