"""Privacy notice and consents (DESIGN §8.5, KE-DPA-05, KE-HLT-03).

Reception gives the notice at registration and records the acknowledgement with the notice
version, how it was given and who acknowledged it; the staff member is ``created_by``.
Change ``NOTICE_VERSION`` whenever the wording changes.
"""

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.access import policies
from apps.audit.services import record
from apps.facilities.models import Facility
from apps.patients.models import Consent, Patient

NOTICE_VERSION = "2026-10"


def notice(facility: Facility) -> dict[str, str]:
    controller = facility.odpc_controller_registration or "pending registration"
    text = (
        f"{facility.name} collects your name, contacts, identifiers and health information to "
        "register you, treat you, bill you or your insurer, report to the Ministry of Health as "
        "the law requires, and keep your record. Your information is kept confidential, shared "
        "only with people involved in your care, your payer and authorities the law names, and "
        "kept in Kenya. You may ask to see, correct or receive a copy of your information, object "
        "to some uses, or complain to the Office of the Data Protection Commissioner. Ask "
        "reception for the Data Protection Officer. "
        f"Data controller registration (ODPC): {controller}."
    )
    return {"version": NOTICE_VERSION, "text": text}


def current(patient: Patient) -> dict[str, Consent]:
    """The latest decision per kind."""
    latest: dict[str, Consent] = {}
    for row in patient.consents.order_by("created_at"):
        latest[row.kind] = row
    return latest


@transaction.atomic
def record_consent(
    patient: Patient,
    *,
    actor: Any,
    kind: str,
    decision: str,
    method: str,
    version: str = "",
    given_by: str = Consent.GivenBy.PATIENT,
) -> Consent:
    if not policies.has_permission(actor, "patients.consent.record", facility=patient.facility_id):
        raise PermissionDenied("You may not record consents here.")
    if kind not in Consent.Kind.values:
        raise ValidationError({"kind": "Unknown consent."})
    if decision not in Consent.Decision.values:
        raise ValidationError({"decision": "Choose given, declined or withdrawn."})
    if method not in Consent.Method.values:
        raise ValidationError({"method": "Say how the notice or request was given."})
    if given_by not in Consent.GivenBy.values:
        raise ValidationError({"given_by": "Say who gave the answer."})
    if kind == Consent.Kind.PRIVACY_NOTICE:
        if version != NOTICE_VERSION:
            raise ValidationError({"version": "Show the current privacy notice and try again."})
        if decision != Consent.Decision.GIVEN:
            raise ValidationError({"decision": "The privacy notice is acknowledged, not declined."})
    row = Consent.objects.create(
        patient=patient,
        facility_id=patient.facility_id,
        kind=kind,
        decision=decision,
        method=method,
        notice_version=version,
        given_by=given_by,
        created_by=actor,
        updated_by=actor,
    )
    record(
        "patients.consent.recorded",
        actor,
        row,
        patient=patient,
        detail={"kind": kind, "decision": decision, "version": version, "method": method},
    )
    return row
