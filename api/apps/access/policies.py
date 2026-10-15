"""The authorization decision (DESIGN §7.3): RBAC within scope, licence, relationship, SoD.

``has_permission`` answers "may this user use this permission here, now?":

- the user is active and holds an *active* assignment valid at ``at`` whose role grants
  the permission, in the facility of the resource;
- an assignment narrowed to a department or ward does not cover resources that belong
  to a different department or ward (resources without one are covered);
- permissions marked ``requires_licence`` also need a valid professional licence;
- there is no superuser bypass: Django's ``is_superuser`` grants nothing here.

Relationship (care team, break-glass) and sensitivity checks live in ``chart_access``
(P1-UAC-08/09); separation of duties for approvals lives in ``approvals``.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.access.catalogue import all_permissions
from apps.access.models import RoleAssignment

# Set by P1-UAC-07 (professional licences). Until then licensed permissions are denied.
licence_checker: Callable[[Any, str, datetime], bool] = lambda user, code, at: False  # noqa: E731


def _active(user: Any) -> bool:
    return bool(user is not None and getattr(user, "is_authenticated", False) and user.is_active)


def active_assignments(
    user: Any, *, at: datetime | None = None, facility: Any = None
) -> QuerySet[RoleAssignment]:
    if not _active(user):
        return RoleAssignment.objects.none()
    at = at or timezone.now()
    queryset = RoleAssignment.objects.filter(
        user=user,
        status=RoleAssignment.Status.ACTIVE,
        role__active=True,
        valid_from__lte=at,
    ).filter(Q(valid_to__isnull=True) | Q(valid_to__gt=at))
    if facility is not None:
        queryset = queryset.filter(facility_id=getattr(facility, "pk", facility))
    return queryset


def _scope_covers(assignment: RoleAssignment, department: Any, ward: Any) -> bool:
    ward_id = getattr(ward, "pk", ward)
    ward_department_id = getattr(ward, "department_id", None)
    department_id = getattr(department, "pk", department) or ward_department_id
    if assignment.ward_id is not None and ward_id is not None and assignment.ward_id != ward_id:
        return False
    if assignment.department_id is not None:
        if department_id is not None and assignment.department_id != department_id:
            return False
    return True


def has_permission(
    user: Any,
    code: str,
    *,
    facility: Any = None,
    department: Any = None,
    ward: Any = None,
    at: datetime | None = None,
) -> bool:
    definition = all_permissions().get(code)
    if definition is None:
        return False
    at = at or timezone.now()
    assignments = active_assignments(user, at=at, facility=facility).filter(
        role__permissions__code=code, role__permissions__active=True
    )
    if not any(_scope_covers(a, department, ward) for a in assignments):
        return False
    if definition.requires_licence and not licence_checker(user, code, at):
        return False
    return True


def effective_permissions(user: Any, *, facility: Any, at: datetime | None = None) -> set[str]:
    """Permission codes usable in ``facility`` (for /api/v1/me; the API still checks each one)."""
    at = at or timezone.now()
    codes = set(
        active_assignments(user, at=at, facility=facility)
        .filter(role__permissions__active=True)
        .values_list("role__permissions__code", flat=True)
    )
    catalogue = all_permissions()
    return {
        code
        for code in codes
        if code in catalogue
        and (not catalogue[code].requires_licence or licence_checker(user, code, at))
    }


def role_codes(user: Any, *, facility: Any = None, at: datetime | None = None) -> list[str]:
    return sorted(
        set(active_assignments(user, at=at, facility=facility).values_list("role__code", flat=True))
    )


def facilities_for(user: Any, *, at: datetime | None = None) -> list[int]:
    return sorted(set(active_assignments(user, at=at).values_list("facility_id", flat=True)))
