from rest_framework import serializers

from apps.facilities.models import Bed, Department, Facility, ServicePoint, Ward


class FacilitySerializer(serializers.ModelSerializer[Facility]):
    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "mfl_code",
            "fid",
            "keph_level",
            "sha_contract_number",
            "kra_pin",
            "odpc_controller_registration",
            "odpc_processor_registration",
            "slade_provider_code",
            "mrn_format",
            "require_mfa_for_all",
            "workstation_lock_minutes",
            "session_idle_minutes",
            "session_absolute_hours",
            "care_team_expiry_hours",
            "break_glass_minutes",
            "active",
        ]
        read_only_fields = ["id", "active"]


class DepartmentSerializer(serializers.ModelSerializer[Department]):
    class Meta:
        model = Department
        fields = ["id", "code", "name", "active"]
        read_only_fields = ["id"]


class ServicePointSerializer(serializers.ModelSerializer[ServicePoint]):
    class Meta:
        model = ServicePoint
        fields = ["id", "code", "name", "kind", "department", "active"]
        read_only_fields = ["id"]


class WardSerializer(serializers.ModelSerializer[Ward]):
    beds_total = serializers.IntegerField(read_only=True)
    beds_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ward
        fields = [
            "id",
            "code",
            "name",
            "kind",
            "sex",
            "department",
            "active",
            "beds_total",
            "beds_available",
        ]
        read_only_fields = ["id"]


class BedSerializer(serializers.ModelSerializer[Bed]):
    class Meta:
        model = Bed
        fields = ["id", "ward", "code", "status", "active", "status_changed_at"]
        read_only_fields = ["id", "status", "status_changed_at"]


class BedStatusSerializer(serializers.Serializer[None]):
    status = serializers.ChoiceField(choices=Bed.Status.choices)
