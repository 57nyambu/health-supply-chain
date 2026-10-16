"""Reception lookups in the HIE Client Registry (P1-PAT-02, KE-DHA-04).

Local records come first: the local search runs before the registry is asked, and a
registry outage never stops reception (the registry part reports ``unavailable``).
Importing re-reads the registry server-side — demographics are never taken from the
browser — and creates a local record carrying the CR ID as a verified identifier.
"""

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError

from apps.access import policies
from apps.audit.services import record
from apps.core import crypto
from apps.core.problems import ApiProblem
from apps.facilities.models import Facility
from apps.patients import identifiers as ids
from apps.patients import services
from apps.patients.adapters.client_registry import (
    SEARCHABLE_TYPES,
    RegistryPerson,
    RegistryUnavailable,
    get_registry,
)
from apps.patients.models import Patient, PatientIdentifier


class RegistryDown(ApiProblem):
    status_code = 503
    default_detail = "The national Client Registry is not answering. Register the patient locally and link them later."
    default_code = "registry_unavailable"


@dataclass
class Lookup:
    local: list[services.Candidate]
    status: str  # found | not_found | unavailable
    person: RegistryPerson | None = None
    registered_patient: Patient | None = None


def _ensure(actor: Any, code: str, facility_id: int) -> None:
    if not policies.has_permission(actor, code, facility=facility_id):
        raise PermissionDenied("You may not use the Client Registry here.")


def _normalised(identifier_type: str, number: str) -> str:
    if identifier_type not in SEARCHABLE_TYPES:
        raise ValidationError(
            {
                "type": "The Client Registry is searched by national ID, Maisha Namba, alien ID or refugee ID."
            }
        )
    return ids.validate(identifier_type, number)


def _holder(facility_id: int, cr_id: str) -> Patient | None:
    row = (
        PatientIdentifier.objects.filter(
            facility_id=facility_id,
            type=PatientIdentifier.Type.CLIENT_REGISTRY,
            value_index=ids.index(PatientIdentifier.Type.CLIENT_REGISTRY, ids.normalise(cr_id)),
            active=True,
        )
        .select_related("patient")
        .first()
    )
    return row.patient if row else None


def lookup(*, actor: Any, facility_id: int, identifier_type: str, number: str) -> Lookup:
    _ensure(actor, "patients.registry.search", facility_id)
    normalised = _normalised(identifier_type, number)
    result = Lookup(
        local=services.search(facility=facility_id, actor=actor, query=normalised),
        status="not_found",
    )
    try:
        result.person = get_registry().find(identifier_type, normalised, facility_id=facility_id)
    except RegistryUnavailable:
        result.status = "unavailable"
    if result.person is not None:
        result.status = "found"
        result.registered_patient = _holder(facility_id, result.person.cr_id)
    record(
        "patients.registry.searched",
        actor,
        facility=facility_id,
        purpose="registration",
        detail={
            "lookup_hmac": crypto.blind_index(normalised, purpose="audit.search"),
            "id_type": identifier_type,
            "outcome": result.status,
        },
    )
    return result


def import_person(
    *,
    actor: Any,
    facility: Facility,
    identifier_type: str,
    number: str,
    privacy_notice: dict[str, Any],
    contacts: list[dict[str, Any]] | None = None,
    next_of_kin: list[dict[str, Any]] | None = None,
    override_reason: str = "",
) -> Patient:
    """Create a local record from the registry match, storing the CR ID (verified)."""
    _ensure(actor, "patients.registry.import", facility.pk)
    normalised = _normalised(identifier_type, number)
    registry = get_registry()
    try:
        person = registry.find(identifier_type, normalised, facility_id=facility.pk)
    except RegistryUnavailable as exc:
        raise RegistryDown() from exc
    if person is None:
        raise ValidationError({"number": "The Client Registry has no record for this identifier."})
    identifiers = [{"type": PatientIdentifier.Type.CLIENT_REGISTRY, "value": person.cr_id}]
    identifiers += [{"type": t, "value": v} for t, v in person.identifiers if t in ids.ENTERABLE]
    if not contacts and person.phone:
        contacts = [{"kind": "phone", "value": person.phone, "is_primary": True}]
    patient = services.create_patient(
        facility=facility,
        actor=actor,
        given_name=person.given_name,
        middle_name=person.middle_name,
        family_name=person.family_name,
        sex=person.sex,
        date_of_birth=person.date_of_birth,
        identifiers=identifiers,
        contacts=contacts or [],
        next_of_kin=next_of_kin or [],
        override_reason=override_reason,
        privacy_notice=privacy_notice,
        identifier_source=PatientIdentifier.Source.CLIENT_REGISTRY,
    )
    record(
        "patients.registry.imported",
        actor,
        patient,
        patient=patient,
        purpose="registration",
        detail={"mode": registry.mode},
    )
    return patient
