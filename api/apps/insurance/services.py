"""Coverage changes (audited). Phase 3 adds eligibility, consent, pre-authorisation and
claims here; Phase 2 reads through ``selectors`` only (docs/agent/lanes/SEAMS.md)."""

from datetime import date
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.access import policies
from apps.audit.services import record
from apps.core import crypto
from apps.insurance.models import Coverage, Scheme

MEMBER_INDEX_PURPOSE = "insurance.member_number"


def member_index(member_number: str) -> str:
    return crypto.blind_index(member_number, purpose=MEMBER_INDEX_PURPOSE)


def _ensure(actor: Any, code: str, facility: Any) -> None:
    if actor is not None and not policies.has_permission(actor, code, facility=facility):
        raise PermissionDenied("You do not have permission to do this here.")


@transaction.atomic
def add_coverage(
    *,
    patient: Any,
    scheme: Scheme,
    member_number: str,
    actor: Any,
    relationship: str = Coverage.Relationship.PRINCIPAL,
    valid_from: date | None = None,
    valid_to: date | None = None,
) -> Coverage:
    """Record that ``patient`` is a member of ``scheme`` (unverified until Phase 3 checks)."""
    _ensure(actor, "insurance.coverage.manage", patient.facility_id)
    number = crypto.normalise(member_number)
    if not 4 <= len(number) <= 40:
        raise ValidationError({"member_number": "Enter the member number from the card."})
    if not scheme.active or not scheme.payer.active:
        raise ValidationError({"scheme": "This scheme is not active."})
    if relationship not in Coverage.Relationship.values:
        raise ValidationError({"relationship": "Choose principal or dependant."})
    if valid_from and valid_to and valid_to < valid_from:
        raise ValidationError({"valid_to": "The end date is before the start date."})
    index = member_index(number)
    existing = Coverage.objects.filter(
        patient=patient, scheme=scheme, member_number_index=index, active=True
    ).first()
    if existing is not None:
        return existing
    coverage = Coverage.objects.create(
        facility_id=patient.facility_id,
        patient=patient,
        scheme=scheme,
        member_number=number,
        member_number_index=index,
        relationship=relationship,
        valid_from=valid_from,
        valid_to=valid_to,
        created_by=actor,
        updated_by=actor,
    )
    record(
        "insurance.coverage.added",
        actor,
        coverage,
        patient=patient,
        facility=patient.facility_id,
        detail={"scheme_code": scheme.code, "payer_code": scheme.payer.code},
    )
    return coverage


@transaction.atomic
def end_coverage(coverage: Coverage, *, actor: Any, reason: str) -> Coverage:
    """Deactivate a coverage (never deleted); the reason stays in the audit trail."""
    _ensure(actor, "insurance.coverage.manage", coverage.facility_id)
    if not reason.strip():
        raise ValidationError({"reason": "Say why the cover is ended."})
    current = Coverage.objects.select_for_update().get(pk=coverage.pk)
    if current.active:
        current.active = False
        current.version += 1
        current.updated_by = actor
        current.save(update_fields=["active", "version", "updated_by", "updated_at"])
        record(
            "insurance.coverage.ended",
            actor,
            current,
            patient=current.patient_id,
            facility=current.facility_id,
            detail={"reason_given": True},
        )
    return current
