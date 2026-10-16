from datetime import date
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from apps.access.models import BreakGlassGrant
from apps.patients import dsar, privacy
from apps.patients.adapters.client_registry import SEARCHABLE_TYPES
from apps.patients.identifiers import mask
from apps.patients.models import (
    Consent,
    DataSubjectRequest,
    NextOfKin,
    Patient,
    PatientContact,
    PatientIdentifier,
    PatientMerge,
)


def age_text(dob: date | None) -> str | None:
    if dob is None:
        return None
    today = timezone.localdate()
    months = (
        (today.year - dob.year) * 12 + today.month - dob.month - (1 if today.day < dob.day else 0)
    )
    return f"{months // 12}y" if months >= 24 else f"{months}m"


class IdentifierSerializer(serializers.ModelSerializer[PatientIdentifier]):
    class Meta:
        model = PatientIdentifier
        fields = ["id", "type", "value", "issuer", "source", "verified_at", "active"]
        read_only_fields = ["id", "source", "verified_at", "active"]


class MaskedIdentifierSerializer(serializers.ModelSerializer[PatientIdentifier]):
    value = serializers.SerializerMethodField(method_name="masked_value")

    class Meta:
        model = PatientIdentifier
        fields = ["type", "value"]

    def masked_value(self, obj: PatientIdentifier) -> str:
        return mask(obj.value)


class ContactSerializer(serializers.ModelSerializer[PatientContact]):
    class Meta:
        model = PatientContact
        fields = ["id", "kind", "value", "is_primary", "active"]
        read_only_fields = ["id", "active"]


class NextOfKinSerializer(serializers.ModelSerializer[NextOfKin]):
    class Meta:
        model = NextOfKin
        fields = ["id", "name", "relationship", "phone", "active"]
        read_only_fields = ["id", "active"]


class ConsentSerializer(serializers.ModelSerializer[Consent]):
    recorded_at = serializers.DateTimeField(source="created_at", read_only=True)
    recorded_by: serializers.PrimaryKeyRelatedField[Any] = serializers.PrimaryKeyRelatedField(
        source="created_by", read_only=True
    )
    version = serializers.CharField(source="notice_version", read_only=True)

    class Meta:
        model = Consent
        fields = [
            "id",
            "kind",
            "decision",
            "version",
            "method",
            "given_by",
            "recorded_at",
            "recorded_by",
        ]
        read_only_fields = fields


class PatientSerializer(serializers.ModelSerializer[Patient]):
    display_name = serializers.CharField(read_only=True)
    age = serializers.SerializerMethodField()
    identifiers = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()
    next_of_kin = serializers.SerializerMethodField()
    consents = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "mrn",
            "given_name",
            "middle_name",
            "family_name",
            "display_name",
            "sex",
            "date_of_birth",
            "dob_estimated",
            "age",
            "is_unidentified",
            "description",
            "status",
            "merged_into",
            "version",
            "identifiers",
            "contacts",
            "next_of_kin",
            "consents",
            "retention_until",
            "legal_hold",
        ]
        read_only_fields = fields

    def get_age(self, obj: Patient) -> str | None:
        return age_text(obj.date_of_birth)

    def get_identifiers(self, obj: Patient) -> Any:
        return IdentifierSerializer(obj.identifiers.filter(active=True), many=True).data

    def get_contacts(self, obj: Patient) -> Any:
        return ContactSerializer(obj.contacts.filter(active=True), many=True).data

    def get_next_of_kin(self, obj: Patient) -> Any:
        return NextOfKinSerializer(obj.next_of_kin.filter(active=True), many=True).data

    def get_consents(self, obj: Patient) -> Any:
        """The current decision per kind (privacy notice, SMS reminders, research)."""
        return ConsentSerializer(list(privacy.current(obj).values()), many=True).data


class SearchResultSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField(source="patient.pk")
    mrn = serializers.CharField(source="patient.mrn")
    display_name = serializers.CharField(source="patient.display_name")
    sex = serializers.CharField(source="patient.sex")
    date_of_birth = serializers.DateField(source="patient.date_of_birth")
    dob_estimated = serializers.BooleanField(source="patient.dob_estimated")
    age = serializers.SerializerMethodField()
    is_unidentified = serializers.BooleanField(source="patient.is_unidentified")
    identifiers = serializers.SerializerMethodField()
    score = serializers.IntegerField()
    reasons = serializers.ListField(child=serializers.CharField())

    def get_age(self, obj: Any) -> str | None:
        return age_text(obj.patient.date_of_birth)

    def get_identifiers(self, obj: Any) -> Any:
        return MaskedIdentifierSerializer(
            obj.patient.identifiers.filter(active=True), many=True
        ).data


class SearchQuerySerializer(serializers.Serializer[None]):
    """Search terms travel in the body, never the URL: names, IDs and phones would
    otherwise land in proxy access logs (ADR-023)."""

    q = serializers.CharField(max_length=100, allow_blank=False)
    date_of_birth = serializers.DateField(required=False)
    sex = serializers.ChoiceField(choices=Patient.Sex.choices, required=False)


class SearchResponseSerializer(serializers.Serializer[Any]):
    results = SearchResultSerializer(many=True)


class BreakGlassAccessSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    reason = serializers.CharField()
    expires_at = serializers.DateTimeField()


class AccessSerializer(serializers.Serializer[Any]):
    """The chart access decision the UI shows (selectors.access_payload)."""

    level = serializers.ChoiceField(
        choices=["none", "demographics", "summary", "full", "sensitive"]
    )
    care_team = serializers.BooleanField()
    break_glass = BreakGlassAccessSerializer(allow_null=True)
    break_glass_available = serializers.BooleanField()


class PatientRecordSerializer(PatientSerializer):
    access = AccessSerializer(read_only=True)

    class Meta(PatientSerializer.Meta):
        fields = [*PatientSerializer.Meta.fields, "access"]
        read_only_fields = fields


class ChartSerializer(serializers.Serializer[Any]):
    """Sections are ``null`` below their level; Phase 2 fills them (selectors.chart_sections)."""

    access = AccessSerializer()
    patient = PatientSerializer()
    summary = serializers.DictField(allow_null=True)
    record = serializers.DictField(allow_null=True)


class IdentifierInputSerializer(serializers.Serializer[None]):
    type = serializers.CharField(max_length=20)
    value = serializers.CharField(max_length=40)
    issuer = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")


class ContactInputSerializer(serializers.Serializer[None]):
    kind = serializers.ChoiceField(choices=PatientContact.Kind.choices)
    value = serializers.CharField(max_length=120)
    is_primary = serializers.BooleanField(required=False, default=False)


class NextOfKinInputSerializer(serializers.Serializer[None]):
    name = serializers.CharField(max_length=120)
    relationship = serializers.CharField(max_length=40)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")


class PrivacyNoticeSerializer(serializers.Serializer[None]):
    version = serializers.CharField(max_length=20)
    method = serializers.ChoiceField(choices=Consent.Method.choices)
    given_by = serializers.ChoiceField(
        choices=Consent.GivenBy.choices, required=False, default=Consent.GivenBy.PATIENT
    )


class ConsentInputSerializer(PrivacyNoticeSerializer):
    kind = serializers.ChoiceField(choices=Consent.Kind.choices)
    decision = serializers.ChoiceField(choices=Consent.Decision.choices)
    version = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")


class PatientCreateSerializer(serializers.Serializer[None]):
    given_name = serializers.CharField(max_length=80)
    middle_name = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    family_name = serializers.CharField(max_length=80)
    sex = serializers.ChoiceField(choices=Patient.Sex.choices)
    date_of_birth = serializers.DateField(required=False, allow_null=True, default=None)
    age_years = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=130, default=None
    )
    age_months = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=11, default=None
    )
    identifiers = IdentifierInputSerializer(many=True, required=False, default=list)
    contacts = ContactInputSerializer(many=True, required=False, default=list)
    next_of_kin = NextOfKinInputSerializer(many=True, required=False, default=list)
    override_reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    privacy_notice = PrivacyNoticeSerializer()


class PatientUpdateSerializer(serializers.Serializer[None]):
    version = serializers.IntegerField(min_value=1)
    given_name = serializers.CharField(max_length=80, required=False)
    middle_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    family_name = serializers.CharField(max_length=80, required=False)
    sex = serializers.ChoiceField(choices=Patient.Sex.choices, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    dob_estimated = serializers.BooleanField(required=False)


class UnidentifiedSerializer(serializers.Serializer[None]):
    sex = serializers.ChoiceField(choices=Patient.Sex.choices)
    approx_age_years = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=130, default=None
    )


class MergeRequestSerializer(serializers.Serializer[None]):
    duplicate = serializers.UUIDField()
    reason = serializers.CharField(max_length=255)


class UnmergeSerializer(serializers.Serializer[None]):
    reason = serializers.CharField(max_length=255)


class MergeSerializer(serializers.ModelSerializer[PatientMerge]):
    class Meta:
        model = PatientMerge
        fields = [
            "id",
            "survivor",
            "duplicate",
            "status",
            "reason",
            "approval",
            "reversal_approval",
            "merged_at",
            "reversed_at",
        ]
        read_only_fields = fields


class BreakGlassRequestSerializer(serializers.Serializer[None]):
    reason = serializers.ChoiceField(choices=BreakGlassGrant.Reason.choices)
    justification = serializers.CharField(max_length=500)


class BreakGlassGrantSerializer(serializers.ModelSerializer[BreakGlassGrant]):
    class Meta:
        model = BreakGlassGrant
        fields = [
            "id",
            "patient",
            "reason",
            "granted_at",
            "expires_at",
            "ended_at",
            "review_status",
        ]
        read_only_fields = fields


class PrivacyNoticeTextSerializer(serializers.Serializer[None]):
    version = serializers.CharField()
    text = serializers.CharField()


class DsarSerializer(serializers.ModelSerializer[DataSubjectRequest]):
    overdue = serializers.SerializerMethodField()

    class Meta:
        model = DataSubjectRequest
        fields = [
            "id",
            "reference",
            "patient",
            "kind",
            "channel",
            "requester",
            "details",
            "received_at",
            "due_at",
            "overdue",
            "status",
            "identity_verified_by",
            "identity_verified_at",
            "identity_evidence",
            "export_json",
            "export_pdf",
            "outcome",
            "closed_at",
            "closed_by",
            "version",
        ]
        read_only_fields = fields

    def get_overdue(self, obj: DataSubjectRequest) -> bool:
        return dsar.is_overdue(obj)


class DsarCreateSerializer(serializers.Serializer[None]):
    patient = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=DataSubjectRequest.Kind.choices)
    channel = serializers.ChoiceField(choices=DataSubjectRequest.Channel.choices)
    requester = serializers.ChoiceField(
        choices=DataSubjectRequest.Requester.choices,
        required=False,
        default=DataSubjectRequest.Requester.PATIENT,
    )
    details = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    received_at = serializers.DateTimeField(required=False, allow_null=True, default=None)


class DsarVerifySerializer(serializers.Serializer[None]):
    evidence = serializers.ChoiceField(choices=sorted(dsar.EVIDENCE))


class DsarExportSerializer(serializers.Serializer[None]):
    include_sensitive = serializers.BooleanField(required=False, default=False)


class DsarCloseSerializer(serializers.Serializer[None]):
    status = serializers.ChoiceField(
        choices=[
            DataSubjectRequest.Status.COMPLETED,
            DataSubjectRequest.Status.REFUSED,
            DataSubjectRequest.Status.WITHDRAWN,
        ]
    )
    outcome = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class RegistryQuerySerializer(serializers.Serializer[None]):
    type = serializers.ChoiceField(choices=list(SEARCHABLE_TYPES))
    number = serializers.CharField(max_length=40)


class RegistryPersonSerializer(serializers.Serializer[Any]):
    """What reception sees to confirm identity: names and DOB, identifiers and phone masked."""

    cr_id = serializers.CharField()
    given_name = serializers.CharField()
    middle_name = serializers.CharField()
    family_name = serializers.CharField()
    sex = serializers.CharField()
    date_of_birth = serializers.DateField(allow_null=True)
    identifiers = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    def get_identifiers(self, obj: Any) -> list[dict[str, str]]:
        return [{"type": t, "value": mask(v)} for t, v in obj.identifiers]

    def get_phone(self, obj: Any) -> str:
        return mask(obj.phone) if obj.phone else ""


class RegistryResultSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=["found", "not_found", "unavailable"])
    person = RegistryPersonSerializer(allow_null=True)
    registered_patient = serializers.UUIDField(allow_null=True)


class RegistrySearchSerializer(serializers.Serializer[Any]):
    local = SearchResultSerializer(many=True)
    registry = RegistryResultSerializer()


class RegistryImportSerializer(RegistryQuerySerializer):
    privacy_notice = PrivacyNoticeSerializer()
    contacts = ContactInputSerializer(many=True, required=False, default=list)
    next_of_kin = NextOfKinInputSerializer(many=True, required=False, default=list)
    override_reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
