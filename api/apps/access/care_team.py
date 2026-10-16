"""Care-team membership (DESIGN §7.7).

Visits, admissions, queues and allocations call ``add_member`` when they assign a user to
a patient and ``close_episode`` when the episode ends. Membership then lasts
``Facility.care_team_expiry_hours`` (default 72 h) so results and follow-up stay visible.
"""

from datetime import datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.access.models import CareTeamMember
from apps.audit.services import record
from apps.facilities.models import Facility


def current_members(patient: Any, *, at: datetime | None = None) -> Any:
    at = at or timezone.now()
    return CareTeamMember.objects.filter(
        patient=patient, removed_at__isnull=True, started_at__lte=at
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=at))


def is_member(user: Any, patient: Any, *, at: datetime | None = None) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return bool(current_members(patient, at=at).filter(user=user).exists())


@transaction.atomic
def add_member(
    *, patient: Any, user: Any, source: str, source_id: str, added_by: Any = None
) -> CareTeamMember:
    """Put ``user`` on ``patient``'s care team for one episode (idempotent; reopens a closed one)."""
    if source not in CareTeamMember.Source.values:
        raise ValidationError({"source": "Unknown care-team source."})
    member, created = CareTeamMember.objects.select_for_update().get_or_create(
        patient=patient,
        user=user,
        source=source,
        source_id=str(source_id),
        defaults={
            "facility_id": patient.facility_id,
            "added_by": added_by,
            "started_at": timezone.now(),
        },
    )
    if not created and (member.episode_closed_at or member.removed_at):
        member.episode_closed_at = member.expires_at = member.removed_at = None
        member.save(update_fields=["episode_closed_at", "expires_at", "removed_at"])
    elif not created:
        return member
    record(
        "access.care_team.added",
        added_by,
        member,
        patient=patient,
        facility=patient.facility_id,
        detail={"member_id": user.pk, "source": source},
    )
    return member


@transaction.atomic
def close_episode(*, source: str, source_id: str, closed_at: datetime | None = None) -> int:
    """Start the expiry clock for every member of one visit, admission, queue or allocation."""
    closed_at = closed_at or timezone.now()
    members = list(
        CareTeamMember.objects.select_for_update().filter(
            source=source,
            source_id=str(source_id),
            episode_closed_at__isnull=True,
            removed_at__isnull=True,
        )
    )
    hours = {
        f.pk: f.care_team_expiry_hours
        for f in Facility.objects.filter(pk__in={m.facility_id for m in members})
    }
    for member in members:
        member.episode_closed_at = closed_at
        member.expires_at = closed_at + timedelta(hours=hours[member.facility_id])
        member.save(update_fields=["episode_closed_at", "expires_at"])
    for patient_id in {m.patient_id for m in members}:
        first = next(m for m in members if m.patient_id == patient_id)
        record(
            "access.care_team.episode_closed",
            None,
            (f"access.caresource.{source}", str(source_id)),
            patient=patient_id,
            facility=first.facility_id,
            detail={"members": sum(1 for m in members if m.patient_id == patient_id)},
        )
    return len(members)


@transaction.atomic
def remove_member(member: CareTeamMember, *, removed_by: Any) -> CareTeamMember:
    """End a membership now (reassignment, wrong patient); history stays."""
    if member.removed_at is None:
        member.removed_at = timezone.now()
        member.save(update_fields=["removed_at"])
        record(
            "access.care_team.removed",
            removed_by,
            member,
            patient=member.patient_id,
            facility=member.facility_id,
            detail={"member_id": member.user_id, "source": member.source},
        )
    return member
