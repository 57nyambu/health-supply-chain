"""Visit and queue state changes (DESIGN §6.2, §6.3). The only way to change ``Visit.status``.

Every transition is checked against ``TRANSITIONS``, written as an append-only
``VisitTransition`` row, audited, and — for opening and ending — emitted as a domain event
for the other lane (SEAMS §2). Other apps add the checks behind "clinically complete" and
"financially cleared" with ``register_requirement`` instead of this module importing them.
"""

import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.access import care_team, policies
from apps.audit.services import record
from apps.core import events, sequences
from apps.core.problems import Conflict
from apps.facilities.models import ServicePoint
from apps.insurance import selectors as insurance
from apps.visits.models import (
    ENDED,
    NOT_OPEN,
    PayerType,
    QueueBoard,
    QueueSettings,
    QueueTicket,
    TriageCategory,
    Visit,
    VisitStatus,
    VisitTransition,
    VisitType,
)

S = VisitStatus

# DESIGN §6.2 state machine. Additions (ADR-040): walk-in pharmacy/lab visits go straight to
# services; emergency visits may skip the consultation queue (the treating team triaged);
# left-before-seen is also possible while waiting for triage; death can be recorded at any
# stage of care.
TRANSITIONS: dict[str, set[str]] = {
    S.REGISTERED: {S.AWAITING_TRIAGE, S.AWAITING_SERVICES, S.CANCELLED, S.LEFT_BEFORE_SEEN},
    S.AWAITING_TRIAGE: {S.IN_TRIAGE, S.LEFT_BEFORE_SEEN, S.CANCELLED},
    S.IN_TRIAGE: {S.AWAITING_CONSULTATION, S.IN_CONSULTATION, S.DECEASED},
    S.AWAITING_CONSULTATION: {S.IN_CONSULTATION, S.LEFT_BEFORE_SEEN},
    S.IN_CONSULTATION: {
        S.AWAITING_SERVICES,
        S.ADMITTED,
        S.CLINICALLY_COMPLETE,
        S.DECEASED,
        S.AWAITING_CONSULTATION,
    },
    S.AWAITING_SERVICES: {S.IN_SERVICE, S.AWAITING_REVIEW, S.CLINICALLY_COMPLETE, S.DECEASED},
    S.IN_SERVICE: {S.AWAITING_SERVICES, S.AWAITING_REVIEW, S.DECEASED},
    S.AWAITING_REVIEW: {S.IN_CONSULTATION, S.DECEASED},
    S.ADMITTED: {S.CLINICALLY_COMPLETE, S.DECEASED},
    S.CLINICALLY_COMPLETE: {S.FINANCIALLY_CLEARED},
    S.FINANCIALLY_CLEARED: {S.CLOSED},
    S.DECEASED: {S.FINANCIALLY_CLEARED},
    S.CLOSED: set(),
    S.CANCELLED: set(),
    S.LEFT_BEFORE_SEEN: set(),
}
# Only walk-in visits go from registered straight to services.
WALK_IN = {VisitType.WALK_IN_PHARMACY, VisitType.WALK_IN_LAB}

# Permission needed to move a visit *into* a status through the generic transition API.
# Domain services (triage, consultation, admission, discharge) call ``transition`` with their
# own checks already made.
TARGET_PERMISSION: dict[str, str] = {
    S.AWAITING_TRIAGE: "visits.queue.manage",
    S.IN_TRIAGE: "clinical.triage.record",
    S.AWAITING_CONSULTATION: "visits.queue.manage",
    S.IN_CONSULTATION: "clinical.note.write",
    S.AWAITING_SERVICES: "visits.queue.manage",
    S.IN_SERVICE: "visits.queue.manage",
    S.AWAITING_REVIEW: "visits.queue.manage",
    S.CLINICALLY_COMPLETE: "clinical.note.write",
    S.FINANCIALLY_CLEARED: "billing.invoice.finalize",
    S.CLOSED: "billing.invoice.finalize",
    S.CANCELLED: "visits.visit.create",
    S.LEFT_BEFORE_SEEN: "visits.queue.manage",
    S.DECEASED: "clinical.note.write",
    S.ADMITTED: "inpatient.admission.create",
}

PREFIX: dict[str, str] = {
    VisitType.OPD: "OP",
    VisitType.WALK_IN_PHARMACY: "OP",
    VisitType.WALK_IN_LAB: "OP",
    VisitType.EMERGENCY: "EM",
    VisitType.INPATIENT: "IP",
}
FIRST_POINT: dict[str, str] = {
    VisitType.OPD: ServicePoint.Kind.TRIAGE,
    VisitType.EMERGENCY: ServicePoint.Kind.EMERGENCY,
    VisitType.WALK_IN_PHARMACY: ServicePoint.Kind.PHARMACY,
    VisitType.WALK_IN_LAB: ServicePoint.Kind.LAB,
}
TRIAGE_RANK = {
    TriageCategory.RED: 0,
    TriageCategory.ORANGE: 1,
    TriageCategory.YELLOW: 2,
    TriageCategory.GREEN: 3,
    TriageCategory.BLUE: 4,
}
UNTRIAGED_RANK = 5

# Hooks other apps register (from ``ready()``) to act in the same transaction as a visit
# change: "opened" (billing captures the consultation charge) and "ended" (billing reverses
# unrendered charges). Synchronous on purpose: the outbox relay is for the other lane.
Hook = Callable[[Visit, Any], None]
_hooks: dict[str, dict[str, Hook]] = {}


def register_hook(event: str, name: str, fn: Hook) -> None:
    if event not in ("opened", "ended"):
        raise ValueError(f"Unknown visit hook {event!r}")
    _hooks.setdefault(event, {})[name] = fn


def _run_hooks(event: str, visit: Visit, actor: Any) -> None:
    for name in sorted(_hooks.get(event, {})):
        _hooks[event][name](visit, actor)


# Requirements other apps register: fn(visit) -> list of PHI-free reasons it is not met.
Requirement = Callable[[Visit], list[str]]
_requirements: dict[str, dict[str, Requirement]] = {}


class TransitionRefused(Conflict):
    default_detail = "The visit cannot move to that status now."
    default_code = "visit_transition_refused"

    def __init__(self, detail: str, unmet: list[str] | None = None) -> None:
        super().__init__(detail)
        self.extra = {"unmet": unmet or []}


class OpenVisitExists(Conflict):
    default_detail = "This patient already has an open visit; continue it instead."
    default_code = "open_visit_exists"

    def __init__(self, visit: Visit) -> None:
        super().__init__()
        self.extra = {"visit_id": str(visit.pk)}


def register_requirement(status: str, name: str, fn: Requirement) -> None:
    """``fn`` must return [] before a visit may enter ``status`` (clinically_complete,
    financially_cleared, closed). Registered from the owning app's ``ready()``."""
    _requirements.setdefault(status, {})[name] = fn


def unmet_requirements(visit: Visit, status: str) -> list[str]:
    reasons: list[str] = []
    for name in sorted(_requirements.get(status, {})):
        reasons.extend(_requirements[status][name](visit))
    return reasons


def _ensure(actor: Any, code: str, facility: Any) -> None:
    if actor is not None and not policies.has_permission(actor, code, facility=facility):
        raise PermissionDenied("You do not have permission to do this here.")


def payer_type_for(coverage: Any, *, waiver: bool = False) -> str:
    if waiver:
        return PayerType.WAIVER
    if coverage is None:
        return PayerType.CASH
    kind = coverage.scheme.payer.kind
    if kind == "sha":
        return PayerType.SHA
    if kind == "employer":
        return PayerType.CORPORATE
    return PayerType.INSURER


# --- Opening ---------------------------------------------------------------------------------------


def _visit_number(facility: Any, visit_type: str, now: datetime) -> str:
    local = timezone.localtime(now)
    day = local.strftime("%y%m%d")
    seq = sequences.next_value(facility_id=facility.pk, name=f"visit-{day}", year=local.year)
    mfl = facility.mfl_code or str(facility.pk)
    return f"{PREFIX[visit_type]}-{mfl}-{day}-{seq:03d}"


def open_visits_of(patient: Any) -> Any:
    return Visit.objects.filter(patient=patient).exclude(status__in=NOT_OPEN)


@transaction.atomic
def open_visit(
    *,
    patient: Any,
    visit_type: str,
    actor: Any,
    coverage: Any = None,
    waiver: bool = False,
    service_point: ServicePoint | None = None,
    arrival_mode: str = Visit.ArrivalMode.WALK_IN,
    brought_by: str = "",
    episode_of: Visit | None = None,
    department: Any = None,
) -> Visit:
    """Open a visit and its first queue ticket. Emergency visits start in triage and are
    never refused for payment or cover (ADR-013)."""
    facility = patient.facility
    _ensure(actor, "visits.visit.create", facility.pk)
    if visit_type not in VisitType.values:
        raise ValidationError({"visit_type": "Choose a visit type."})
    if patient.status != "active":
        raise ValidationError({"patient": "This record was merged; open the surviving record."})
    existing = open_visits_of(patient).exclude(pk=getattr(episode_of, "pk", None)).first()
    if existing is not None and visit_type != VisitType.EMERGENCY:
        raise OpenVisitExists(existing)
    if coverage is not None:
        if coverage.patient_id != patient.pk or not insurance.is_current(coverage):
            if visit_type != VisitType.EMERGENCY:
                raise ValidationError({"coverage": "Choose current cover of this patient."})
            coverage = None  # an emergency never waits on cover questions
    if arrival_mode not in Visit.ArrivalMode.values:
        raise ValidationError({"arrival_mode": "Choose how the patient arrived."})
    if brought_by and brought_by not in Visit.BroughtBy.values:
        raise ValidationError({"brought_by": "Choose who brought the patient."})
    now = timezone.now()
    start = S.REGISTERED
    visit = Visit.objects.create(
        facility=facility,
        number=_visit_number(facility, visit_type, now),
        patient=patient,
        visit_type=visit_type,
        status=start,
        coverage=coverage,
        payer_type=payer_type_for(coverage, waiver=waiver),
        arrival_mode=arrival_mode,
        brought_by=brought_by,
        episode_of=episode_of,
        department=department,
        opened_at=now,
        status_changed_at=now,
        created_by=actor,
        updated_by=actor,
    )
    VisitTransition.objects.create(
        visit=visit, from_status="", to_status=start, actor=actor, at=now
    )
    record(
        "visits.visit.opened",
        actor,
        visit,
        patient=patient,
        detail={"visit_type": visit_type, "payer_type": visit.payer_type, "number": visit.number},
    )
    events.emit(
        "visits.visit.opened",
        aggregate=visit,
        payload={
            "visit_id": str(visit.pk),
            "patient_id": str(patient.pk),
            "visit_type": visit_type,
            "coverage_id": str(coverage.pk) if coverage else None,
        },
    )
    _run_hooks("opened", visit, actor)
    if visit_type != VisitType.INPATIENT:
        point = service_point or _default_point(facility, visit_type)
        if point is not None:
            enqueue(visit, point, actor=actor)
        next_status = S.AWAITING_SERVICES if visit_type in WALK_IN else S.AWAITING_TRIAGE
        visit = transition(visit, next_status, actor=None, reason="opened")
        if visit_type == VisitType.EMERGENCY:
            visit = transition(visit, S.IN_TRIAGE, actor=None, reason="emergency")
    return visit


def _default_point(facility: Any, visit_type: str) -> ServicePoint | None:
    kind = FIRST_POINT.get(visit_type)
    point = (
        ServicePoint.objects.filter(facility=facility, kind=kind, active=True)
        .order_by("code")
        .first()
    )
    if point is None and visit_type == VisitType.EMERGENCY:
        point = (
            ServicePoint.objects.filter(
                facility=facility, kind=ServicePoint.Kind.TRIAGE, active=True
            )
            .order_by("code")
            .first()
        )
    return point


# --- Transitions -----------------------------------------------------------------------------------


def lock(visit: Visit | Any) -> Visit:
    return Visit.objects.select_for_update().get(pk=getattr(visit, "pk", visit))


@transaction.atomic
def transition(
    visit: Visit,
    to: str,
    *,
    actor: Any,
    reason: str = "",
    check_permission: bool = False,
    expected_version: int | None = None,
) -> Visit:
    """Move a visit to ``to`` if the state machine and registered requirements allow it."""
    current = lock(visit)
    if expected_version is not None and current.version != expected_version:
        raise Conflict()
    if to not in VisitStatus.values:
        raise ValidationError({"to": "Unknown visit status."})
    if check_permission:
        _ensure(actor, TARGET_PERMISSION.get(to, "visits.queue.manage"), current.facility_id)
    if current.status == to:
        return current
    if to not in TRANSITIONS[current.status]:
        raise TransitionRefused(
            f"A visit that is {current.get_status_display().lower()} cannot move to that status."
        )
    if (
        current.status == S.REGISTERED
        and to == S.AWAITING_SERVICES
        and current.visit_type not in WALK_IN
    ):
        raise TransitionRefused("Only walk-in visits go straight to services.")
    if to == S.CANCELLED and not reason.strip():
        raise ValidationError({"reason": "Say why the visit is cancelled."})
    unmet = unmet_requirements(current, to)
    if unmet:
        raise TransitionRefused("Some steps are not finished yet.", unmet)
    now = timezone.now()
    previous = current.status
    current.status = to
    current.status_changed_at = now
    current.version += 1
    current.updated_by = actor
    fields = ["status", "status_changed_at", "version", "updated_by", "updated_at"]
    if to == S.CLINICALLY_COMPLETE:
        current.clinically_completed_at = now
        fields.append("clinically_completed_at")
    if to in ENDED:
        current.closed_at = now
        fields.append("closed_at")
    current.save(update_fields=fields)
    VisitTransition.objects.create(
        visit=current, from_status=previous, to_status=to, actor=actor, reason=reason[:255], at=now
    )
    record(
        "visits.visit.transitioned",
        actor,
        current,
        patient=current.patient_id,
        detail={"from": previous, "to": to},
    )
    if to in ENDED:
        _end_episode(current, outcome=to, actor=actor)
    return current


def _end_episode(visit: Visit, *, outcome: str, actor: Any) -> None:
    for ticket in QueueTicket.objects.select_for_update().filter(
        visit=visit,
        status__in=[
            QueueTicket.Status.WAITING,
            QueueTicket.Status.CALLED,
            QueueTicket.Status.SERVING,
        ],
    ):
        ticket.status = (
            QueueTicket.Status.LEFT
            if outcome == S.LEFT_BEFORE_SEEN
            else QueueTicket.Status.CANCELLED
        )
        ticket.finished_at = timezone.now()
        ticket.save(update_fields=["status", "finished_at", "updated_at"])
    care_team.close_episode(source="visit", source_id=str(visit.pk))
    care_team.close_episode(source="queue", source_id=str(visit.pk))
    _run_hooks("ended", visit, actor)
    events.emit(
        "visits.visit.closed",
        aggregate=visit,
        payload={"visit_id": str(visit.pk), "outcome": outcome},
    )


def set_triage_category(visit: Visit, category: str, *, actor: Any) -> Visit:
    """Called by clinical triage: the category orders every queue the visit is in."""
    if category not in TriageCategory.values:
        raise ValidationError({"category": "Choose a triage category."})
    current = lock(visit)
    if current.triage_category != category:
        current.triage_category = category
        current.updated_by = actor
        current.save(update_fields=["triage_category", "updated_by", "updated_at"])
    return current


@transaction.atomic
def record_disposition(visit: Visit, disposition: str, *, actor: Any) -> Visit:
    if disposition not in Visit.Disposition.values:
        raise ValidationError({"disposition": "Choose a disposition."})
    current = lock(visit)
    current.disposition = disposition
    current.updated_by = actor
    current.version += 1
    current.save(update_fields=["disposition", "updated_by", "version", "updated_at"])
    record(
        "visits.visit.disposition_recorded",
        actor,
        current,
        patient=current.patient_id,
        detail={"disposition": disposition},
    )
    return current


def join_care_team(visit: Visit, user: Any) -> None:
    """Assign a clinician to the visit (consultation, order performer…)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return
    care_team.add_member(
        patient=visit.patient, user=user, source="visit", source_id=str(visit.pk), added_by=user
    )


# --- Queues ----------------------------------------------------------------------------------------


def queue_settings(facility: Any) -> QueueSettings:
    found, _ = QueueSettings.objects.get_or_create(facility_id=getattr(facility, "pk", facility))
    return found


@transaction.atomic
def enqueue(
    visit: Visit,
    point: ServicePoint,
    *,
    actor: Any,
    transferred_from: QueueTicket | None = None,
    note: str = "",
) -> QueueTicket:
    if point.facility_id != visit.facility_id or not point.active:
        raise ValidationError({"service_point": "Choose an active service point of this facility."})
    if visit.status in NOT_OPEN and visit.status not in (S.CLINICALLY_COMPLETE, S.DECEASED):
        raise TransitionRefused("This visit has ended.")
    existing = QueueTicket.objects.filter(
        visit=visit,
        service_point=point,
        status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.CALLED],
    ).first()
    if existing is not None:
        return existing
    now = timezone.now()
    local = timezone.localtime(now)
    seq = sequences.next_value(
        facility_id=visit.facility_id, name=f"q-{point.pk}-{local:%y%m%d}", year=local.year
    )
    ticket = QueueTicket.objects.create(
        facility_id=visit.facility_id,
        visit=visit,
        service_point=point,
        number=f"{point.code}-{seq:03d}",
        service_date=local.date(),
        arrived_at=now,
        priority_reason=transferred_from.priority_reason if transferred_from else "",
        transferred_from=transferred_from,
        note=note[:255],
        created_by=actor,
        updated_by=actor,
    )
    record(
        "visits.ticket.created",
        actor,
        ticket,
        patient=visit.patient_id,
        detail={"service_point": point.code, "number": ticket.number},
    )
    return ticket


def ordered(tickets: Any) -> list[QueueTicket]:
    """Triage category (red first), then priority bumps, then arrival (DESIGN §6.3)."""

    def key(t: QueueTicket) -> tuple[int, int, datetime]:
        visit = t.visit
        if visit.triage_category:
            rank = TRIAGE_RANK[TriageCategory(visit.triage_category)]
        else:
            rank = TRIAGE_RANK[TriageCategory.ORANGE] if visit.is_emergency else UNTRIAGED_RANK
        return (rank, 0 if t.priority_reason else 1, t.requeued_at or t.arrived_at)

    return sorted(tickets, key=key)


def waiting(point: ServicePoint) -> list[QueueTicket]:
    rows = QueueTicket.objects.filter(
        service_point=point, status=QueueTicket.Status.WAITING
    ).select_related("visit")
    return ordered(rows)


def _ticket(ticket: QueueTicket | Any) -> QueueTicket:
    return (
        QueueTicket.objects.select_for_update()
        .select_related("visit", "service_point")
        .get(pk=getattr(ticket, "pk", ticket))
    )


def _call(ticket: QueueTicket, actor: Any, room: str) -> QueueTicket:
    now = timezone.now()
    ticket.status = QueueTicket.Status.CALLED
    ticket.call_count += 1
    ticket.called_at = now
    ticket.called_by = actor
    ticket.room = room[:40] or ticket.service_point.name
    ticket.updated_by = actor
    settings_ = queue_settings(ticket.facility_id)
    if ticket.call_count >= settings_.lwbs_max_calls and ticket.lwbs_flagged_at is None:
        ticket.lwbs_flagged_at = now
    ticket.save()
    care_team.add_member(
        patient=ticket.visit.patient,
        user=actor,
        source="queue",
        source_id=str(ticket.visit_id),
        added_by=actor,
    )
    record(
        "visits.ticket.called",
        actor,
        ticket,
        patient=ticket.visit.patient_id,
        detail={"number": ticket.number, "calls": ticket.call_count},
    )
    return ticket


@transaction.atomic
def call_next(point: ServicePoint, *, actor: Any, room: str = "") -> QueueTicket | None:
    _ensure(actor, "visits.queue.manage", point.facility_id)
    # Lock the waiting rows so two desks never call the same patient.
    candidates = list(
        QueueTicket.objects.select_for_update(skip_locked=True, of=("self",))
        .filter(service_point=point, status=QueueTicket.Status.WAITING)
        .select_related("visit", "service_point")
    )
    if not candidates:
        return None
    return _call(ordered(candidates)[0], actor, room)


@transaction.atomic
def call(ticket: QueueTicket, *, actor: Any, room: str = "") -> QueueTicket:
    """Call a specific ticket (or recall a called one)."""
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    if current.status not in (QueueTicket.Status.WAITING, QueueTicket.Status.CALLED):
        raise TransitionRefused("Only waiting or called tickets can be called.")
    return _call(current, actor, room or current.room)


@transaction.atomic
def start_serving(ticket: QueueTicket, *, actor: Any) -> QueueTicket:
    """The patient arrived at the room. Gated contexts are checked by the caller's workflow
    (``apps.visits.gates``) — triage and emergency never are."""
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    if current.status not in (QueueTicket.Status.WAITING, QueueTicket.Status.CALLED):
        raise TransitionRefused("This ticket is not waiting.")
    current.status = QueueTicket.Status.SERVING
    current.served_at = timezone.now()
    current.lwbs_flagged_at = None
    current.updated_by = actor
    current.save()
    care_team.add_member(
        patient=current.visit.patient,
        user=actor,
        source="queue",
        source_id=str(current.visit_id),
        added_by=actor,
    )
    record("visits.ticket.serving", actor, current, patient=current.visit.patient_id)
    return current


@transaction.atomic
def finish(ticket: QueueTicket, *, actor: Any) -> QueueTicket:
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    if not current.active:
        return current
    current.status = QueueTicket.Status.DONE
    current.finished_at = timezone.now()
    current.updated_by = actor
    current.save()
    record("visits.ticket.done", actor, current, patient=current.visit.patient_id)
    return current


@transaction.atomic
def skip(ticket: QueueTicket, *, actor: Any) -> QueueTicket:
    """No-show: back of the queue; flagged for left-before-seen after N calls."""
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    if current.status != QueueTicket.Status.CALLED:
        raise TransitionRefused("Only a called ticket can be skipped.")
    current.status = QueueTicket.Status.WAITING
    current.requeued_at = timezone.now()
    current.updated_by = actor
    current.save()
    record(
        "visits.ticket.skipped",
        actor,
        current,
        patient=current.visit.patient_id,
        detail={"calls": current.call_count},
    )
    return current


@transaction.atomic
def transfer(
    ticket: QueueTicket, to: ServicePoint, *, actor: Any, note: str = "", send_back: bool = False
) -> QueueTicket:
    """Move the patient to another service point's queue (``send_back`` with a note)."""
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    if not current.active:
        raise TransitionRefused("This ticket is no longer in a queue.")
    if send_back and not note.strip():
        raise ValidationError({"note": "Add a note saying why the patient is sent back."})
    current.status = QueueTicket.Status.TRANSFERRED
    current.finished_at = timezone.now()
    current.updated_by = actor
    current.save()
    new = enqueue(current.visit, to, actor=actor, transferred_from=current, note=note)
    record(
        "visits.ticket.sent_back" if send_back else "visits.ticket.transferred",
        actor,
        current,
        patient=current.visit.patient_id,
        detail={"to": to.code, "new_ticket_id": str(new.pk)},
    )
    return new


@transaction.atomic
def prioritise(ticket: QueueTicket, *, actor: Any, reason_code: str) -> QueueTicket:
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    if reason_code not in QueueTicket.PriorityReason.values:
        raise ValidationError({"reason_code": "Choose a priority reason."})
    current.priority_reason = reason_code
    current.updated_by = actor
    current.save()
    record(
        "visits.ticket.prioritised",
        actor,
        current,
        patient=current.visit.patient_id,
        severity="notice",
        detail={"reason_code": reason_code},
    )
    return current


# --- Left before seen ------------------------------------------------------------------------------


def flag_idle_tickets(*, now: datetime | None = None) -> int:
    """Beat job: flag tickets waiting longer than the facility's idle limit (idempotent)."""
    now = now or timezone.now()
    flagged = 0
    for config in QueueSettings.objects.all():
        limit = now - timedelta(minutes=config.lwbs_idle_minutes)
        flagged += (
            QueueTicket.objects.filter(
                facility_id=config.facility_id,
                status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.CALLED],
                lwbs_flagged_at__isnull=True,
            )
            .filter(Q(requeued_at__lt=limit) | Q(requeued_at__isnull=True, arrived_at__lt=limit))
            .update(lwbs_flagged_at=now)
        )
    return flagged


def lwbs_work_queue(facility: Any) -> Any:
    return (
        QueueTicket.objects.filter(
            facility_id=getattr(facility, "pk", facility),
            lwbs_flagged_at__isnull=False,
            status__in=[QueueTicket.Status.WAITING, QueueTicket.Status.CALLED],
        )
        .select_related("visit", "service_point")
        .order_by("lwbs_flagged_at")
    )


@transaction.atomic
def confirm_left_before_seen(ticket: QueueTicket, *, actor: Any) -> Visit:
    """Staff confirm the patient left. Unrendered charges are reversed by billing on the
    ``visits.visit.closed`` event (outcome ``left_before_seen``)."""
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    if current.lwbs_flagged_at is None:
        raise TransitionRefused("This ticket is not in the left-before-seen work queue.")
    return transition(current.visit, S.LEFT_BEFORE_SEEN, actor=actor, reason="left before seen")


@transaction.atomic
def dismiss_left_before_seen(ticket: QueueTicket, *, actor: Any) -> QueueTicket:
    current = _ticket(ticket)
    _ensure(actor, "visits.queue.manage", current.facility_id)
    current.lwbs_flagged_at = None
    current.call_count = 0
    current.requeued_at = timezone.now()
    current.save()
    record("visits.ticket.lwbs_dismissed", actor, current, patient=current.visit.patient_id)
    return current


# --- Queue boards ----------------------------------------------------------------------------------


def hash_board_token(token: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(), f"board:{token}".encode(), hashlib.sha256
    ).hexdigest()


@transaction.atomic
def create_board(
    *, facility: Any, name: str, service_points: list[ServicePoint], actor: Any
) -> tuple[QueueBoard, str]:
    """Create a board and return its device token (shown once, only the HMAC is kept)."""
    facility_id = getattr(facility, "pk", facility)
    _ensure(actor, "visits.board.manage", facility_id)
    if not service_points or any(p.facility_id != facility_id for p in service_points):
        raise ValidationError({"service_points": "Choose service points of this facility."})
    prefix = secrets.token_hex(4)
    token = f"{prefix}.{secrets.token_urlsafe(24)}"
    board = QueueBoard.objects.create(
        facility_id=facility_id,
        name=name.strip(),
        lookup_prefix=prefix,
        token_hash=hash_board_token(token),
    )
    board.service_points.set(service_points)
    record(
        "visits.board.created",
        actor,
        board,
        facility=facility_id,
        detail={"service_points": sorted(p.code for p in service_points)},
    )
    return board, token


@transaction.atomic
def revoke_board(board: QueueBoard, *, actor: Any) -> QueueBoard:
    _ensure(actor, "visits.board.manage", board.facility_id)
    if board.active:
        board.active = False
        board.save(update_fields=["active"])
        record("visits.board.revoked", actor, board, facility=board.facility_id)
    return board


def board_for_token(token: str) -> QueueBoard | None:
    prefix, _, _ = token.partition(".")
    board = QueueBoard.objects.filter(lookup_prefix=prefix, active=True).first()
    if board is None or not hmac.compare_digest(board.token_hash, hash_board_token(token)):
        return None
    return board
