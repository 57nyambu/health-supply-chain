"""Compatibility values for the legacy dashboards (frontend/), removed with them in P1-WEB-06.

``tier`` only steers which legacy dashboard the browser opens; it grants nothing.
Access is decided by role assignments and policies (apps.access).
"""

from typing import Any

TIER_BY_ROLE = {
    "ADMIN": 1,
    "BRANCH_MANAGER": 2,
    "WAREHOUSE": 2,
    "PROCUREMENT": 2,
    "CASHIER": 2,
    "REPORTER": 3,
}


def legacy_tier(user: Any) -> int | None:
    return TIER_BY_ROLE.get(getattr(user, "role", ""))


def legacy_warehouse_id(user: Any) -> int | None:
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    if profile.warehouse_id:
        return int(profile.warehouse_id)
    first = profile.branch.warehouse_set.order_by("pk").values_list("pk", flat=True).first()
    return int(first) if first is not None else None
