"""Login, lockout and credential changes (DESIGN §7.2, P1-UAC-04). Everything is audited.

- Progressive delay: from the 5th consecutive failure the next attempt must wait
  1, 2, 4, 8, 16 seconds (refused with 429 meanwhile, never slept on the server).
- Lock: the 10th consecutive failure locks the account until an administrator unlocks it.
- Unknown e-mail and wrong password get the same answer; a locked account is only
  revealed when the correct password is given.
"""

import secrets
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.access import policies
from apps.accounts.models import User, UserSession
from apps.accounts.sessions import end_sessions
from apps.audit.services import record

DELAY_AFTER = 5
LOCK_AFTER = 10
MAX_DELAY_SECONDS = 60
_DUMMY_HASH = make_password("timing-equaliser-not-a-real-password")


@dataclass(frozen=True)
class LoginResult:
    outcome: str  # "ok" | "invalid" | "throttled" | "locked"
    user: User | None = None
    retry_after: int = 0


def delay_seconds(failures: int) -> int:
    if failures < DELAY_AFTER:
        return 0
    return int(min(2 ** (failures - DELAY_AFTER), MAX_DELAY_SECONDS))


def _wait_remaining(user: User) -> int:
    wait = delay_seconds(user.failed_login_attempts)
    if not wait or user.last_failed_login_at is None:
        return 0
    elapsed = (timezone.now() - user.last_failed_login_at).total_seconds()
    return max(0, int(wait - elapsed + 0.999))


@transaction.atomic
def _record_failure(user: User) -> User:
    user = User.objects.select_for_update().get(pk=user.pk)
    user.failed_login_attempts += 1
    user.last_failed_login_at = timezone.now()
    fields = ["failed_login_attempts", "last_failed_login_at"]
    if user.failed_login_attempts >= LOCK_AFTER and not user.account_locked:
        user.account_locked = True
        user.locked_at = timezone.now()
        fields += ["account_locked", "locked_at"]
        record(
            "auth.account.locked",
            None,
            user,
            outcome="denied",
            severity="high",
            detail={"failures": user.failed_login_attempts},
        )
    user.save(update_fields=fields)
    return user


def attempt_login(request: HttpRequest, email: str, password: str) -> LoginResult:
    user = User.objects.filter(email__iexact=email.strip()).first()
    if user is None or not user.is_active:
        check_password(password, _DUMMY_HASH)  # same work as a real check
        record(
            "auth.login.failed", None, outcome="denied", detail={"reason": "invalid_credentials"}
        )
        return LoginResult("invalid")

    if user.account_locked:
        correct = user.check_password(password)
        record("auth.login.failed", user, user, outcome="denied", detail={"reason": "locked"})
        return LoginResult("locked" if correct else "invalid")

    wait = _wait_remaining(user)
    if wait:
        record("auth.login.throttled", user, user, outcome="denied", detail={"retry_after": wait})
        return LoginResult("throttled", retry_after=wait)

    authenticated = authenticate(request, email=user.email, password=password)
    if authenticated is None:
        user = _record_failure(user)
        record(
            "auth.login.failed",
            user,
            user,
            outcome="denied",
            detail={"reason": "invalid_credentials", "failures": user.failed_login_attempts},
        )
        if user.account_locked:
            return LoginResult("invalid")
        return LoginResult("invalid", retry_after=delay_seconds(user.failed_login_attempts))

    if authenticated.failed_login_attempts or authenticated.last_failed_login_at:
        User.objects.filter(pk=authenticated.pk).update(
            failed_login_attempts=0, last_failed_login_at=None
        )
    login(request, authenticated)
    request.session["auth_at"] = timezone.now().timestamp()
    request.session["last_activity"] = request.session["auth_at"]
    record("auth.login.succeeded", authenticated, authenticated)
    return LoginResult("ok", user=authenticated)


@transaction.atomic
def unlock_account(user: User, *, by: Any, facility: Any) -> User:
    if not policies.has_permission(by, "admin.user.unlock", facility=facility):
        raise PermissionDenied("You do not have permission to unlock accounts here.")
    user = User.objects.select_for_update().get(pk=user.pk)
    user.account_locked = False
    user.locked_at = None
    user.failed_login_attempts = 0
    user.last_failed_login_at = None
    user.save(
        update_fields=[
            "account_locked",
            "locked_at",
            "failed_login_attempts",
            "last_failed_login_at",
        ]
    )
    record("auth.account.unlocked", by, user, facility=facility, severity="notice")
    return user


def change_password(user: User, *, current: str, new: str) -> None:
    if not user.check_password(current):
        record("auth.password.change_failed", user, user, outcome="denied")
        raise ValidationError({"current_password": "The current password is not correct."})
    if current == new:
        raise ValidationError({"new_password": "Choose a password you have not just used."})
    validate_password(new, user)
    with transaction.atomic():
        user.set_password(new)
        user.must_change_password = False
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password", "must_change_password", "password_changed_at"])
        record("auth.password.changed", user, user)


@transaction.atomic
def reset_credentials(user: User, *, by: Any, facility: Any) -> str:
    """Set a one-time temporary password (shown once to the administrator, never sent).

    The user must change it at the next sign-in; all their sessions end now.
    """
    if not policies.has_permission(by, "admin.user.reset_credentials", facility=facility):
        raise PermissionDenied("You do not have permission to reset credentials here.")
    if by.pk == user.pk:
        raise ValidationError({"user": "Use change password for your own account."})
    temporary = "-".join(secrets.token_urlsafe(4) for _ in range(4))
    user = User.objects.select_for_update().get(pk=user.pk)
    user.set_password(temporary)
    user.must_change_password = True
    user.account_locked = False
    user.failed_login_attempts = 0
    user.save()
    ended = end_sessions(user, reason=UserSession.EndReason.REVOKED)
    record(
        "admin.user.credentials_reset",
        by,
        user,
        facility=facility,
        severity="notice",
        detail={"sessions_ended": ended},
    )
    return temporary


def session_limits(facility: Any) -> dict[str, int]:
    """Idle/absolute/lock limits for a facility (defaults from DESIGN §7.2)."""
    return {
        "idle_minutes": int(getattr(facility, "session_idle_minutes", 30)),
        "absolute_hours": int(getattr(facility, "session_absolute_hours", 12)),
        "lock_minutes": int(getattr(facility, "workstation_lock_minutes", 5)),
    }
