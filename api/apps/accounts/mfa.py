"""Multi-factor authentication with TOTP and recovery codes (DESIGN §7.2, P1-UAC-05).

MFA is required when any of these holds:
- the user holds a role flagged ``mfa_required`` (facility/system admin, medical
  superintendent, finance manager, claims officer, auditor, DPO);
- a facility where the user holds a role requires MFA for all users;
- the request comes from outside FACILITY_NETWORK_ALLOWLIST;
- the user has enrolled a device (enrolled users are always challenged).

A required-but-not-enrolled user may sign in but reaches nothing beyond MFA
enrolment (and their own /me) until a device is confirmed.
"""

import hashlib
import hmac
import ipaddress
import secrets
import time
from typing import Any

import pyotp
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.access import policies
from apps.access.models import RoleAssignment
from apps.accounts.models import MfaDevice, RecoveryCode, User
from apps.audit.context import client_ip
from apps.audit.services import record
from apps.facilities.models import Facility

STEP_SECONDS = 30
RECOVERY_CODES = 10
SESSION_VERIFIED = "mfa_verified"


def network_allowed(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for entry in settings.FACILITY_NETWORK_ALLOWLIST:
        try:
            if address in ipaddress.ip_network(entry.strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


def active_device(user: User) -> MfaDevice | None:
    return (
        MfaDevice.objects.filter(user=user, confirmed_at__isnull=False, removed_at__isnull=True)
        .order_by("-confirmed_at")
        .first()
    )


def role_requires_mfa(user: User) -> bool:
    return (
        policies.active_assignments(user).filter(role__mfa_required=True).exists()
    ) or RoleAssignment.objects.filter(
        user=user, status=RoleAssignment.Status.PENDING_APPROVAL, role__mfa_required=True
    ).exists()


def mfa_required(user: User, ip: str | None) -> bool:
    # IMPLEMENTATION §8: seeded users may sign in without a second factor in development
    # only; anyone who enrols a device is still challenged. Production refuses the switch.
    if settings.MFA_DEV_BYPASS and settings.DJANGO_ENV == "dev" and active_device(user) is None:
        return False
    if role_requires_mfa(user):
        return True
    if Facility.objects.filter(
        pk__in=policies.facilities_for(user), require_mfa_for_all=True
    ).exists():
        return True
    return not network_allowed(ip)


def state(request: Any) -> str:
    """ "ok", "enrol" (required, no device) or "verify" (device present, not verified)."""
    django_request = getattr(request, "_request", request)
    session = getattr(django_request, "session", None)
    if session is not None and session.get(SESSION_VERIFIED):
        return "ok"
    user = request.user
    device = active_device(user)
    if device is None:
        return "enrol" if mfa_required(user, client_ip(django_request)) else "ok"
    return "verify"


def begin_totp_setup(user: User) -> tuple[MfaDevice, str]:
    MfaDevice.objects.filter(user=user, confirmed_at__isnull=True, removed_at__isnull=True).update(
        removed_at=timezone.now()
    )
    device = MfaDevice.objects.create(user=user, secret=pyotp.random_base32())
    uri = pyotp.TOTP(device.secret).provisioning_uri(
        name=user.email, issuer_name=settings.SITE_NAME
    )
    record("auth.mfa.setup_started", user, device)
    return device, uri


def _accept_totp(device: MfaDevice, code: str) -> bool:
    """Accept a code for the current, previous or next step, never twice (replay guard)."""
    if not code.isdigit() or len(code) != 6:
        return False
    totp = pyotp.TOTP(device.secret)
    now_step = int(time.time()) // STEP_SECONDS
    for step in (now_step - 1, now_step, now_step + 1):
        if (
            hmac.compare_digest(totp.at(step * STEP_SECONDS), code)
            and step > device.last_used_counter
        ):
            MfaDevice.objects.filter(pk=device.pk).update(last_used_counter=step)
            device.last_used_counter = step
            return True
    return False


def _code_hash(code: str) -> str:
    normalised = code.replace("-", "").replace(" ", "").lower()
    return hmac.new(settings.SECRET_KEY.encode(), normalised.encode(), hashlib.sha256).hexdigest()


def issue_recovery_codes(user: User) -> list[str]:
    """New single-use codes (shown once); any unused older codes stop working."""
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    codes = [f"{secrets.token_hex(3)}-{secrets.token_hex(3)}" for _ in range(RECOVERY_CODES)]
    RecoveryCode.objects.bulk_create(
        [RecoveryCode(user=user, code_hash=_code_hash(c)) for c in codes]
    )
    record("auth.mfa.recovery_codes_issued", user, user, detail={"count": len(codes)})
    return codes


@transaction.atomic
def confirm_totp_setup(user: User, code: str) -> list[str] | None:
    device = (
        MfaDevice.objects.select_for_update()
        .filter(user=user, confirmed_at__isnull=True, removed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if device is None or not _accept_totp(device, code):
        record("auth.mfa.setup_failed", user, user, outcome="denied")
        return None
    MfaDevice.objects.filter(user=user, confirmed_at__isnull=False, removed_at__isnull=True).update(
        removed_at=timezone.now()
    )
    device.confirmed_at = timezone.now()
    device.save(update_fields=["confirmed_at"])
    record("auth.mfa.enrolled", user, device, severity="notice")
    return issue_recovery_codes(user)


@transaction.atomic
def verify(user: User, *, code: str = "", recovery_code: str = "") -> str | None:
    """Return "totp" or "recovery" when the factor is valid, else None (audited either way)."""
    method = None
    if code:
        device = active_device(user)
        if device is not None:
            device = MfaDevice.objects.select_for_update().get(pk=device.pk)
            method = "totp" if _accept_totp(device, code) else None
    elif recovery_code:
        used = RecoveryCode.objects.filter(
            user=user, code_hash=_code_hash(recovery_code), used_at__isnull=True
        ).update(used_at=timezone.now())
        method = "recovery" if used else None
    if method is None:
        record("auth.mfa.failed", user, user, outcome="denied")
    else:
        record("auth.mfa.verified", user, user, detail={"method": method})
    return method


def remove_devices(user: User) -> int:
    removed = MfaDevice.objects.filter(user=user, removed_at__isnull=True).update(
        removed_at=timezone.now()
    )
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    return removed


def summary(request: Any) -> dict[str, Any]:
    user = request.user
    django_request = getattr(request, "_request", request)
    return {
        "enrolled": active_device(user) is not None,
        "required": mfa_required(user, client_ip(django_request))
        or active_device(user) is not None,
        "verified": bool(django_request.session.get(SESSION_VERIFIED)),
    }
