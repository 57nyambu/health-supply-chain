"""Chart access levels (DESIGN §7.3, §7.7, §7.8).

``check_chart_access(user, patient, purpose)`` is the one place that decides how much of a
patient's record a user may see::

    level = highest role level for the relationship (baseline, or care team / break-glass)
          capped by permissions:  sensitive needs clinical.record.read_sensitive,
                                  full needs clinical.record.read_full (licensed) unless break-glass,
                                  summary needs clinical.record.read_summary or read_full
          capped by purpose:      registration and billing see demographics only

Selectors that return PHI call it and shape their output to the level.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.access import care_team, policies
from apps.access.models import BreakGlassGrant
from apps.access.roles import ChartAccess

ORDER = {level: index for index, level in enumerate(ChartAccess)}
PURPOSES = ("care", "registration", "billing", "records", "audit")
PURPOSE_CAPS = {"registration": ChartAccess.DEMOGRAPHICS, "billing": ChartAccess.DEMOGRAPHICS}
READ_SUMMARY = "clinical.record.read_summary"
READ_FULL = "clinical.record.read_full"
READ_SENSITIVE = "clinical.record.read_sensitive"
BREAK_GLASS = "access.breakglass.request"


def at_least(level: ChartAccess | str, needed: ChartAccess | str) -> bool:
    return ORDER[ChartAccess(level)] >= ORDER[ChartAccess(needed)]


def _lower(a: ChartAccess, b: ChartAccess) -> ChartAccess:
    return a if ORDER[a] <= ORDER[b] else b


def _higher(a: ChartAccess, b: ChartAccess) -> ChartAccess:
    return a if ORDER[a] >= ORDER[b] else b


@dataclass(frozen=True)
class ChartAccessDecision:
    level: ChartAccess
    care_team: bool = False
    break_glass: BreakGlassGrant | None = None
    may_break_glass: bool = False

    def allows(self, needed: ChartAccess | str) -> bool:
        return at_least(self.level, needed)

    @property
    def sensitive(self) -> bool:
        return self.level == ChartAccess.SENSITIVE


NO_ACCESS = ChartAccessDecision(ChartAccess.NONE)


def active_break_glass(
    user: Any, patient: Any, *, at: datetime | None = None
) -> BreakGlassGrant | None:
    at = at or timezone.now()
    return (
        BreakGlassGrant.objects.filter(
            user=user, patient=patient, granted_at__lte=at, expires_at__gt=at, ended_at__isnull=True
        )
        .order_by("-expires_at")
        .first()
    )


def baseline_level(user: Any, facility: Any, *, at: datetime | None = None) -> ChartAccess:
    """The level a user has for any patient of ``facility`` without a care relationship."""
    roles = [
        a.role
        for a in policies.active_assignments(user, at=at, facility=facility).select_related("role")
    ]
    level = ChartAccess.NONE
    for role in roles:
        level = _higher(level, ChartAccess(role.chart_baseline))
    return _cap_by_permissions(user, level, facility, at=at, break_glass=False)


def _cap_by_permissions(
    user: Any, level: ChartAccess, facility: Any, *, at: datetime | None, break_glass: bool
) -> ChartAccess:
    def may(code: str) -> bool:
        return policies.has_permission(user, code, facility=facility, at=at)

    if level == ChartAccess.SENSITIVE and not may(READ_SENSITIVE):
        level = ChartAccess.FULL
    if level == ChartAccess.FULL and not break_glass and not may(READ_FULL):
        level = ChartAccess.SUMMARY
    if level == ChartAccess.SUMMARY and not (may(READ_SUMMARY) or may(READ_FULL)):
        level = ChartAccess.DEMOGRAPHICS
    return level


def decide(
    user: Any, patient: Any, *, purpose: str = "care", at: datetime | None = None
) -> ChartAccessDecision:
    """Full decision: level plus why (care team, break-glass) for banners and audit."""
    if user is None or not getattr(user, "is_authenticated", False):
        return NO_ACCESS
    at = at or timezone.now()
    facility = patient.facility_id
    roles = [
        a.role
        for a in policies.active_assignments(user, at=at, facility=facility).select_related("role")
    ]
    if not roles:
        return NO_ACCESS
    on_team = care_team.is_member(user, patient, at=at)
    may_break_glass = policies.has_permission(user, BREAK_GLASS, facility=facility, at=at)
    grant = active_break_glass(user, patient, at=at) if may_break_glass else None

    level = ChartAccess.NONE
    for role in roles:
        related = on_team or grant is not None
        level = _higher(
            level, ChartAccess(role.chart_care_team if related else role.chart_baseline)
        )
    if grant is not None:
        level = _higher(level, ChartAccess.FULL)
    level = _cap_by_permissions(user, level, facility, at=at, break_glass=grant is not None)
    offer = (
        may_break_glass and purpose not in PURPOSE_CAPS and not at_least(level, ChartAccess.FULL)
    )
    cap = PURPOSE_CAPS.get(purpose)
    if cap is not None:
        level = _lower(level, cap)
    return ChartAccessDecision(
        level=level, care_team=on_team, break_glass=grant, may_break_glass=offer
    )


def check_chart_access(user: Any, patient: Any, purpose: str = "care") -> ChartAccess:
    """none / demographics / summary / full / sensitive for this user, patient and purpose."""
    return decide(user, patient, purpose=purpose).level
