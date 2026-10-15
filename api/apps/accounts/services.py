"""State changes for staff accounts."""

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.access import policies
from apps.accounts.models import User, UserSession
from apps.accounts.sessions import end_sessions
from apps.audit.services import record


@transaction.atomic
def deactivate_user(user: User, *, by: Any, reason: str, facility: Any) -> User:
    """Deactivate (never delete) a user and end every session immediately (DESIGN §7.6)."""
    if not policies.has_permission(by, "admin.user.deactivate", facility=facility):
        raise PermissionDenied("You do not have permission to deactivate users here.")
    if by.pk == user.pk:
        raise ValidationError({"user": "You cannot deactivate your own account."})
    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])
    ended = end_sessions(user, reason=UserSession.EndReason.DEACTIVATED)
    _blacklist_legacy_tokens(user)
    record(
        "admin.user.deactivated",
        by,
        user,
        facility=facility,
        detail={"sessions_ended": ended},
        severity="notice",
    )
    return user


def _blacklist_legacy_tokens(user: User) -> None:
    """Legacy SimpleJWT refresh tokens die with the account (JWT is removed in P1-UAC-04)."""
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
