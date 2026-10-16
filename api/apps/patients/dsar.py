"""Data subject requests (DESIGN §8.6, KE-DPA-05, KE-DHA-08).

Due dates are calendar days from receipt, from the Data Protection (General) Regulations
2021 (Legal Notice 263; DECISIONS.md Findings 2026-10-16). Access and portability produce a
FHIR R4-shaped JSON bundle plus a readable PDF, stored as ``dsar_export`` documents that only
holders of ``patients.dsar.read`` can open. Sensitive categories are left out (placeholders)
unless the person producing the export holds ``clinical.record.read_sensitive`` and asks for
them (DESIGN §8.1: sensitive PHI is excluded from exports by default).
"""

import io
import json
from datetime import datetime, timedelta
from typing import Any
from xml.sax.saxutils import escape

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.access import policies
from apps.audit.services import record
from apps.core.sensitivity import PLACEHOLDER
from apps.core.sequences import next_value
from apps.documents.models import Document
from apps.documents.services import store_generated
from apps.patients.models import Consent, DataSubjectRequest, Patient

K = DataSubjectRequest.Kind
S = DataSubjectRequest.Status
# Regulation and days (Data Protection (General) Regulations 2021).
DUE_DAYS = {
    K.ACCESS: 7,  # reg. 9(4)
    K.CORRECTION: 14,  # reg. 10(4)
    K.PORTABILITY: 30,  # reg. 11(3)
    K.DELETION: 14,  # reg. 12(3)
    K.OBJECTION: 14,  # objection to processing, "within fourteen days of the request"
    K.RESTRICTION: 14,  # restriction of processing, "within fourteen days of the request"
}
EXPORT_KINDS = {K.ACCESS, K.PORTABILITY}
OPEN = {S.RECEIVED, S.VERIFIED}
EVIDENCE = {
    "national_id_seen",
    "passport_seen",
    "birth_certificate_seen",
    "known_to_staff",
    "other_document_seen",
}
READ_SENSITIVE = "clinical.record.read_sensitive"
GENDER = {"female": "female", "male": "male", "intersex": "other"}


def _ensure(actor: Any, code: str, facility_id: int) -> None:
    if not policies.has_permission(actor, code, facility=facility_id):
        raise PermissionDenied("You may not process data subject requests here.")


def due_at(kind: str, received_at: datetime) -> datetime:
    return received_at + timedelta(days=DUE_DAYS[DataSubjectRequest.Kind(kind)])


def is_overdue(request: DataSubjectRequest, at: datetime | None = None) -> bool:
    return request.status in OPEN and request.due_at < (at or timezone.now())


@transaction.atomic
def receive(
    *,
    actor: Any,
    patient: Patient,
    kind: str,
    channel: str,
    requester: str = DataSubjectRequest.Requester.PATIENT,
    details: str = "",
    received_at: datetime | None = None,
) -> DataSubjectRequest:
    _ensure(actor, "patients.dsar.process", patient.facility_id)
    if kind not in K.values:
        raise ValidationError({"kind": "Choose the right the person is exercising."})
    if channel not in DataSubjectRequest.Channel.values:
        raise ValidationError({"channel": "Say how the request arrived."})
    if requester not in DataSubjectRequest.Requester.values:
        raise ValidationError({"requester": "Say who made the request."})
    received_at = received_at or timezone.now()
    if received_at > timezone.now():
        raise ValidationError({"received_at": "The request cannot be received in the future."})
    year = timezone.localtime(received_at).year
    number = next_value(facility_id=patient.facility_id, name="dsar", year=year)
    request = DataSubjectRequest.objects.create(
        facility_id=patient.facility_id,
        reference=f"DSAR-{year}-{number:04d}",
        patient=patient,
        kind=kind,
        channel=channel,
        requester=requester,
        details=details.strip(),
        received_at=received_at,
        due_at=due_at(kind, received_at),
        created_by=actor,
        updated_by=actor,
    )
    record(
        "patients.dsar.received",
        actor,
        request,
        patient=patient,
        purpose="records",
        detail={"kind": kind, "due": request.due_at.date()},
    )
    return request


def _locked(request: DataSubjectRequest) -> DataSubjectRequest:
    return (
        DataSubjectRequest.objects.select_for_update().select_related("patient").get(pk=request.pk)
    )


@transaction.atomic
def verify_identity(
    request: DataSubjectRequest, *, actor: Any, evidence: str
) -> DataSubjectRequest:
    request = _locked(request)
    _ensure(actor, "patients.dsar.process", request.facility_id)
    if request.status != S.RECEIVED:
        raise ValidationError({"status": "Identity is verified once, on a new request."})
    if evidence not in EVIDENCE:
        raise ValidationError({"evidence": "Say how the requester's identity was checked."})
    request.status = S.VERIFIED
    request.identity_verified_by = actor
    request.identity_verified_at = timezone.now()
    request.identity_evidence = evidence
    request.updated_by = actor
    request.version += 1
    request.save()
    record(
        "patients.dsar.identity_verified",
        actor,
        request,
        patient=request.patient_id,
        purpose="records",
        detail={"evidence": evidence},
    )
    return request


# --- export --------------------------------------------------------------------------------------


def _ref(patient: Patient) -> dict[str, str]:
    return {"reference": f"Patient/{patient.pk}"}


def _patient_resource(patient: Patient) -> dict[str, Any]:
    identifiers = [
        {"use": "usual", "system": f"urn:afyasync:mrn:{patient.facility_id}", "value": patient.mrn}
    ]
    identifiers += [
        {"system": f"urn:afyasync:identifier:{row.type}", "value": row.value}
        for row in patient.identifiers.filter(active=True).order_by("created_at")
    ]
    telecom = [
        {"system": row.kind, "value": row.value, **({"rank": 1} if row.is_primary else {})}
        for row in patient.contacts.filter(active=True).order_by("created_at")
    ]
    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(patient.pk),
        "active": patient.status == Patient.Status.ACTIVE,
        "identifier": identifiers,
        "name": [
            {
                "use": "official",
                "family": patient.family_name,
                "given": [part for part in (patient.given_name, patient.middle_name) if part],
            }
        ],
        "gender": GENDER.get(patient.sex, "unknown"),
        "telecom": telecom,
    }
    if patient.date_of_birth:
        resource["birthDate"] = patient.date_of_birth.isoformat()
        if patient.dob_estimated:
            resource["_birthDate"] = {
                "extension": [{"url": "urn:afyasync:birth-date-estimated", "valueBoolean": True}]
            }
    return resource


def _kin_resources(patient: Patient) -> list[dict[str, Any]]:
    return [
        {
            "resourceType": "RelatedPerson",
            "id": str(kin.pk),
            "patient": _ref(patient),
            "relationship": [{"text": kin.relationship}],
            "name": [{"text": kin.name}],
            "telecom": [{"system": "phone", "value": kin.phone}] if kin.phone else [],
        }
        for kin in patient.next_of_kin.filter(active=True).order_by("created_at")
    ]


def _consent_resources(patient: Patient) -> list[dict[str, Any]]:
    status = {
        Consent.Decision.GIVEN: "active",
        Consent.Decision.DECLINED: "rejected",
        Consent.Decision.WITHDRAWN: "inactive",
    }
    return [
        {
            "resourceType": "Consent",
            "id": str(row.pk),
            "status": status[Consent.Decision(row.decision)],
            "scope": {"text": row.get_kind_display()},
            "patient": _ref(patient),
            "dateTime": row.created_at.isoformat(),
            "policyRule": {
                "text": f"version {row.notice_version}"
                if row.notice_version
                else row.get_method_display()
            },
        }
        for row in patient.consents.order_by("created_at")
    ]


def _document_resources(patient: Patient, reveal: bool) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for document in (
        Document.objects.filter(patient=patient)
        .exclude(category__in=[Document.Category.DSAR_EXPORT, Document.Category.AUDIT_ANCHOR])
        .order_by("created_at")
    ):
        if document.is_sensitive and not reveal:
            resources.append(
                {
                    "resourceType": "DocumentReference",
                    "id": str(document.pk),
                    "status": "current",
                    "meta": {
                        "security": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                                "code": "R",
                            }
                        ]
                    },
                    "description": PLACEHOLDER,
                }
            )
            continue
        resources.append(
            {
                "resourceType": "DocumentReference",
                "id": str(document.pk),
                "status": "superseded" if document.superseded_by_id else "current",
                "type": {"text": document.get_category_display()},
                "subject": _ref(patient),
                "date": document.created_at.isoformat(),
                "content": [
                    {
                        "attachment": {
                            "contentType": document.content_type,
                            "size": document.size,
                            "title": document.original_filename,
                        }
                    }
                ],
            }
        )
    return resources


def build_bundle(patient: Patient, *, include_sensitive: bool) -> dict[str, Any]:
    resources = [_patient_resource(patient)]
    resources += _kin_resources(patient) + _consent_resources(patient)
    resources += _document_resources(patient, include_sensitive)
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": timezone.now().isoformat(),
        "entry": [{"fullUrl": f"urn:uuid:{r['id']}", "resource": r} for r in resources],
    }


def _summary_pdf(request: DataSubjectRequest, bundle: dict[str, Any], facility_name: str) -> bytes:
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title="Personal data summary",
        author=facility_name,
    )
    resources = [entry["resource"] for entry in bundle["entry"]]
    patient = resources[0]
    story: list[Any] = [
        Paragraph("Personal data summary", styles["Title"]),
        Paragraph(f"{escape(facility_name)} — request {request.reference}", styles["Normal"]),
        Paragraph(f"Prepared {timezone.localtime():%d %b %Y %H:%M}", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]

    def section(title: str, rows: list[list[str]]) -> None:
        story.append(Paragraph(title, styles["Heading2"]))
        if not rows:
            story.append(Paragraph("None recorded.", styles["Normal"]))
            return
        table = Table(rows, colWidths=[55 * mm, 115 * mm])
        table.setStyle(
            TableStyle(
                [("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "TOP")]
            )
        )
        story.append(table)

    name = patient["name"][0]
    section(
        "Details",
        [
            ["Name", " ".join([*name["given"], name["family"]])],
            ["Sex", patient["gender"]],
            ["Date of birth", patient.get("birthDate", "not recorded")],
        ],
    )
    section(
        "Identifiers", [[i["system"].rsplit(":", 1)[-1], i["value"]] for i in patient["identifier"]]
    )
    section("Contacts", [[t["system"], t["value"]] for t in patient["telecom"]])
    section(
        "Next of kin",
        [
            [r["relationship"][0]["text"], r["name"][0]["text"]]
            for r in resources
            if r["resourceType"] == "RelatedPerson"
        ],
    )
    section(
        "Consents",
        [
            [r["scope"]["text"], f"{r['status']} ({r['dateTime'][:10]})"]
            for r in resources
            if r["resourceType"] == "Consent"
        ],
    )
    documents = [r for r in resources if r["resourceType"] == "DocumentReference"]
    section(
        "Documents",
        [
            [r.get("date", "")[:10] or "—", r.get("description") or r["type"]["text"]]
            for r in documents
        ],
    )
    if any(r.get("description") == PLACEHOLDER for r in documents):
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                "Some items are in a protected category and are not shown in this copy. Ask the "
                "Data Protection Officer how to receive them.",
                styles["Normal"],
            )
        )
    pdf.build(story)
    return buffer.getvalue()


@transaction.atomic
def export(
    request: DataSubjectRequest, *, actor: Any, include_sensitive: bool = False
) -> DataSubjectRequest:
    request = _locked(request)
    _ensure(actor, "patients.dsar.process", request.facility_id)
    if request.kind not in EXPORT_KINDS:
        raise ValidationError({"kind": "Only access and portability requests produce an export."})
    if request.status != S.VERIFIED:
        raise ValidationError({"status": "Verify the requester's identity before exporting."})
    if include_sensitive and not policies.has_permission(
        actor, READ_SENSITIVE, facility=request.facility_id
    ):
        raise PermissionDenied(
            "Including sensitive categories needs clinical.record.read_sensitive."
        )
    patient = request.patient
    bundle = build_bundle(patient, include_sensitive=include_sensitive)
    facility_name = patient.facility.name
    stem = f"{request.reference.lower()}"
    request.export_json = store_generated(
        actor=actor,
        facility_id=request.facility_id,
        data=json.dumps(bundle, indent=2, ensure_ascii=False).encode("utf-8"),
        content_type="application/json",
        filename=f"{stem}.json",
        category=Document.Category.DSAR_EXPORT,
        patient=patient,
    )
    request.export_pdf = store_generated(
        actor=actor,
        facility_id=request.facility_id,
        data=_summary_pdf(request, bundle, facility_name),
        content_type="application/pdf",
        filename=f"{stem}.pdf",
        category=Document.Category.DSAR_EXPORT,
        patient=patient,
    )
    request.updated_by = actor
    request.version += 1
    request.save()
    record(
        "patients.dsar.exported",
        actor,
        request,
        patient=patient,
        purpose="records",
        severity="notice",
        detail={
            "include_restricted": include_sensitive,
            "json_document": str(request.export_json.pk),
            "pdf_document": str(request.export_pdf.pk),
        },
    )
    return request


@transaction.atomic
def close(
    request: DataSubjectRequest, *, actor: Any, outcome: str, status: str
) -> DataSubjectRequest:
    """Complete, refuse (with the legal basis) or record a withdrawn request."""
    request = _locked(request)
    _ensure(actor, "patients.dsar.process", request.facility_id)
    if request.status not in OPEN:
        raise ValidationError({"status": "This request is already closed."})
    if status not in (S.COMPLETED, S.REFUSED, S.WITHDRAWN):
        raise ValidationError({"status": "Close as completed, refused or withdrawn."})
    if status != S.WITHDRAWN and not outcome.strip():
        raise ValidationError({"outcome": "Record what was done, or the legal basis for refusing."})
    if status == S.COMPLETED:
        if request.status != S.VERIFIED:
            raise ValidationError({"status": "Verify the requester's identity first."})
        if request.kind in EXPORT_KINDS and request.export_pdf_id is None:
            raise ValidationError({"status": "Produce the export before completing the request."})
    request.status = status
    request.outcome = outcome.strip()
    request.closed_at = timezone.now()
    request.closed_by = actor
    request.updated_by = actor
    request.version += 1
    request.save()
    record(
        f"patients.dsar.{status}",
        actor,
        request,
        patient=request.patient_id,
        purpose="records",
        detail={"kind": request.kind, "late": request.closed_at > request.due_at},
    )
    return request
