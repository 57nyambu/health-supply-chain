from typing import Any

from rest_framework import serializers

from apps.patients.api.serializers import age_text
from apps.visits.models import (
    GateContext,
    GateOverride,
    GatePolicy,
    GateType,
    PayerType,
    QueueBoard,
    QueueTicket,
    Visit,
    VisitStatus,
    VisitTransition,
    VisitType,
)


class PatientBriefSerializer(serializers.Serializer[Any]):
    """Demographics level only: what any worklist role may see."""

    id = serializers.UUIDField()
    mrn = serializers.CharField()
    display_name = serializers.CharField()
    sex = serializers.CharField()
    age = serializers.SerializerMethodField()
    is_unidentified = serializers.BooleanField()

    def get_age(self, obj: Any) -> str | None:
        return age_text(obj.date_of_birth)


class TransitionSerializer(serializers.ModelSerializer[VisitTransition]):
    class Meta:
        model = VisitTransition
        fields = ["from_status", "to_status", "actor", "reason", "at"]
        read_only_fields = fields


class VisitSerializer(serializers.ModelSerializer[Visit]):
    patient = PatientBriefSerializer(read_only=True)
    scheme_name = serializers.CharField(source="coverage.scheme.name", read_only=True, default=None)

    class Meta:
        model = Visit
        fields = [
            "id",
            "number",
            "patient",
            "visit_type",
            "status",
            "coverage",
            "scheme_name",
            "payer_type",
            "arrival_mode",
            "brought_by",
            "triage_category",
            "disposition",
            "episode_of",
            "opened_at",
            "status_changed_at",
            "clinically_completed_at",
            "closed_at",
            "version",
        ]
        read_only_fields = fields


class TicketBriefSerializer(serializers.ModelSerializer[QueueTicket]):
    service_point_name = serializers.CharField(source="service_point.name", read_only=True)
    service_point_kind = serializers.CharField(source="service_point.kind", read_only=True)

    class Meta:
        model = QueueTicket
        fields = [
            "id",
            "number",
            "service_point",
            "service_point_name",
            "service_point_kind",
            "status",
            "arrived_at",
            "call_count",
            "room",
            "priority_reason",
            "note",
            "lwbs_flagged_at",
        ]
        read_only_fields = fields


class GateOverrideSerializer(serializers.ModelSerializer[GateOverride]):
    class Meta:
        model = GateOverride
        fields = ["id", "context", "gate", "reason_code", "reason", "created_by", "created_at"]
        read_only_fields = fields


class VisitDetailSerializer(VisitSerializer):
    transitions = TransitionSerializer(many=True, read_only=True)
    tickets = TicketBriefSerializer(many=True, read_only=True)
    gate_overrides = GateOverrideSerializer(many=True, read_only=True)

    class Meta(VisitSerializer.Meta):
        fields = [*VisitSerializer.Meta.fields, "transitions", "tickets", "gate_overrides"]
        read_only_fields = fields


class VisitOpenSerializer(serializers.Serializer[Any]):
    patient = serializers.UUIDField()
    visit_type = serializers.ChoiceField(choices=VisitType.choices)
    coverage = serializers.UUIDField(required=False, allow_null=True, default=None)
    waiver = serializers.BooleanField(required=False, default=False)
    service_point = serializers.IntegerField(required=False, allow_null=True, default=None)
    arrival_mode = serializers.ChoiceField(
        choices=Visit.ArrivalMode.choices, required=False, default=Visit.ArrivalMode.WALK_IN
    )
    brought_by = serializers.ChoiceField(
        choices=Visit.BroughtBy.choices, required=False, allow_blank=True, default=""
    )


class VisitQuerySerializer(serializers.Serializer[Any]):
    status = serializers.MultipleChoiceField(choices=VisitStatus.choices, required=False)
    visit_type = serializers.ChoiceField(choices=VisitType.choices, required=False)
    patient = serializers.UUIDField(required=False)
    open = serializers.BooleanField(required=False, allow_null=True, default=None)
    date = serializers.DateField(required=False)


class VisitTransitionSerializer(serializers.Serializer[Any]):
    to = serializers.ChoiceField(choices=VisitStatus.choices)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    version = serializers.IntegerField(required=False, allow_null=True, default=None)


class DispositionSerializer(serializers.Serializer[Any]):
    disposition = serializers.ChoiceField(choices=Visit.Disposition.choices)


class GateQuerySerializer(serializers.Serializer[Any]):
    context = serializers.ChoiceField(choices=GateContext.choices)  # type: ignore[assignment]


class GateDecisionSerializer(serializers.Serializer[Any]):
    cleared = serializers.BooleanField()
    gate = serializers.CharField()
    reason = serializers.CharField()
    context = serializers.CharField()  # type: ignore[assignment]
    override_id = serializers.UUIDField(allow_null=True)
    details = serializers.DictField()


class GateOverrideRequestSerializer(serializers.Serializer[Any]):
    context = serializers.ChoiceField(choices=GateContext.choices)  # type: ignore[assignment]
    reason_code = serializers.ChoiceField(choices=GateOverride.ReasonCode.choices)
    reason = serializers.CharField(max_length=255)


class TicketSerializer(TicketBriefSerializer):
    visit = VisitSerializer(read_only=True)

    class Meta(TicketBriefSerializer.Meta):
        fields = [*TicketBriefSerializer.Meta.fields, "visit", "called_at", "served_at"]
        read_only_fields = fields


class ServicePointQueueSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    kind = serializers.CharField()
    waiting = serializers.IntegerField()
    called = serializers.IntegerField()
    serving = serializers.IntegerField()


class CallSerializer(serializers.Serializer[Any]):
    room = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")


class TransferSerializer(serializers.Serializer[Any]):
    service_point = serializers.IntegerField()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class PrioritiseSerializer(serializers.Serializer[Any]):
    reason_code = serializers.ChoiceField(choices=QueueTicket.PriorityReason.choices)


class GatePolicySerializer(serializers.ModelSerializer[GatePolicy]):
    class Meta:
        model = GatePolicy
        fields = ["id", "context", "payer_type", "gate", "condition", "updated_at", "approval"]
        read_only_fields = fields


class GatePolicyChangeSerializer(serializers.Serializer[Any]):
    context = serializers.ChoiceField(choices=GateContext.choices)  # type: ignore[assignment]
    payer_type = serializers.ChoiceField(choices=PayerType.choices)
    gate = serializers.ChoiceField(choices=GateType.choices)
    condition = serializers.ChoiceField(choices=GatePolicy.Condition.choices, default="always")
    reason = serializers.CharField(max_length=255)


class ApprovalRefSerializer(serializers.Serializer[Any]):
    approval_id = serializers.UUIDField()
    status = serializers.CharField()


class BoardSerializer(serializers.ModelSerializer[QueueBoard]):
    class Meta:
        model = QueueBoard
        fields = ["id", "name", "service_points", "active", "created_at", "last_seen_at"]
        read_only_fields = fields


class BoardCreateSerializer(serializers.Serializer[Any]):
    name = serializers.CharField(max_length=80)
    service_points = serializers.ListField(child=serializers.IntegerField(), min_length=1)


class BoardCreatedSerializer(BoardSerializer):
    token = serializers.CharField(read_only=True)

    class Meta(BoardSerializer.Meta):
        fields = [*BoardSerializer.Meta.fields, "token"]
        read_only_fields = fields


class BoardTicketSerializer(serializers.Serializer[Any]):
    """What a TV may show: ticket number, where to go, status. Never a name (KE-DPA-01)."""

    number = serializers.CharField()
    room = serializers.CharField()
    service_point = serializers.CharField()
    status = serializers.CharField()
    called_at = serializers.DateTimeField(allow_null=True)


class BoardDisplaySerializer(serializers.Serializer[Any]):
    name = serializers.CharField()
    now_calling = BoardTicketSerializer(many=True)
    waiting = BoardTicketSerializer(many=True)
