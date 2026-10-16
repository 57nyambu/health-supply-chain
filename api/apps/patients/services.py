"""State changes and search for the patient registry (DESIGN §5, §6.1, §6.6). All audited."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.access import approvals, chart, policies
from apps.access.models import ApprovalRequest
from apps.access.roles import ChartAccess
from apps.audit.services import record
from apps.core import crypto
from apps.core.problems import ApiProblem, Conflict
from apps.core.sequences import next_value
from apps.facilities.models import Facility
from apps.patients import identifiers as ids
from apps.patients.models import (
    Consent,
    NextOfKin,
    Patient,
    PatientContact,
    PatientIdentifier,
    PatientMerge,
)

MIN_QUERY = 3
NAME_MATCH = 0.3
DUPLICATE_NAME_MATCH = 0.6
MERGE_ACTION = "patients.merge"
UNMERGE_ACTION = "patients.unmerge"
EDITABLE = {"given_name", "middle_name", "family_name", "sex", "date_of_birth", "dob_estimated"}


class LikelyDuplicate(ApiProblem):
    status_code = 409
    default_detail = "A patient who looks the same is already registered. Open that record, or give a reason to register anyway."
    default_code = "likely_duplicate"

    def __init__(self, candidates: list["Candidate"]) -> None:
        super().__init__()
        self.extra = {
            "candidates": [
                {"id": str(c.patient.pk), "score": c.score, "reasons": c.reasons}
                for c in candidates
            ]
        }


@dataclass
class Candidate:
    patient: Patient
    score: int
    reasons: list[str] = field(default_factory=list)


def _ensure(actor: Any, code: str, facility: Any) -> None:
    if not policies.has_permission(actor, code, facility=facility):
        raise PermissionDenied("You do not have permission to do this here.")


def _merge_candidates(
    found: dict[Any, Candidate], patient: Patient, score: int, reason: str
) -> None:
    current = found.get(patient.pk)
    if current is None:
        found[patient.pk] = Candidate(patient, score, [reason])
    else:
        current.score = max(current.score, score)
        if reason not in current.reasons:
            current.reasons.append(reason)


def _active_patients(facility_id: int) -> QuerySet[Patient]:
    return Patient.objects.filter(facility_id=facility_id, status=Patient.Status.ACTIVE)


def _exact_matches(facility_id: int, query: str, found: dict[Any, Candidate]) -> bool:
    matched = False
    for type_ in ids.candidate_types(query):
        rows = PatientIdentifier.objects.filter(
            facility_id=facility_id,
            type=type_,
            value_index=ids.index(type_, ids.normalise(query)),
            active=True,
            patient__status=Patient.Status.ACTIVE,
        ).select_related("patient")
        for row in rows:
            _merge_candidates(found, row.patient, 100, "identifier")
            matched = True
    try:
        phone = ids.normalise_phone(query)
    except ValidationError:
        return matched
    phone_rows = PatientContact.objects.filter(
        facility_id=facility_id,
        kind=PatientContact.Kind.PHONE,
        value_index=ids.phone_index(phone),
        active=True,
        patient__status=Patient.Status.ACTIVE,
    ).select_related("patient")
    for contact in phone_rows:
        _merge_candidates(found, contact.patient, 95, "phone")
        matched = True
    return matched


def _name_matches(
    facility_id: int,
    name: str,
    date_of_birth: date | None,
    sex: str | None,
    threshold: float,
    found: dict[Any, Candidate],
) -> None:
    rows = (
        _active_patients(facility_id)
        .annotate(similarity=TrigramSimilarity("search_name", name.lower()))
        .filter(similarity__gte=threshold)
        .order_by("-similarity")[:50]
    )
    for patient in rows:
        score = int(patient.similarity * 70)
        reasons = ["name"]
        if date_of_birth and patient.date_of_birth:
            if patient.date_of_birth == date_of_birth:
                score += 20
                reasons.append("date_of_birth")
            elif abs(patient.date_of_birth.year - date_of_birth.year) <= 1:
                score += 10
                reasons.append("birth_year")
        if sex and patient.sex == sex:
            score += 5
            reasons.append("sex")
        for reason in reasons:
            _merge_candidates(found, patient, score, reason)


def search(
    *,
    facility: Any,
    actor: Any,
    query: str,
    date_of_birth: date | None = None,
    sex: str | None = None,
    limit: int = 20,
) -> list[Candidate]:
    """Search-before-create: exact identifier/phone first, then fuzzy name + DOB scoring."""
    facility_id = int(getattr(facility, "pk", facility))
    if chart.baseline_level(actor, facility_id) == ChartAccess.NONE:
        raise PermissionDenied("Your role does not give access to patient records.")
    query = query.strip()
    found: dict[Any, Candidate] = {}
    exact = _exact_matches(facility_id, query, found) if query else False
    if not exact:
        if len(query) < MIN_QUERY:
            raise ValidationError(
                {"q": f"Type at least {MIN_QUERY} characters or an exact identifier."}
            )
        if any(ch.isalpha() for ch in query):
            _name_matches(facility_id, query, date_of_birth, sex, NAME_MATCH, found)
    results = sorted(found.values(), key=lambda c: (-c.score, c.patient.search_name))[:limit]
    record(
        "patients.patient.searched",
        actor,
        facility=facility_id,
        detail={
            "lookup_hmac": crypto.blind_index(query, purpose="audit.search"),
            "results": len(results),
        },
    )
    return results


def find_duplicates(
    *,
    facility_id: int,
    full_name: str,
    date_of_birth: date | None,
    sex: str,
    identifier_pairs: list[tuple[str, str]],
    phones: list[str],
) -> list[Candidate]:
    found: dict[Any, Candidate] = {}
    for type_, normalised in identifier_pairs:
        for row in PatientIdentifier.objects.filter(
            facility_id=facility_id,
            type=type_,
            value_index=ids.index(type_, normalised),
            active=True,
        ).select_related("patient"):
            _merge_candidates(found, row.patient, 100, "identifier")
    for phone in phones:
        for contact in PatientContact.objects.filter(
            facility_id=facility_id,
            kind=PatientContact.Kind.PHONE,
            value_index=ids.phone_index(phone),
            active=True,
            patient__status=Patient.Status.ACTIVE,
        ).select_related("patient"):
            _merge_candidates(found, contact.patient, 80, "phone")
    if full_name.strip():
        named: dict[Any, Candidate] = {}
        _name_matches(facility_id, full_name, date_of_birth, sex, DUPLICATE_NAME_MATCH, named)
        for candidate in named.values():
            same_person = "sex" in candidate.reasons and (
                "date_of_birth" in candidate.reasons
                or "birth_year" in candidate.reasons
                or date_of_birth is None
            )
            if same_person:
                _merge_candidates(found, candidate.patient, candidate.score, "name")
    return sorted(found.values(), key=lambda c: -c.score)


def estimate_dob(age_years: int | None, age_months: int | None, today: date | None = None) -> date:
    today = today or timezone.localdate()
    months = (age_years or 0) * 12 + (age_months or 0)
    if months < 0 or months > 130 * 12:
        raise ValidationError({"age_years": "Enter an age between 0 and 130."})
    year, month = divmod(today.year * 12 + (today.month - 1) - months, 12)
    return date(year, month + 1, min(today.day, 28))


def format_mrn(facility: Facility, seq: int, today: date) -> str:
    mfl = facility.mfl_code or f"F{facility.pk}"
    return facility.mrn_format.format(
        MFL=mfl, YY=f"{today.year % 100:02d}", YYYY=today.year, seq=seq
    )


def _new_mrn(facility: Facility) -> str:
    today = timezone.localdate()
    return format_mrn(
        facility, next_value(facility_id=facility.pk, name="mrn", year=today.year), today
    )


def _add_identifier(
    patient: Patient, actor: Any, type_: str, normalised: str, *, issuer: str = "", source: str
) -> PatientIdentifier:
    try:
        with transaction.atomic():
            return PatientIdentifier.objects.create(
                patient=patient,
                facility_id=patient.facility_id,
                type=type_,
                value=normalised,
                value_index=ids.index(type_, normalised),
                issuer=issuer,
                source=source,
                created_by=actor,
                updated_by=actor,
            )
    except IntegrityError as exc:
        raise ValidationError(
            {
                "identifiers": f"This {PatientIdentifier.Type(type_).label.lower()} is already registered to another patient."
            }
        ) from exc


def _contact_values(contacts: list[dict[str, Any]]) -> list[tuple[str, str, str, bool]]:
    rows = []
    for contact in contacts:
        kind = contact.get("kind")
        raw = str(contact.get("value", ""))
        if kind == PatientContact.Kind.PHONE:
            value = ids.normalise_phone(raw)
            rows.append((kind, value, ids.phone_index(value), bool(contact.get("is_primary"))))
        elif kind == PatientContact.Kind.EMAIL:
            value = raw.strip().lower()
            if "@" not in value:
                raise ValidationError({"contacts": "This is not a valid e-mail address."})
            rows.append((kind, value, ids.email_index(value), bool(contact.get("is_primary"))))
        else:
            raise ValidationError({"contacts": "Contact kind must be phone or email."})
    return rows


@transaction.atomic
def create_patient(
    *,
    facility: Facility,
    actor: Any,
    given_name: str,
    family_name: str,
    sex: str,
    middle_name: str = "",
    date_of_birth: date | None = None,
    age_years: int | None = None,
    age_months: int | None = None,
    identifiers: list[dict[str, Any]] | None = None,
    contacts: list[dict[str, Any]] | None = None,
    next_of_kin: list[dict[str, Any]] | None = None,
    override_reason: str = "",
    privacy_notice: dict[str, Any] | None = None,
) -> Patient:
    """Register a patient. ``privacy_notice`` ({version, method, given_by}) records that the
    notice was given (DESIGN §8.5); it is required for every identified registration."""
    _ensure(actor, "patients.patient.create", facility)
    if not privacy_notice:
        raise ValidationError({"privacy_notice": "Give the privacy notice and record how."})
    if not given_name.strip() or not family_name.strip():
        raise ValidationError({"given_name": "Enter the given and family names."})
    if sex not in Patient.Sex.values:
        raise ValidationError({"sex": "Choose a sex."})
    estimated = False
    if date_of_birth is None and (age_years is not None or age_months is not None):
        date_of_birth, estimated = estimate_dob(age_years, age_months), True
    if date_of_birth and date_of_birth > timezone.localdate():
        raise ValidationError({"date_of_birth": "The date of birth is in the future."})
    pairs = []
    for item in identifiers or []:
        type_ = str(item.get("type", ""))
        if type_ not in ids.ENTERABLE:
            raise ValidationError({"identifiers": "Unknown identifier type."})
        pairs.append(
            (type_, ids.validate(type_, str(item.get("value", ""))), str(item.get("issuer", "")))
        )
    contact_rows = _contact_values(contacts or [])
    full_name = " ".join(part for part in (given_name, middle_name, family_name) if part)
    duplicates = find_duplicates(
        facility_id=facility.pk,
        full_name=full_name,
        date_of_birth=date_of_birth,
        sex=sex,
        identifier_pairs=[(t, v) for t, v, _ in pairs],
        phones=[value for kind, value, _, _ in contact_rows if kind == PatientContact.Kind.PHONE],
    )
    if any("identifier" in c.reasons for c in duplicates):
        raise ValidationError(
            {"identifiers": "This identifier is already registered to another patient."}
        )
    if duplicates:
        if not override_reason.strip():
            raise LikelyDuplicate(duplicates)
        _ensure(actor, "patients.duplicate.override", facility)
    patient = Patient.objects.create(
        facility=facility,
        mrn=_new_mrn(facility),
        given_name=given_name.strip(),
        middle_name=middle_name.strip(),
        family_name=family_name.strip(),
        sex=sex,
        date_of_birth=date_of_birth,
        dob_estimated=estimated,
        created_by=actor,
        updated_by=actor,
    )
    for type_, normalised, issuer in pairs:
        _add_identifier(
            patient, actor, type_, normalised, issuer=issuer, source=PatientIdentifier.Source.MANUAL
        )
    for kind, value, value_index, primary in contact_rows:
        PatientContact.objects.create(
            patient=patient,
            facility=facility,
            kind=kind,
            value=value,
            value_index=value_index,
            is_primary=primary,
            created_by=actor,
            updated_by=actor,
        )
    for kin in next_of_kin or []:
        _add_kin(patient, actor, kin)
    from apps.patients.privacy import record_consent

    record_consent(
        patient,
        actor=actor,
        kind="privacy_notice",
        decision="given",
        version=str(privacy_notice.get("version", "")),
        method=str(privacy_notice.get("method", "")),
        given_by=str(privacy_notice.get("given_by", "patient")),
    )
    record(
        "patients.patient.created",
        actor,
        patient,
        patient=patient,
        facility=facility,
        detail={"id_types": sorted(t for t, _, _ in pairs), "age_estimated": estimated},
    )
    if duplicates:
        record(
            "patients.duplicate.overridden",
            actor,
            patient,
            patient=patient,
            facility=facility,
            severity="notice",
            detail={"candidates": [str(c.patient.pk) for c in duplicates], "reason_given": True},
        )
    return patient


def _add_kin(patient: Patient, actor: Any, kin: dict[str, Any]) -> NextOfKin:
    name = str(kin.get("name", "")).strip()
    relationship = str(kin.get("relationship", "")).strip()
    if not name or not relationship:
        raise ValidationError({"next_of_kin": "Enter the next of kin's name and relationship."})
    phone = ids.normalise_phone(str(kin["phone"])) if kin.get("phone") else ""
    return NextOfKin.objects.create(
        patient=patient,
        facility_id=patient.facility_id,
        name=name,
        relationship=relationship,
        phone=phone,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def update_patient(patient: Patient, *, actor: Any, version: int, **changes: Any) -> Patient:
    _ensure(actor, "patients.patient.update", patient.facility_id)
    unknown = set(changes) - EDITABLE
    if unknown:
        raise ValidationError({name: "This field cannot be changed here." for name in unknown})
    current = Patient.objects.select_for_update().get(pk=patient.pk)
    if current.status != Patient.Status.ACTIVE:
        raise ValidationError({"status": "This record was merged; update the surviving record."})
    if current.version != version:
        raise Conflict()
    changed = sorted(name for name, value in changes.items() if getattr(current, name) != value)
    for name in changed:
        setattr(current, name, changes[name])
    if changed:
        current.version += 1
        current.updated_by = actor
        current.save()
        record(
            "patients.patient.updated", actor, current, patient=current, detail={"fields": changed}
        )
    return current


@transaction.atomic
def add_identifier(
    patient: Patient, *, actor: Any, type_: str, value: str, issuer: str = ""
) -> PatientIdentifier:
    _ensure(actor, "patients.patient.update", patient.facility_id)
    if type_ not in ids.ENTERABLE:
        raise ValidationError({"type": "Unknown identifier type."})
    row = _add_identifier(
        patient,
        actor,
        type_,
        ids.validate(type_, value),
        issuer=issuer,
        source=PatientIdentifier.Source.MANUAL,
    )
    record("patients.identifier.added", actor, row, patient=patient, detail={"type": type_})
    return row


@transaction.atomic
def add_contact(
    patient: Patient, *, actor: Any, kind: str, value: str, is_primary: bool = False
) -> PatientContact:
    _ensure(actor, "patients.patient.update", patient.facility_id)
    [(kind, normalised, value_index, primary)] = _contact_values(
        [{"kind": kind, "value": value, "is_primary": is_primary}]
    )
    if primary:
        PatientContact.objects.filter(patient=patient, kind=kind, is_primary=True).update(
            is_primary=False
        )
    row = PatientContact.objects.create(
        patient=patient,
        facility_id=patient.facility_id,
        kind=kind,
        value=normalised,
        value_index=value_index,
        is_primary=primary,
        created_by=actor,
        updated_by=actor,
    )
    record("patients.contact.added", actor, row, patient=patient, detail={"kind": kind})
    return row


@transaction.atomic
def add_next_of_kin(patient: Patient, *, actor: Any, **kin: Any) -> NextOfKin:
    _ensure(actor, "patients.patient.update", patient.facility_id)
    row = _add_kin(patient, actor, kin)
    record("patients.next_of_kin.added", actor, row, patient=patient)
    return row


@transaction.atomic
def register_unidentified(
    *, facility: Facility, actor: Any, sex: str, approx_age_years: int | None = None
) -> Patient:
    """Emergency quick registration with a temporary ID and placeholder name (DESIGN §6.6)."""
    _ensure(actor, "patients.patient.register_unidentified", facility)
    if sex not in Patient.Sex.values:
        raise ValidationError({"sex": "Choose a sex (or unknown)."})
    today = timezone.localdate()
    temporary = f"ER-{today.year}-{next_value(facility_id=facility.pk, name='temporary', year=today.year):04d}"
    sex_label = {"female": "female", "male": "male"}.get(sex, "person")
    age = f", approx. {approx_age_years}y" if approx_age_years is not None else ""
    patient = Patient.objects.create(
        facility=facility,
        mrn=_new_mrn(facility),
        sex=sex,
        is_unidentified=True,
        description=f"Unknown {sex_label}{age}, {temporary}",
        date_of_birth=estimate_dob(approx_age_years, 0) if approx_age_years is not None else None,
        dob_estimated=approx_age_years is not None,
        created_by=actor,
        updated_by=actor,
    )
    _add_identifier(
        patient,
        actor,
        PatientIdentifier.Type.TEMPORARY,
        temporary,
        source=PatientIdentifier.Source.SYSTEM,
    )
    record(
        "patients.patient.registered_unidentified",
        actor,
        patient,
        patient=patient,
        facility=facility,
        severity="notice",
    )
    return patient


# --- merges (maker-checker, reversible) -----------------------------------------------------------


@transaction.atomic
def request_merge(
    *, survivor: Patient, duplicate: Patient, actor: Any, reason: str
) -> PatientMerge:
    _ensure(actor, "patients.merge.request", survivor.facility_id)
    if survivor.pk == duplicate.pk or survivor.facility_id != duplicate.facility_id:
        raise ValidationError({"duplicate": "Choose another record from the same facility."})
    if Patient.Status.MERGED in (survivor.status, duplicate.status):
        raise ValidationError({"duplicate": "One of the records is already merged."})
    if PatientMerge.objects.filter(
        duplicate=duplicate, status=PatientMerge.Status.REQUESTED
    ).exists():
        raise ValidationError(
            {"duplicate": "A merge of this record is already waiting for approval."}
        )
    merge = PatientMerge.objects.create(
        facility_id=survivor.facility_id,
        survivor=survivor,
        duplicate=duplicate,
        reason=reason.strip(),
        created_by=actor,
        updated_by=actor,
    )
    merge.approval = approvals.request_approval(
        action=MERGE_ACTION,
        facility=survivor.facility_id,
        requested_by=actor,
        payload={
            "merge_id": str(merge.pk),
            "survivor": str(survivor.pk),
            "duplicate": str(duplicate.pk),
        },
        required_permissions=["patients.merge.approve"],
        reason=reason,
        resource=("patients.patientmerge", str(merge.pk)),
    )
    merge.save(update_fields=["approval"])
    record(
        "patients.merge.requested",
        actor,
        merge,
        patient=survivor,
        detail={"duplicate_id": str(duplicate.pk)},
    )
    return merge


def _execute_merge(request: ApprovalRequest, approver: Any) -> None:
    merge = PatientMerge.objects.select_for_update().get(pk=request.payload["merge_id"])
    survivor = Patient.objects.select_for_update().get(pk=merge.survivor_id)
    duplicate = Patient.objects.select_for_update().get(pk=merge.duplicate_id)
    if Patient.Status.MERGED in (survivor.status, duplicate.status):
        raise ValidationError({"duplicate": "One of the records is already merged."})
    moved: dict[str, list[str]] = {
        "identifiers": [],
        "identifiers_deactivated": [],
        "contacts": [],
        "next_of_kin": [],
        "consents": [],
        "documents": [],
    }
    existing = set(
        PatientIdentifier.objects.filter(patient=survivor, active=True).values_list(
            "type", "value_index"
        )
    )
    for row in PatientIdentifier.objects.filter(patient=duplicate, active=True):
        if (row.type, row.value_index) in existing or row.type == PatientIdentifier.Type.TEMPORARY:
            PatientIdentifier.objects.filter(pk=row.pk).update(active=False)
            moved["identifiers_deactivated"].append(str(row.pk))
        else:
            PatientIdentifier.objects.filter(pk=row.pk).update(patient=survivor)
            moved["identifiers"].append(str(row.pk))
    for model, key in ((PatientContact, "contacts"), (NextOfKin, "next_of_kin")):
        pks = [
            str(pk)
            for pk in model.objects.filter(patient=duplicate, active=True).values_list(
                "pk", flat=True
            )
        ]
        model.objects.filter(pk__in=pks).update(patient=survivor)
        moved[key] = pks
    # Consents and documents follow the person; unmerge moves them back.
    from apps.documents import selectors as documents
    from apps.documents import services as document_services

    moved["consents"] = [
        str(pk) for pk in Consent.objects.filter(patient=duplicate).values_list("pk", flat=True)
    ]
    Consent.objects.filter(pk__in=moved["consents"]).update(patient=survivor)
    moved["documents"] = documents.ids_for_patient(duplicate)
    document_services.reassign(moved["documents"], survivor)
    duplicate.status = Patient.Status.MERGED
    duplicate.merged_into = survivor
    duplicate.version += 1
    duplicate.save(update_fields=["status", "merged_into", "version", "updated_at"])
    merge.status = PatientMerge.Status.MERGED
    merge.moved = moved
    merge.merged_at = timezone.now()
    merge.save(update_fields=["status", "moved", "merged_at", "updated_at"])
    record(
        "patients.merge.completed",
        approver,
        merge,
        patient=survivor,
        severity="notice",
        detail={
            "duplicate_id": str(duplicate.pk),
            "rows_moved": sum(len(v) for v in moved.values()),
        },
    )


@transaction.atomic
def request_unmerge(merge: PatientMerge, *, actor: Any, reason: str) -> PatientMerge:
    _ensure(actor, "patients.merge.request", merge.facility_id)
    if merge.status != PatientMerge.Status.MERGED:
        raise ValidationError({"status": "Only completed merges can be reversed."})
    merge.reversal_approval = approvals.request_approval(
        action=UNMERGE_ACTION,
        facility=merge.facility_id,
        requested_by=actor,
        payload={"merge_id": str(merge.pk)},
        required_permissions=["patients.merge.approve"],
        reason=reason,
        resource=("patients.patientmerge", str(merge.pk)),
    )
    merge.save(update_fields=["reversal_approval"])
    record("patients.merge.reversal_requested", actor, merge, patient=merge.survivor_id)
    return merge


def _execute_unmerge(request: ApprovalRequest, approver: Any) -> None:
    merge = PatientMerge.objects.select_for_update().get(pk=request.payload["merge_id"])
    if merge.status != PatientMerge.Status.MERGED:
        raise ValidationError({"status": "Only completed merges can be reversed."})
    duplicate = Patient.objects.select_for_update().get(pk=merge.duplicate_id)
    moved = merge.moved
    PatientIdentifier.objects.filter(pk__in=moved.get("identifiers", [])).update(patient=duplicate)
    PatientIdentifier.objects.filter(pk__in=moved.get("identifiers_deactivated", [])).update(
        active=True
    )
    PatientContact.objects.filter(pk__in=moved.get("contacts", [])).update(patient=duplicate)
    NextOfKin.objects.filter(pk__in=moved.get("next_of_kin", [])).update(patient=duplicate)
    from apps.documents import services as document_services

    Consent.objects.filter(pk__in=moved.get("consents", [])).update(patient=duplicate)
    document_services.reassign(moved.get("documents", []), duplicate)
    duplicate.status = Patient.Status.ACTIVE
    duplicate.merged_into = None
    duplicate.version += 1
    duplicate.save(update_fields=["status", "merged_into", "version", "updated_at"])
    merge.status = PatientMerge.Status.REVERSED
    merge.reversed_at = timezone.now()
    merge.save(update_fields=["status", "reversed_at", "updated_at"])
    record(
        "patients.merge.reversed",
        approver,
        merge,
        patient=merge.survivor_id,
        severity="notice",
        detail={"duplicate_id": str(duplicate.pk)},
    )


def register_executors() -> None:
    approvals.register_executor(MERGE_ACTION, _execute_merge)
    approvals.register_executor(UNMERGE_ACTION, _execute_unmerge)
