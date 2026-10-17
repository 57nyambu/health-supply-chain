"""Eligibility checks (P3-SHA-01 acceptance 3; INSURANCE.md §1, §3.2; KE-SHA-01, KE-SHA-03).

Every check leaves an ``EligibilityCheck`` snapshot (who, when, what the payer said, the
raw answer encrypted) and moves ``Coverage.verification``. A payer outage never blocks
reception: the snapshot is ``pending_verification`` and the cover stays as it was
(DESIGN §16 degraded mode). Emergencies never wait for this (ADR-013).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.access import policies
from apps.audit.services import record
from apps.core import crypto, events
from apps.core.problems import ApiProblem
from apps.insurance.adapters import gateway_for
from apps.insurance.gateway import (
    ConfigurationError,
    EligibilityResult,
    EligibilityStatus,
    PayerServiceCode,
    RateLimited,
    TransientError,
    ValidationRejected,
)
from apps.insurance.models import Coverage, EligibilityCheck
from apps.insurance.refs import coverage_ref

PENDING_MESSAGE = "The payer is not answering. Carry on with the visit and check again later."
VERIFICATION = {
    EligibilityStatus.ELIGIBLE: Coverage.Verification.VERIFIED,
    EligibilityStatus.NOT_ELIGIBLE: Coverage.Verification.FAILED,
    EligibilityStatus.INACTIVE: Coverage.Verification.FAILED,
    EligibilityStatus.NOT_FOUND: Coverage.Verification.FAILED,
}


class PayerNotConfigured(ApiProblem):
    status_code = 503
    default_detail = "This payer's integration is not set up yet."
    default_code = "payer_not_configured"


class PayerUnavailable(ApiProblem):
    status_code = 503
    default_detail = PENDING_MESSAGE
    default_code = "payer_unavailable"


def _ensure(actor: Any, code: str, facility: Any) -> None:
    if actor is not None and not policies.has_permission(actor, code, facility=facility):
        raise PermissionDenied("You do not have permission to do this here.")


def _request_hash(coverage: Coverage) -> str:
    ref = coverage_ref(coverage)
    if ref.cr_id:
        basis = f"cr:{ref.cr_id}"
    elif ref.identification is not None:
        basis = f"{ref.identification[0]}:{ref.identification[1].reveal()}"
    else:
        basis = f"member:{ref.member_number.reveal()}"
    return crypto.blind_index(basis, purpose="insurance.eligibility")


def check(coverage: Coverage, *, actor: Any, on: date | None = None) -> EligibilityCheck:
    """Ask the payer whether ``coverage`` is good on ``on`` (default today) and record it."""
    _ensure(actor, "insurance.eligibility.check", coverage.facility_id)
    day = on or timezone.localdate()
    payer = coverage.scheme.payer
    try:
        gateway = gateway_for(payer.gateway)
    except ConfigurationError as exc:
        raise PayerNotConfigured(str(exc)) from exc
    try:
        result = gateway.check_eligibility(coverage_ref(coverage), day)
    except (TransientError, RateLimited):
        result = EligibilityResult(EligibilityStatus.PENDING, message=PENDING_MESSAGE)
    except ValidationRejected as exc:
        raise ValidationError({"coverage": exc.violations}) from exc
    except ConfigurationError as exc:
        raise PayerNotConfigured(str(exc)) from exc
    with transaction.atomic():
        current = Coverage.objects.select_for_update().get(pk=coverage.pk)
        snapshot = EligibilityCheck.objects.create(
            facility_id=current.facility_id,
            coverage=current,
            gateway=gateway.code,
            mode=gateway.mode,
            status=result.status.value,
            checked_on=day,
            request_hash=_request_hash(current),
            member_ref=result.member_ref,
            summary=result.summary,
            message=result.message[:255],
            raw_payload=json.dumps(
                {
                    "status": result.status.value,
                    "schemes": [
                        {
                            "name": s.scheme_name,
                            "status": s.status,
                            "active": s.active,
                            "from": s.valid_from.isoformat() if s.valid_from else None,
                            "to": s.valid_to.isoformat() if s.valid_to else None,
                            "reason": s.reason,
                        }
                        for s in result.schemes
                    ],
                    "biometrics_enforced": result.biometrics_enforced,
                    "otp_allowed": result.otp_allowed,
                }
            ),
            trace_id=result.trace_id[:100],
            created_by=actor,
            updated_by=actor,
        )
        new_state = VERIFICATION.get(result.status)
        fields = ["version", "updated_by", "updated_at"]
        if new_state is not None:
            current.verification = new_state
            current.verified_at = timezone.now()
            fields += ["verification", "verified_at"]
        if result.member_ref and result.member_ref != current.payer_member_ref:
            current.payer_member_ref = result.member_ref
            fields.append("payer_member_ref")
        current.version += 1
        current.updated_by = actor
        current.save(update_fields=fields)
        record(
            "insurance.eligibility.checked",
            actor,
            snapshot,
            patient=current.patient_id,
            facility=current.facility_id,
            purpose="registration",
            detail={"status": result.status.value, "gateway": gateway.code, "mode": gateway.mode},
        )
        events.emit(
            "insurance.coverage.verified",
            aggregate=current,
            payload={"coverage_id": str(current.pk), "result": result.status.value},
        )
    return snapshot


def billable(coverage: Coverage, *, actor: Any) -> list[PayerServiceCode]:
    """The services the payer lists for this member (SHA interventions with their flags)."""
    _ensure(actor, "insurance.eligibility.check", coverage.facility_id)
    try:
        gateway = gateway_for(coverage.scheme.payer.gateway)
        codes = gateway.list_billable(coverage_ref(coverage))
    except ConfigurationError as exc:
        raise PayerNotConfigured(str(exc)) from exc
    except ValidationRejected as exc:
        raise ValidationError({"coverage": exc.violations}) from exc
    except (TransientError, RateLimited) as exc:
        raise PayerUnavailable() from exc
    record(
        "insurance.benefits.listed",
        actor,
        coverage,
        patient=coverage.patient_id,
        facility=coverage.facility_id,
        purpose="registration",
        detail={"count": len(codes), "gateway": gateway.code},
    )
    return codes


def latest(coverage: Coverage) -> EligibilityCheck | None:
    return EligibilityCheck.objects.filter(coverage=coverage).order_by("-created_at").first()


def snapshot_details(check: EligibilityCheck) -> dict[str, Any]:
    """The stored answer (schemes, flags) for the screen — IDs, codes and dates only."""
    try:
        data = json.loads(check.raw_payload or "{}")
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}
