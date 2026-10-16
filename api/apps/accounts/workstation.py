"""Shared workstations: lock, PIN unlock and quick user switch (DESIGN §7.2, P1-UAC-06).

- A signed, httpOnly cookie identifies the device (``workstation_id``).
- The session locks after the facility's ``workstation_lock_minutes`` idle (default 5)
  or on request; while locked only unlock, switch, /me and logout answer.
- Unlock: the signed-in user's PIN. Switch: another user's PIN, allowed only if that
  user did a full sign-in on this workstation within the last 12 hours. The device
  keeps working, but the session now belongs to the new user, so every later action
  is attributed to them.
- PINs are 6 digits, hashed (argon2id), throttled; 5 consecutive failures end the
  user's PIN eligibility everywhere (and the locked session) — a full sign-in is needed.
"""

import secrets
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from apps.accounts.models import User, UserSession, WorkstationSession
from apps.accounts.sessions import end_sessions
from apps.audit import context as audit_context
from apps.audit.services import record

COOKIE = "workstation_id"
COOKIE_SALT = "afyasync.workstation"
COOKIE_MAX_AGE = 365 * 24 * 3600
SESSION_LOCKED = "workstation_locked"
PIN_WINDOW = timedelta(hours=12)
MAX_PIN_FAILURES = 5
PIN_LENGTH = 6
_DUMMY_PIN_HASH = make_password("000000-not-a-pin")


def workstation_id(request: HttpRequest) -> str:
    return str(getattr(request, "workstation_id", "") or "")


class WorkstationMiddleware:
    """Read (or issue) the device cookie and put it into the audit context."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            value = str(request.get_signed_cookie(COOKIE, salt=COOKIE_SALT))
            issued = False
        except (KeyError, signing.BadSignature):
            value = secrets.token_hex(16)
            issued = True
        request.workstation_id = value  # type: ignore[attr-defined]
        audit_context.update(workstation_id=value)
        response = self.get_response(request)
        if issued and request.path.startswith("/api/"):
            response.set_signed_cookie(
                COOKIE,
                value,
                salt=COOKIE_SALT,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
                secure=settings.SESSION_COOKIE_SECURE,
            )
        return response


def is_locked(request: HttpRequest) -> bool:
    return bool(request.session.get(SESSION_LOCKED))


def record_full_signin(request: HttpRequest, user: User, *, mfa_verified: bool) -> None:
    ws = workstation_id(request)
    if ws:
        WorkstationSession.objects.create(
            workstation_id=ws, user=user, signed_in_at=timezone.now(), mfa_verified=mfa_verified
        )


def lock(request: HttpRequest, *, reason: str) -> None:
    if not is_locked(request):
        request.session[SESSION_LOCKED] = True
        record("auth.workstation.locked", request.user, request.user, detail={"reason": reason})


def validate_pin(pin: str) -> None:
    if len(pin) != PIN_LENGTH or not pin.isdigit():
        raise ValidationError({"pin": "The PIN must be exactly 6 digits."})
    if len(set(pin)) == 1 or pin in "0123456789" or pin in "9876543210":
        raise ValidationError(
            {"pin": "Choose a PIN that is not a repeated or consecutive sequence."}
        )


@transaction.atomic
def set_pin(user: User, *, pin: str, password: str) -> None:
    if not user.check_password(password):
        record("auth.pin.change_failed", user, user, outcome="denied")
        raise ValidationError({"password": "The password is not correct."})
    validate_pin(pin)
    user.pin_hash = make_password(pin)
    user.pin_set_at = timezone.now()
    user.pin_failures = 0
    user.save(update_fields=["pin_hash", "pin_set_at", "pin_failures"])
    record("auth.pin.set", user, user)


def _eligible(user: User, ws: str) -> WorkstationSession | None:
    return (
        WorkstationSession.objects.filter(
            workstation_id=ws,
            user=user,
            ended_at__isnull=True,
            signed_in_at__gte=timezone.now() - PIN_WINDOW,
        )
        .order_by("-signed_in_at")
        .first()
    )


@transaction.atomic
def _check_pin(user: User, pin: str) -> bool:
    """Verify a PIN with lockout; 5 consecutive failures revoke PIN eligibility."""
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.pin_hash and check_password(pin, user.pin_hash):
        if user.pin_failures:
            User.objects.filter(pk=user.pk).update(pin_failures=0)
        return True
    if not user.pin_hash:
        check_password(pin, _DUMMY_PIN_HASH)
    user.pin_failures += 1
    User.objects.filter(pk=user.pk).update(pin_failures=user.pin_failures)
    record("auth.pin.failed", user, user, outcome="denied", detail={"failures": user.pin_failures})
    if user.pin_failures >= MAX_PIN_FAILURES:
        WorkstationSession.objects.filter(user=user, ended_at__isnull=True).update(
            ended_at=timezone.now()
        )
        User.objects.filter(pk=user.pk).update(pin_failures=0)
        record("auth.pin.locked_out", user, user, outcome="denied", severity="high")
    return False


def _end_for_full_login(request: HttpRequest, user: User) -> str:
    end_sessions(
        user, reason=UserSession.EndReason.REVOKED, session_key=request.session.session_key
    )
    logout(request)
    return "full_login"


def unlock(request: HttpRequest, user: User, *, pin: str) -> str:
    """ "ok", "invalid" or "full_login" (no recent sign-in here, no PIN, or 5 failures)."""
    ws = workstation_id(request)
    if not user.pin_hash or _eligible(user, ws) is None:
        return _end_for_full_login(request, user)
    if _check_pin(user, pin):
        request.session[SESSION_LOCKED] = False
        request.session["last_activity"] = timezone.now().timestamp()
        record("auth.workstation.unlocked", user, user)
        return "ok"
    if _eligible(user, ws) is None:  # the failure that revoked PIN eligibility
        return _end_for_full_login(request, user)
    return "invalid"


def switch_user(request: HttpRequest, *, email: str, pin: str) -> tuple[str, User | None]:
    """Hand the locked workstation to another user by PIN. Returns (outcome, user)."""
    ws = workstation_id(request)
    target = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
    if target is None or target.account_locked:
        check_password(pin, _DUMMY_PIN_HASH)
        record(
            "auth.workstation.switch_failed", None, outcome="denied", detail={"reason": "unknown"}
        )
        return "invalid", None
    eligibility = _eligible(target, ws)
    if eligibility is None:
        record(
            "auth.workstation.switch_failed",
            target,
            target,
            outcome="denied",
            detail={"reason": "no_recent_signin"},
        )
        return "full_login", None
    if not _check_pin(target, pin):
        return "invalid", None
    previous = request.user if request.user.is_authenticated else None
    if previous is not None and previous.pk != target.pk:
        end_sessions(
            previous, reason=UserSession.EndReason.SWITCHED, session_key=request.session.session_key
        )
        record(
            "auth.workstation.switched_out", previous, previous, detail={"to_user_id": target.pk}
        )
    login(request, target, backend="django.contrib.auth.backends.ModelBackend")
    now = timezone.now().timestamp()
    request.session["auth_at"] = eligibility.signed_in_at.timestamp()
    request.session["last_activity"] = now
    request.session["mfa_verified"] = eligibility.mfa_verified
    request.session[SESSION_LOCKED] = False
    record(
        "auth.workstation.switched_in",
        target,
        target,
        detail={"from_user_id": previous.pk if previous is not None else None},
    )
    return "ok", target


def summary(request: Any) -> dict[str, Any]:
    django_request = getattr(request, "_request", request)
    return {"locked": is_locked(django_request), "pin_set": bool(request.user.pin_hash)}
