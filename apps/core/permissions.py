"""
Smart Health Extension — shared access-control tiers.

Exactly 3 levels, built on the existing accounts.User.Role choices.
No new roles were added — this module only groups the existing 6 roles
into 3 access levels and provides reusable DRF permission classes.

    Tier 1 — Admin            : role == ADMIN
    Tier 2 — Facility Staff   : role in {BRANCH_MANAGER, WAREHOUSE, PROCUREMENT, CASHIER}
                                 scoped to request.user.profile.warehouse
    Tier 3 — Read-Only        : role == REPORTER (internal, JWT)
                                 OR external integrator via X-API-Key (see authentication.py)
"""
from rest_framework.permissions import BasePermission

TIER_1_ROLES = {'ADMIN'}
TIER_2_ROLES = {'BRANCH_MANAGER', 'WAREHOUSE', 'PROCUREMENT', 'CASHIER'}
TIER_3_INTERNAL_ROLES = {'REPORTER'}


def user_tier(user):
    """Returns 1, 2, or 3 for an authenticated internal user, else None."""
    if not getattr(user, 'is_authenticated', False):
        return None
    if user.role in TIER_1_ROLES:
        return 1
    if user.role in TIER_2_ROLES:
        return 2
    if user.role in TIER_3_INTERNAL_ROLES:
        return 3
    return None


def user_warehouse_id(user):
    """Tier-2 users are scoped to the single facility on their WorkerProfile."""
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'warehouse_id', None) if profile else None


class IsTier1(BasePermission):
    """Admin only — full, district-wide access."""
    def has_permission(self, request, view):
        return user_tier(request.user) == 1


class IsTier1OrTier2(BasePermission):
    """Admin (unscoped) or Facility Staff (scoped to their own facility)."""
    def has_permission(self, request, view):
        return user_tier(request.user) in (1, 2)

    def has_object_permission(self, request, view, obj):
        if user_tier(request.user) == 1:
            return True
        return getattr(obj, 'warehouse_id', None) == user_warehouse_id(request.user)


class IsTier3InternalReadOnly(BasePermission):
    """REPORTER role — read-only, district-wide, internal (JWT) users only."""
    def has_permission(self, request, view):
        return (
            user_tier(request.user) == 3
            and request.method in ('GET', 'HEAD', 'OPTIONS')
        )


class IsAnyInternalTier(BasePermission):
    """Any authenticated internal user (Tier 1, 2, or 3) — read access baseline."""
    def has_permission(self, request, view):
        return user_tier(request.user) is not None