"""Snapshots of our records for the payer port (``gateway.CoverageRef`` …). Services build
them; adapters only ever see these, never our models (ADR-070)."""

from __future__ import annotations

from apps.facilities.models import Facility
from apps.insurance.gateway import CoverageRef, Secret
from apps.insurance.models import Coverage, Payer
from apps.patients.models import PatientIdentifier

# Identifiers a payer may be asked about, most specific first (SHA: CR ID by default).
LOOKUP_TYPES = (
    PatientIdentifier.Type.NATIONAL_ID,
    PatientIdentifier.Type.ALIEN_ID,
    PatientIdentifier.Type.REFUGEE_ID,
    PatientIdentifier.Type.BIRTH_CERTIFICATE,
    PatientIdentifier.Type.BIRTH_NOTIFICATION,
)


def _identifiers(coverage: Coverage) -> dict[str, str]:
    # A read of the patient's identifiers for the payer call; the caller audits the check.
    # (Requested from the integrator: a patients selector for this — PROGRESS-PHASE-3.)
    rows = PatientIdentifier.objects.filter(patient_id=coverage.patient_id, active=True).only(
        "type", "value"
    )
    found: dict[str, str] = {}
    for row in rows:
        found.setdefault(row.type, row.value)
    return found


def coverage_ref(coverage: Coverage) -> CoverageRef:
    identifiers = _identifiers(coverage)
    identification = next(
        ((t, Secret(identifiers[t])) for t in LOOKUP_TYPES if t in identifiers), None
    )
    facility = Facility.objects.only("fid").get(pk=coverage.facility_id)
    scheme = coverage.scheme
    return CoverageRef(
        coverage_id=str(coverage.pk),
        payer_code=scheme.payer.code,
        scheme_code=scheme.code,
        scheme_kind=scheme.kind,
        member_number=Secret(coverage.member_number),
        relationship=coverage.relationship,
        cr_id=identifiers.get(PatientIdentifier.Type.CLIENT_REGISTRY, "")
        or (coverage.payer_member_ref if scheme.payer.kind == Payer.Kind.SHA else ""),
        identification=identification,
        facility_code=facility.fid or "",
    )
