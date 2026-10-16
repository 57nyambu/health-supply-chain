from datetime import date
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from apps.access.models import BreakGlassGrant
from apps.patients.identifiers import mask
from apps.patients.models import NextOfKin, Patient, PatientContact, PatientIdentifier, PatientMerge


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


class PatientSerializer(serializers.ModelSerializer[Patient]):
    display_name = serializers.CharField(read_only=True)
    age = serializers.SerializerMethodField()
    identifiers = serializers.SerializerMethodField()
    contacts = serializers.SerializerMethodField()
    next_of_kin = serializers.SerializerMethodField()

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
    q = serializers.CharField(max_length=100, allow_blank=False)
    date_of_birth = serializers.DateField(required=False)
    sex = serializers.ChoiceField(choices=Patient.Sex.choices, required=False)


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
