from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer[AuditEvent]):
    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "ts",
            "facility_id",
            "seq",
            "actor_id",
            "actor_role",
            "workstation_id",
            "ip",
            "request_id",
            "action",
            "resource_type",
            "resource_id",
            "patient_id",
            "purpose",
            "outcome",
            "severity",
            "detail",
            "hash",
        ]
        read_only_fields = fields


class AuditFilterSerializer(serializers.Serializer[None]):
    actor = serializers.IntegerField(required=False)
    patient = serializers.UUIDField(required=False)
    action = serializers.CharField(required=False, max_length=100)
    resource_type = serializers.CharField(required=False, max_length=100)
    outcome = serializers.ChoiceField(required=False, choices=AuditEvent.Outcome.choices)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
