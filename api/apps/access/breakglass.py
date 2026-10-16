"""Break-glass: immediate, time-limited full chart access with mandatory review (DESIGN §7.8).

A clinician without full access gives a reason and a justification and gets full access
for ``Facility.break_glass_minutes`` (default 60). The grant is logged at high severity,
the medical superintendent and the DPO are notified (no patient details in the message),
and it waits in the review queue until a reviewer marks it justified or escalates it.
Break-glass never reveals sensitive categories without ``clinical.record.read_sensitive``.
"""

from datetime import timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.access import chart, policies
from apps.access.models import BreakGlassGrant, RoleAssignment
from apps.access.roles import ChartAccess
from apps.audit.services import record
from apps.facilities.models import Facility

NOTIFY_ROLES = ("medical_superintendent", "dpo")
MIN_JUSTIFICATION = 10


def _recipients(facility_id: int, exclude: Any) -> list[Any]:
    now = timezone.now()
    assignments = (
        RoleAssignment.objects.filter(
            facility_id=facility_id,
            role__code__in=NOTIFY_ROLES,
            status=RoleAssignment.Status.ACTIVE,
            valid_from__lte=now,
            user__is_active=True,
        )
        .exclude(valid_to__lte=now)
        .exclude(user=exclude)
        .select_related("user")
    )
    return list({a.user_id: a.user for a in assignments}.values())


def _notify(grant: BreakGlassGrant) -> None:
    from apps.integrations.notify import notify_user

    facility = Facility.objects.get(pk=grant.facility_id)
    for user in _recipients(grant.facility_id, exclude=grant.user_id):
        notify_user(
            user,
            subject="Break-glass access needs review",
            message=(
                f"Emergency chart access was granted at {facility.name} and is waiting in the "
                f"break-glass review queue (reference {grant.pk})."
            ),
        )


@transaction.atomic
def request_access(*, user: Any, patient: Any, reason: str, justification: str) -> BreakGlassGrant:
    facility_id = patient.facility_id
    if not policies.has_permission(user, chart.BREAK_GLASS, facility=facility_id):
        raise PermissionDenied("You may not use break-glass access here.")
    if reason not in BreakGlassGrant.Reason.values:
        raise ValidationError(
            {"reason": "Choose emergency, continuity of care or clinical review."}
        )
    justification = justification.strip()
    if len(justification) < MIN_JUSTIFICATION:
        raise ValidationError(
            {"justification": "Explain why you need access (at least 10 characters)."}
        )
    existing = chart.active_break_glass(user, patient)
    if existing is not None:
        return existing
    if chart.decide(user, patient).allows(ChartAccess.FULL):
        raise ValidationError({"patient": "You already have full access to this record."})
    minutes = Facility.objects.values_list("break_glass_minutes", flat=True).get(pk=facility_id)
    now = timezone.now()
    grant = BreakGlassGrant.objects.create(
        facility_id=facility_id,
        patient=patient,
        user=user,
        reason=reason,
        justification=justification,
        granted_at=now,
        expires_at=now + timedelta(minutes=minutes),
    )
    record(
        "access.breakglass.granted",
        user,
        grant,
        patient=patient,
        purpose="care",
        severity="high",
        detail={"reason": reason, "minutes": minutes},
    )
    transaction.on_commit(lambda: _notify(grant))
    return grant


@transaction.atomic
def end_access(grant: BreakGlassGrant, *, user: Any) -> BreakGlassGrant:
    """The clinician leaves emergency access before it expires."""
    if grant.user_id != user.pk:
        raise PermissionDenied("Only the clinician who used break-glass can end it.")
    if grant.ended_at is None and grant.expires_at > timezone.now():
        grant.ended_at = timezone.now()
        grant.save(update_fields=["ended_at"])
        record("access.breakglass.ended", user, grant, patient=grant.patient_id)
    return grant


@transaction.atomic
def review(
    grant: BreakGlassGrant, *, reviewer: Any, outcome: str, note: str = ""
) -> BreakGlassGrant:
    grant = BreakGlassGrant.objects.select_for_update().get(pk=grant.pk)
    if not policies.has_permission(
        reviewer, "access.breakglass.review", facility=grant.facility_id
    ):
        raise PermissionDenied("You may not review break-glass access here.")
    if grant.user_id == reviewer.pk:
        raise PermissionDenied("You cannot review your own break-glass access.")
    if outcome not in (BreakGlassGrant.Review.JUSTIFIED, BreakGlassGrant.Review.ESCALATED):
        raise ValidationError({"outcome": "Mark it justified or escalate it."})
    if outcome == BreakGlassGrant.Review.ESCALATED and not note.strip():
        raise ValidationError({"note": "Say why it is escalated."})
    if grant.review_status != BreakGlassGrant.Review.PENDING:
        raise ValidationError({"review_status": "This grant has already been reviewed."})
    grant.review_status = outcome
    grant.reviewed_by = reviewer
    grant.reviewed_at = timezone.now()
    grant.review_note = note.strip()
    grant.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "review_note"])
    record(
        f"access.breakglass.{outcome}",
        reviewer,
        grant,
        patient=grant.patient_id,
        purpose="audit",
        severity="high" if outcome == BreakGlassGrant.Review.ESCALATED else "notice",
    )
    return grant
