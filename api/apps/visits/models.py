"""Visits, queues, payment gates and queue boards (DESIGN §6.2-6.4, P2-VIS-01..03).

``Visit.status`` changes only through ``apps.visits.services.transition``; every change is
an append-only ``VisitTransition`` row plus an audit event. Queue tickets are per service
point per day. Gates are data (``GatePolicy``) evaluated by ``apps.visits.gates``; emergency
visits and discharge are never gated, whatever the data says (ADR-013).
"""

from django.db import models
from django.db.models import Q

from apps.core.ids import uuid7
from apps.core.models import PhiModel


class VisitType(models.TextChoices):
    OPD = "opd", "Outpatient"
    EMERGENCY = "emergency", "Emergency"
    INPATIENT = "inpatient", "Inpatient (direct admission)"
    WALK_IN_PHARMACY = "walk_in_pharmacy", "Walk-in pharmacy"
    WALK_IN_LAB = "walk_in_lab", "Walk-in laboratory"


class VisitStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    AWAITING_TRIAGE = "awaiting_triage", "Waiting for triage"
    IN_TRIAGE = "in_triage", "In triage"
    AWAITING_CONSULTATION = "awaiting_consultation", "Waiting for consultation"
    IN_CONSULTATION = "in_consultation", "In consultation"
    AWAITING_SERVICES = "awaiting_services", "Waiting for services"
    IN_SERVICE = "in_service", "At a service point"
    AWAITING_REVIEW = "awaiting_review", "Waiting for review"
    ADMITTED = "admitted", "Admitted"
    CLINICALLY_COMPLETE = "clinically_complete", "Clinically complete"
    FINANCIALLY_CLEARED = "financially_cleared", "Financially cleared"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"
    LEFT_BEFORE_SEEN = "left_before_seen", "Left before being seen"
    DECEASED = "deceased", "Deceased"


# Statuses after which the patient is no longer being cared for in this visit.
ENDED = {
    VisitStatus.CLOSED,
    VisitStatus.CANCELLED,
    VisitStatus.LEFT_BEFORE_SEEN,
}
# A patient has at most one visit that is not in one of these.
NOT_OPEN = ENDED | {
    VisitStatus.CLINICALLY_COMPLETE,
    VisitStatus.FINANCIALLY_CLEARED,
    VisitStatus.DECEASED,
}


class PayerType(models.TextChoices):
    """Columns of the gate table (DESIGN §6.4)."""

    CASH = "cash", "Cash / self-pay"
    SHA = "sha", "SHA"
    INSURER = "insurer", "Private insurer"
    CORPORATE = "corporate", "Corporate"
    WAIVER = "waiver", "Waiver"


class TriageCategory(models.TextChoices):
    RED = "red", "Red — emergency"
    ORANGE = "orange", "Orange — very urgent"
    YELLOW = "yellow", "Yellow — urgent"
    GREEN = "green", "Green — routine"
    BLUE = "blue", "Blue — dead on arrival"


class Visit(PhiModel):
    class ArrivalMode(models.TextChoices):
        WALK_IN = "walk_in", "Walk-in"
        AMBULANCE = "ambulance", "Ambulance"
        OTHER = "other", "Other"

    class BroughtBy(models.TextChoices):
        SELF = "self", "Self"
        RELATIVE = "relative", "Relative"
        SAMARITAN = "samaritan", "Good samaritan"
        PARAMEDICS = "paramedics", "Paramedics"
        POLICE = "police", "Police"
        UNKNOWN = "unknown", "Unknown"

    class Disposition(models.TextChoices):
        HOME = "home", "Home"
        ADMIT = "admit", "Admit"
        REFER = "refer", "Refer"
        DECEASED = "deceased", "Deceased"

    number = models.CharField(max_length=40)
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="visits")
    visit_type = models.CharField(max_length=20, choices=VisitType.choices)
    status = models.CharField(
        max_length=25, choices=VisitStatus.choices, default=VisitStatus.REGISTERED
    )
    coverage = models.ForeignKey(
        "insurance.Coverage", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    payer_type = models.CharField(max_length=10, choices=PayerType.choices, default=PayerType.CASH)
    arrival_mode = models.CharField(
        max_length=10, choices=ArrivalMode.choices, default=ArrivalMode.WALK_IN
    )
    brought_by = models.CharField(max_length=12, choices=BroughtBy.choices, blank=True)
    triage_category = models.CharField(max_length=10, choices=TriageCategory.choices, blank=True)
    disposition = models.CharField(max_length=10, choices=Disposition.choices, blank=True)
    department = models.ForeignKey(
        "facilities.Department", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # An inpatient visit created from an outpatient/emergency visit points back to it.
    episode_of = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="episodes"
    )
    opened_at = models.DateTimeField()
    status_changed_at = models.DateTimeField()
    clinically_completed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["facility", "status"]),
            models.Index(fields=["facility", "opened_at"]),
            models.Index(fields=["patient", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["facility", "number"], name="visits_visit_number"),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def is_emergency(self) -> bool:
        return self.visit_type == VisitType.EMERGENCY

    @property
    def is_open(self) -> bool:
        return self.status not in NOT_OPEN


class VisitTransition(models.Model):
    """Append-only history of ``Visit.status`` (never updated or deleted)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="transitions")
    from_status = models.CharField(max_length=25, choices=VisitStatus.choices, blank=True)
    to_status = models.CharField(max_length=25, choices=VisitStatus.choices)
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    reason = models.CharField(max_length=255, blank=True)
    at = models.DateTimeField()

    class Meta:
        ordering = ["at"]

    def __str__(self) -> str:
        return f"{self.visit_id}: {self.from_status} → {self.to_status}"


class QueueSettings(models.Model):
    """Per-facility queue behaviour (DESIGN §6.2 left-before-seen)."""

    facility = models.OneToOneField(
        "facilities.Facility", on_delete=models.PROTECT, related_name="queue_settings"
    )
    lwbs_max_calls = models.PositiveSmallIntegerField(default=3)
    lwbs_idle_minutes = models.PositiveIntegerField(default=240)

    def __str__(self) -> str:
        return f"Queue settings of facility {self.facility_id}"


class QueueTicket(PhiModel):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        CALLED = "called", "Called"
        SERVING = "serving", "Being served"
        DONE = "done", "Done"
        TRANSFERRED = "transferred", "Transferred"
        CANCELLED = "cancelled", "Cancelled"
        LEFT = "left", "Left before being seen"

    class PriorityReason(models.TextChoices):
        ELDERLY = "elderly", "Elderly"
        DISABLED = "disabled", "Disability"
        PREGNANT = "pregnant", "Pregnant"
        CHILD = "child", "Young child"
        CLINICAL = "clinical", "Clinical concern"
        VIP = "vip", "VIP"

    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="tickets")
    service_point = models.ForeignKey(
        "facilities.ServicePoint", on_delete=models.PROTECT, related_name="tickets"
    )
    number = models.CharField(max_length=30)
    service_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.WAITING)
    arrived_at = models.DateTimeField()
    requeued_at = models.DateTimeField(null=True, blank=True)
    priority_reason = models.CharField(max_length=10, choices=PriorityReason.choices, blank=True)
    call_count = models.PositiveSmallIntegerField(default=0)
    called_at = models.DateTimeField(null=True, blank=True)
    called_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    room = models.CharField(max_length=40, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    transferred_from = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    note = models.CharField(max_length=255, blank=True)
    lwbs_flagged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["arrived_at"]
        indexes = [models.Index(fields=["service_point", "status", "service_date"])]
        constraints = [
            models.UniqueConstraint(
                fields=["service_point", "service_date", "number"], name="visits_ticket_number"
            ),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def active(self) -> bool:
        return self.status in (self.Status.WAITING, self.Status.CALLED, self.Status.SERVING)


class GateContext(models.TextChoices):
    """Where a gate is evaluated (DESIGN §6.4 rows). Discharge is deliberately absent."""

    CONSULTATION = "consultation", "OPD consultation"
    LAB = "lab", "Laboratory"
    IMAGING = "imaging", "Imaging"
    PROCEDURE = "procedure", "Procedure / treatment room"
    PHARMACY = "pharmacy", "Pharmacy"
    ELECTIVE_ADMISSION = "elective_admission", "Elective admission"


class GateType(models.TextChoices):
    NONE = "none", "No gate"
    PAY_BEFORE_SERVICE = "pay_before_service", "Pay before service"
    ELIGIBILITY_VERIFIED = "eligibility_verified", "Eligibility verified"
    MEMBER_VERIFIED = "member_verified", "Member verified"
    PREAUTH_APPROVED = "preauth_approved", "Pre-authorisation approved"
    DEPOSIT = "deposit", "Deposit paid"
    CREDIT_LIMIT = "credit_limit", "Within credit limit"


class GatePolicy(models.Model):
    class Condition(models.TextChoices):
        ALWAYS = "always", "Always"
        IF_FLAGGED = "if_flagged", "Only if the intervention or scheme flags it"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.PROTECT, related_name="gate_policies"
    )
    context = models.CharField(max_length=20, choices=GateContext.choices)
    payer_type = models.CharField(max_length=10, choices=PayerType.choices)
    gate = models.CharField(max_length=25, choices=GateType.choices)
    condition = models.CharField(max_length=12, choices=Condition.choices, default=Condition.ALWAYS)
    updated_at = models.DateTimeField(auto_now=True)
    approval = models.ForeignKey(
        "access.ApprovalRequest", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["facility", "context", "payer_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "context", "payer_type"], name="visits_one_gate_per_cell"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.context}/{self.payer_type}: {self.gate}"


class GateOverride(PhiModel):
    """A permitted user let a visit past a gate, with a reason; shown on the bill and audited."""

    class ReasonCode(models.TextChoices):
        CLINICAL_URGENCY = "clinical_urgency", "Clinical urgency"
        PAYMENT_PROMISED = "payment_promised", "Payment promised"
        WAIVER_PENDING = "waiver_pending", "Waiver being processed"
        PAYER_SYSTEM_DOWN = "payer_system_down", "Payer system unavailable"
        OTHER = "other", "Other"

    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="gate_overrides")
    context = models.CharField(max_length=20, choices=GateContext.choices)
    gate = models.CharField(max_length=25, choices=GateType.choices)
    reason_code = models.CharField(max_length=20, choices=ReasonCode.choices)
    reason = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Override {self.context} for {self.visit_id}"


class QueueBoard(models.Model):
    """A TV board for a group of service points: ticket numbers and rooms only, no names.
    It authenticates with a device token scoped to this board (only the HMAC is stored)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.PROTECT, related_name="queue_boards"
    )
    name = models.CharField(max_length=80)
    service_points = models.ManyToManyField("facilities.ServicePoint", related_name="boards")
    lookup_prefix = models.CharField(max_length=8, unique=True)
    token_hash = models.CharField(max_length=64)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["facility", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "name"],
                condition=Q(active=True),
                name="visits_board_name",
            )
        ]

    def __str__(self) -> str:
        return self.name
