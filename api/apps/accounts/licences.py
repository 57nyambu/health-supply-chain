"""Professional licences: recording, registry verification, expiry warnings (DESIGN §7.10)."""

from datetime import date, datetime, timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.access import policies
from apps.access.models import RoleAssignment
from apps.accounts.adapters.hwr import get_registry
from apps.accounts.models import ProfessionalLicence, User
from apps.audit.services import record
from apps.integrations.notify import notify_user

WARN_DAYS = 30
LICENCE_FIELDS = {
    "regulator",
    "registration_number",
    "licence_number",
    "valid_from",
    "valid_to",
    "slade_code",
    "active",
}


def licence_ok(user: Any, regulators: set[str], at: datetime) -> bool:
    """policies.licence_checker: a licence valid on ``at`` from an accepted regulator."""
    day = timezone.localdate(at)
    queryset = ProfessionalLicence.objects.filter(user=user, active=True, valid_to__gte=day).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=day)
    )
    if regulators:
        queryset = queryset.filter(regulator__in=regulators)
    return queryset.exists()


def _ensure(actor: Any, facility: Any) -> None:
    if not policies.has_permission(actor, "access.licence.manage", facility=facility):
        raise PermissionDenied("You do not have permission to manage licences here.")


@transaction.atomic
def add_licence(*, user: User, actor: Any, facility: Any, **fields: Any) -> ProfessionalLicence:
    _ensure(actor, facility)
    unknown = set(fields) - LICENCE_FIELDS
    if unknown:
        raise ValidationError({name: "Unknown field." for name in unknown})
    licence = ProfessionalLicence(user=user, **fields)
    licence.full_clean()
    licence.save()
    record(
        "access.licence.added",
        actor,
        licence,
        facility=facility,
        detail={"user_id": user.pk, "regulator": licence.regulator, "valid_to": licence.valid_to},
    )
    return licence


@transaction.atomic
def update_licence(
    licence: ProfessionalLicence, *, actor: Any, facility: Any, **changes: Any
) -> ProfessionalLicence:
    _ensure(actor, facility)
    unknown = set(changes) - LICENCE_FIELDS
    if unknown:
        raise ValidationError({name: "Unknown field." for name in unknown})
    licence = ProfessionalLicence.objects.select_for_update().get(pk=licence.pk)
    changed = [name for name, value in changes.items() if getattr(licence, name) != value]
    for name in changed:
        setattr(licence, name, changes[name])
    if {"regulator", "registration_number"} & set(changed):
        licence.verified_at = None
        licence.verification_source = ""
        licence.puid = ""
    licence.full_clean()
    licence.save()
    if changed:
        record(
            "access.licence.updated",
            actor,
            licence,
            facility=facility,
            detail={"fields": sorted(changed)},
        )
    return licence


def verify_licence(
    licence: ProfessionalLicence, *, actor: Any, facility: Any
) -> ProfessionalLicence:
    """Check the registration against the Health Worker Registry and store the PUID."""
    _ensure(actor, facility)
    registry = get_registry()
    found = registry.lookup(licence.regulator, licence.registration_number)
    if found is None or not found.active:
        record(
            "access.licence.verification_failed",
            actor,
            licence,
            facility=facility,
            outcome="failure",
            detail={"source": registry.source, "found": found is not None},
        )
        raise ValidationError(
            {"registration_number": "The registry has no active registration with this number."}
        )
    with transaction.atomic():
        licence = ProfessionalLicence.objects.select_for_update().get(pk=licence.pk)
        licence.puid = found.puid
        licence.verified_at = timezone.now()
        licence.verification_source = registry.source
        if found.licence_valid_to is not None:
            licence.valid_to = found.licence_valid_to
        licence.save(
            update_fields=["puid", "verified_at", "verification_source", "valid_to", "updated_at"]
        )
        record(
            "access.licence.verified",
            actor,
            licence,
            facility=facility,
            detail={"source": registry.source, "valid_to": licence.valid_to},
        )
    return licence


def _facility_admins(user: User) -> list[User]:
    facilities = RoleAssignment.objects.filter(
        user=user, status=RoleAssignment.Status.ACTIVE
    ).values_list("facility_id", flat=True)
    admin_ids = (
        RoleAssignment.objects.filter(
            facility_id__in=list(facilities),
            role__code="facility_admin",
            status=RoleAssignment.Status.ACTIVE,
        )
        .exclude(user=user)
        .values_list("user_id", flat=True)
    )
    return list(User.objects.filter(pk__in=list(admin_ids), is_active=True))


def notify_expiring(today: date | None = None) -> int:
    """Warn the holder and their facility admins once, 30 days (or less) before expiry."""
    today = today or timezone.localdate()
    due = ProfessionalLicence.objects.filter(
        active=True,
        valid_to__gte=today,
        valid_to__lte=today + timedelta(days=WARN_DAYS),
        user__is_active=True,
    ).exclude(expiry_notified_for=F("valid_to"))
    sent = 0
    for licence in due.select_related("user"):
        expires = licence.valid_to.strftime("%d/%m/%Y")
        notify_user(
            licence.user,
            subject="Your practising licence expires soon",
            message=f"Your {licence.regulator} licence expires on {expires}. Renew it to keep clinical access.",
        )
        for admin in _facility_admins(licence.user):
            notify_user(
                admin,
                subject="A staff practising licence expires soon",
                message=(
                    f"The {licence.regulator} licence of {licence.user.email} expires on {expires}. "
                    "Clinical permissions stop when it expires."
                ),
            )
        ProfessionalLicence.objects.filter(pk=licence.pk).update(
            expiry_notified_for=licence.valid_to
        )
        record("access.licence.expiry_warned", None, licence, detail={"valid_to": licence.valid_to})
        sent += 1
    return sent
