"""The signed-in user's view of themselves: GET /api/v1/me (DESIGN §7.3, §18).

The web app uses ``permissions`` only to hide controls; the API checks every request.
"""

from typing import Any

from django.http import HttpRequest

from apps.access import policies
from apps.access.drf import SESSION_FACILITY_KEY, request_facility
from apps.accounts.legacy import legacy_tier, legacy_warehouse_id
from apps.accounts.login import session_limits
from apps.accounts.session_timeout import SESSION_LIMITS_KEY
from apps.facilities.models import Facility


def choose_facility(request: HttpRequest, facility_id: int | None) -> Facility | None:
    """Make ``facility_id`` the session's active facility (must hold a role there)."""
    allowed = policies.facilities_for(request.user)
    if facility_id is None and len(allowed) == 1:
        facility_id = allowed[0]
    if facility_id not in allowed:
        return None
    facility = Facility.objects.get(pk=facility_id)
    request.session[SESSION_FACILITY_KEY] = facility.pk
    request.session[SESSION_LIMITS_KEY] = session_limits(facility)
    request._access_facility = facility.pk  # type: ignore[attr-defined]
    return facility


def me_payload(request: Any) -> dict[str, Any]:
    user = request.user
    facility_id = request_facility(request)
    facility = Facility.objects.filter(pk=facility_id).first() if facility_id else None
    facilities = Facility.objects.filter(pk__in=policies.facilities_for(user)).order_by("name")
    limits = session_limits(facility) if facility else session_limits(None)
    return {
        "id": user.pk,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "must_change_password": user.must_change_password,
        "facility": (
            {"id": facility.pk, "name": facility.name, "mfl_code": facility.mfl_code}
            if facility
            else None
        ),
        "facilities": [{"id": f.pk, "name": f.name} for f in facilities],
        "roles": policies.role_codes(user, facility=facility_id) if facility_id else [],
        "permissions": sorted(policies.effective_permissions(user, facility=facility_id))
        if facility_id
        else [],
        "session": limits,
        # Legacy dashboards (frontend/) route by these until P1-WEB-06 removes them.
        "legacy": {
            "role": user.role,
            "tier": legacy_tier(user),
            "warehouse_id": legacy_warehouse_id(user),
        },
    }
