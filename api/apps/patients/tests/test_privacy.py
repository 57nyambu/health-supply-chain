import json
from datetime import datetime, timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.access import care_team
from apps.audit.models import AuditEvent
from apps.core.sensitivity import PLACEHOLDER
from apps.documents import services as documents
from apps.documents.models import Document
from apps.documents.tests.conftest import pdf_bytes, upload_file
from apps.patients import dsar, privacy
from apps.patients.models import Consent, DataSubjectRequest, Patient
from apps.patients.tests.factories import PatientFactory

from .test_registry import AMINA

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DPA-05")]
URL = "/api/v1/patients/"
DSAR = f"{URL}dsar/"
NOTICE: dict[str, Any] = {"version": privacy.NOTICE_VERSION, "method": "verbal"}


@pytest.fixture
def reception(api_as, facility):
    return api_as("receptionist", facility=facility)


@pytest.fixture
def dpo(api_as, facility):
    return api_as("dpo", facility=facility)


@pytest.fixture
def patient(facility):
    return PatientFactory.create(facility=facility)


# --- privacy notice and consents -------------------------------------------------------------------


@pytest.mark.req("KE-HLT-03")
def test_registration_records_the_privacy_notice_acknowledgement(reception):
    body = reception.post(
        URL, {**AMINA, "privacy_notice": {**NOTICE, "given_by": "guardian"}}, format="json"
    ).json()
    [ack] = body["consents"]
    assert (ack["kind"], ack["decision"], ack["version"], ack["method"], ack["given_by"]) == (
        "privacy_notice",
        "given",
        privacy.NOTICE_VERSION,
        "verbal",
        "guardian",
    )
    assert ack["recorded_by"] == reception.user.pk
    event = AuditEvent.objects.get(action="patients.consent.recorded")
    assert event.detail["version"] == privacy.NOTICE_VERSION


def test_registration_needs_the_current_notice(reception):
    without = {key: value for key, value in AMINA.items() if key != "privacy_notice"}
    assert reception.post(URL, without, format="json").status_code == 400
    stale = reception.post(
        URL, {**AMINA, "privacy_notice": {"version": "2019-01", "method": "verbal"}}, format="json"
    )
    assert stale.status_code == 400 and stale.json()["errors"][0]["field"] == "version"
    assert not Patient.objects.exists()


def test_the_notice_names_the_facility_and_its_odpc_registration(reception, facility):
    facility.odpc_controller_registration = "ODPC-TEST-0001"
    facility.save()
    notice = reception.get(f"{URL}privacy-notice/").json()
    assert notice["version"] == privacy.NOTICE_VERSION
    assert facility.name in notice["text"] and "ODPC-TEST-0001" in notice["text"]


def test_consents_are_append_only_and_the_latest_counts(reception, patient):
    url = f"{URL}{patient.pk}/consents/"
    assert (
        reception.post(
            url, {"kind": "sms_reminders", "decision": "given", "method": "verbal"}, format="json"
        ).status_code
        == 201
    )
    assert (
        reception.post(
            url,
            {"kind": "sms_reminders", "decision": "withdrawn", "method": "verbal"},
            format="json",
        ).status_code
        == 201
    )
    assert Consent.objects.filter(patient=patient, kind="sms_reminders").count() == 2
    current = {
        c["kind"]: c["decision"] for c in reception.get(f"{URL}{patient.pk}/").json()["consents"]
    }
    assert current == {"sms_reminders": "withdrawn"}
    declined_notice = {
        "kind": "privacy_notice",
        "decision": "declined",
        "method": "verbal",
        "version": privacy.NOTICE_VERSION,
    }
    assert reception.post(url, declined_notice, format="json").status_code == 400


def test_unidentified_patients_acknowledge_the_notice_later(reception):
    unknown = reception.post(f"{URL}unidentified/", {"sex": "male"}, format="json").json()
    assert unknown["consents"] == []
    later = reception.post(
        f"{URL}{unknown['id']}/consents/",
        {"kind": "privacy_notice", "decision": "given", **NOTICE},
        format="json",
    )
    assert later.status_code == 201


def test_consent_service_validation(make_user, patient, grant):
    clerk = make_user()
    grant(clerk, "receptionist", patient.facility)
    from django.core.exceptions import PermissionDenied, ValidationError

    with pytest.raises(PermissionDenied):
        privacy.record_consent(
            patient, actor=make_user(), kind="research", decision="given", method="verbal"
        )
    for bad in (
        {"kind": "marketing"},
        {"decision": "maybe"},
        {"method": "telepathy"},
        {"given_by": "neighbour"},
    ):
        values = {"kind": "research", "decision": "given", "method": "verbal", **bad}
        with pytest.raises(ValidationError):
            privacy.record_consent(patient, actor=clerk, **values)


@pytest.mark.req("KE-DHA-05")
def test_retention_fields_exist_on_patients_and_documents(reception):
    body = reception.post(URL, AMINA, format="json").json()
    assert body["retention_until"] is None and body["legal_hold"] is False
    assert {"retention_until", "legal_hold"} <= {f.name for f in Document._meta.get_fields()}


# --- data subject requests -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "days"),
    [
        ("access", 7),
        ("correction", 14),
        ("deletion", 14),
        ("objection", 14),
        ("restriction", 14),
        ("portability", 30),
    ],
)
def test_due_dates_follow_the_regulations(dpo, patient, kind, days):
    created = dpo.post(
        DSAR, {"patient": str(patient.pk), "kind": kind, "channel": "in_person"}, format="json"
    ).json()
    received = datetime.fromisoformat(created["received_at"])
    due = datetime.fromisoformat(created["due_at"])
    assert due - received == timedelta(days=days)
    assert created["reference"] == f"DSAR-{timezone.localdate().year}-0001"
    assert created["status"] == "received" and created["overdue"] is False


def test_overdue_requests_are_flagged(dpo, patient, make_user, grant):
    officer = make_user()
    grant(officer, "dpo", patient.facility)
    late = dsar.receive(
        actor=officer,
        patient=patient,
        kind="access",
        channel="letter",
        received_at=timezone.now() - timedelta(days=8),
    )
    dsar.receive(actor=officer, patient=patient, kind="portability", channel="email")
    overdue = dpo.get(DSAR, {"overdue": "true"}).json()["results"]
    assert [row["id"] for row in overdue] == [str(late.pk)]
    assert overdue[0]["overdue"] is True
    assert AuditEvent.objects.filter(action="patients.dsar.register_viewed").exists()


def test_access_request_export_is_fhir_shaped_and_hides_sensitive_items(
    api_as, dpo, staff, facility, settings, tmp_path
):
    from apps.documents.tests.conftest import BUCKET  # noqa: F401  (fixture module import)

    settings.STORAGES = {
        **settings.STORAGES,
        "local": {**settings.STORAGES["local"], "OPTIONS": {"location": tmp_path / "objects"}},
    }
    reception = api_as("receptionist", facility=facility)
    patient_id = reception.post(URL, AMINA, format="json").json()["id"]
    patient = Patient.objects.get(pk=patient_id)
    clinician = staff("clinical_officer")
    care_team.add_member(patient=patient, user=clinician, source="visit", source_id="v1")
    common = {
        "actor": clinician,
        "facility_id": facility.pk,
        "filename": "lab.pdf",
        "category": "lab_report",
        "patient": patient,
    }
    documents.upload(content=upload_file(pdf_bytes()), **common)
    secret = documents.upload(content=upload_file(pdf_bytes()), sensitivity="hiv", **common)

    request_id = dpo.post(
        DSAR, {"patient": patient_id, "kind": "access", "channel": "in_person"}, format="json"
    ).json()["id"]
    assert (
        dpo.post(f"{DSAR}{request_id}/export/", {}, format="json").status_code == 400
    )  # identity first
    verified = dpo.post(
        f"{DSAR}{request_id}/verify-identity/", {"evidence": "national_id_seen"}, format="json"
    )
    assert (
        verified.json()["status"] == "verified"
        and verified.json()["identity_verified_by"] == dpo.user.pk
    )
    exported = dpo.post(f"{DSAR}{request_id}/export/", {}, format="json").json()

    downloaded = dpo.get(f"{DSAR}{request_id}/download/json/")
    assert downloaded.status_code == 200 and downloaded["Cache-Control"] == "no-store"
    bundle = json.loads(b"".join(downloaded.streaming_content))
    resources: dict[str, list[dict[str, Any]]] = {}
    for entry in bundle["entry"]:
        resources.setdefault(entry["resource"]["resourceType"], []).append(entry["resource"])
    assert bundle["resourceType"] == "Bundle" and bundle["type"] == "collection"
    [fhir_patient] = resources["Patient"]
    assert fhir_patient["name"][0]["family"] == "Otieno" and fhir_patient["gender"] == "female"
    assert {"system": "urn:afyasync:identifier:national_id", "value": "00123456"} in fhir_patient[
        "identifier"
    ]
    assert fhir_patient["telecom"][0]["value"] == "+254700000111"
    assert resources["RelatedPerson"][0]["relationship"][0]["text"] == "brother"
    assert resources["Consent"][0]["status"] == "active"
    hidden = [d for d in resources["DocumentReference"] if d["id"] == str(secret.pk)]
    assert hidden[0]["description"] == PLACEHOLDER and "content" not in hidden[0]
    pdf = dpo.get(f"{DSAR}{request_id}/download/pdf/")
    assert pdf.status_code == 200 and b"".join(pdf.streaming_content).startswith(b"%PDF")

    # Exports are reached through the DSAR process only: the clinician cannot open them.
    clinician_client = api_as(facility=facility, user=clinician)
    assert (
        clinician_client.get(f"/api/v1/documents/{exported['export_json']}/content/").status_code
        == 403
    )
    assert (
        dpo.post(
            f"{DSAR}{request_id}/export/", {"include_sensitive": True}, format="json"
        ).status_code
        == 403
    )

    completed = dpo.post(
        f"{DSAR}{request_id}/close/",
        {"status": "completed", "outcome": "Copy handed over"},
        format="json",
    )
    assert completed.json()["status"] == "completed"
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "patients.dsar.received",
        "patients.dsar.identity_verified",
        "patients.dsar.exported",
        "patients.dsar.completed",
    } <= actions
    assert AuditEvent.objects.get(action="patients.dsar.completed").detail["late"] is False


def test_sensitive_items_need_the_permission_to_be_included(
    staff, make_user, grant, patient, settings, tmp_path
):
    settings.STORAGES = {
        **settings.STORAGES,
        "local": {**settings.STORAGES["local"], "OPTIONS": {"location": tmp_path / "objects"}},
    }
    officer = staff("medical_superintendent")
    grant(officer, "dpo", patient.facility)
    care_team.add_member(patient=patient, user=officer, source="visit", source_id="v9")
    hidden = documents.upload(
        actor=staff("clinical_officer"),
        facility_id=patient.facility_id,
        content=upload_file(pdf_bytes()),
        filename="x.pdf",
        category="lab_report",
        patient=patient,
        sensitivity="mental_health",
    )
    request = dsar.receive(actor=officer, patient=patient, kind="portability", channel="email")
    dsar.verify_identity(request, actor=officer, evidence="passport_seen")
    exported = dsar.export(request, actor=officer, include_sensitive=True)
    assert exported.export_json is not None
    bundle = json.loads(b"".join(documents.plaintext(exported.export_json)))
    revealed = [e["resource"] for e in bundle["entry"] if e["resource"]["id"] == str(hidden.pk)]
    assert revealed[0]["type"]["text"] == "Lab report"
    assert (
        AuditEvent.objects.get(action="patients.dsar.exported").detail["include_restricted"] is True
    )


def test_request_rules(dpo, patient, make_user, grant):
    from django.core.exceptions import PermissionDenied, ValidationError

    officer = make_user()
    grant(officer, "dpo", patient.facility)
    with pytest.raises(PermissionDenied):
        dsar.receive(actor=make_user(), patient=patient, kind="access", channel="email")
    for bad in (
        {"kind": "revenge"},
        {"channel": "pigeon"},
        {"requester": "stranger"},
        {"received_at": timezone.now() + timedelta(days=1)},
    ):
        values: dict[str, Any] = {"kind": "access", "channel": "email", **bad}
        with pytest.raises(ValidationError):
            dsar.receive(actor=officer, patient=patient, **values)
    correction = dsar.receive(actor=officer, patient=patient, kind="correction", channel="email")
    with pytest.raises(ValidationError):
        dsar.verify_identity(correction, actor=officer, evidence="vibes")
    dsar.verify_identity(correction, actor=officer, evidence="known_to_staff")
    with pytest.raises(ValidationError):
        dsar.verify_identity(correction, actor=officer, evidence="known_to_staff")
    with pytest.raises(ValidationError):
        dsar.export(correction, actor=officer)  # only access and portability export
    with pytest.raises(ValidationError):
        dsar.close(correction, actor=officer, status="completed", outcome="")
    with pytest.raises(ValidationError):
        dsar.close(correction, actor=officer, status="lost", outcome="x")
    dsar.close(
        correction,
        actor=officer,
        status="completed",
        outcome="Date of birth corrected by amendment",
    )
    with pytest.raises(ValidationError):
        dsar.close(correction, actor=officer, status="withdrawn", outcome="")

    access = dsar.receive(actor=officer, patient=patient, kind="access", channel="email")
    with pytest.raises(ValidationError):
        dsar.close(access, actor=officer, status="completed", outcome="done")  # not verified
    dsar.verify_identity(access, actor=officer, evidence="national_id_seen")
    with pytest.raises(ValidationError):
        dsar.close(access, actor=officer, status="completed", outcome="done")  # no export yet
    deletion = dsar.receive(actor=officer, patient=patient, kind="deletion", channel="letter")
    refused = dsar.close(
        deletion,
        actor=officer,
        status="refused",
        outcome="Health Act and DHA retention: records kept 20 years",
    )
    assert refused.status == DataSubjectRequest.Status.REFUSED
    withdrawn = dsar.close(
        dsar.receive(actor=officer, patient=patient, kind="objection", channel="phone"),
        actor=officer,
        status="withdrawn",
        outcome="",
    )
    assert withdrawn.closed_by == officer


def test_dsar_api_details_and_permissions(api_as, dpo, patient, facility):
    created = dpo.post(
        DSAR,
        {
            "patient": str(patient.pk),
            "kind": "access",
            "channel": "email",
            "details": "Wants a copy of all records",
        },
        format="json",
    ).json()
    detail = dpo.get(f"{DSAR}{created['id']}/").json()
    assert dpo.get(f"{DSAR}{created['id']}/download/pdf/").status_code == 404
    assert dpo.get(f"{DSAR}{created['id']}/download/docx/").status_code == 404
    assert detail["details"] == "Wants a copy of all records"
    assert AuditEvent.objects.filter(action="patients.dsar.viewed").exists()
    assert (
        dpo.post(
            DSAR,
            {
                "patient": "0190f7a0-0000-7000-8000-000000000000",
                "kind": "access",
                "channel": "email",
            },
            format="json",
        ).status_code
        == 400
    )
    assert dpo.get(DSAR, {"status": "received"}).json()["results"][0]["id"] == created["id"]
    closed = dpo.post(f"{DSAR}{created['id']}/close/", {"status": "withdrawn"}, format="json")
    assert closed.json()["status"] == "withdrawn"
    reception = api_as("receptionist", facility=facility)
    assert reception.get(DSAR).status_code == 403
    assert (
        reception.post(
            DSAR, {"patient": str(patient.pk), "kind": "access", "channel": "email"}, format="json"
        ).status_code
        == 403
    )


def test_merge_moves_consents_and_documents_and_unmerge_restores_them(
    api_as, staff, facility, settings, tmp_path
):
    settings.STORAGES = {
        **settings.STORAGES,
        "local": {**settings.STORAGES["local"], "OPTIONS": {"location": tmp_path / "objects"}},
    }
    reception = api_as("receptionist", facility=facility)
    unknown = reception.post(f"{URL}unidentified/", {"sex": "female"}, format="json").json()
    reception.post(
        f"{URL}{unknown['id']}/consents/",
        {"kind": "privacy_notice", "decision": "given", **NOTICE},
        format="json",
    )
    nurse = staff("nurse")
    document = documents.upload(
        actor=nurse,
        facility_id=facility.pk,
        content=upload_file(pdf_bytes()),
        filename="ecg.pdf",
        category="other",
        patient=Patient.objects.get(pk=unknown["id"]),
    )
    real = reception.post(URL, AMINA, format="json").json()
    hrio = api_as("hrio", facility=facility)
    approval = hrio.post(
        f"{URL}{real['id']}/merge/",
        {"duplicate": unknown["id"], "reason": "Identified"},
        format="json",
    ).json()["approval"]
    supervisor = api_as("hrio_supervisor", facility=facility)
    supervisor.post(f"/api/v1/access/approvals/{approval}/approve/")
    document.refresh_from_db()
    assert str(document.patient_id) == real["id"]
    assert Consent.objects.filter(patient_id=real["id"]).count() == 2
    from apps.patients.models import PatientMerge

    merge = PatientMerge.objects.get()
    reversal = hrio.post(
        f"{URL}merges/{merge.pk}/unmerge/", {"reason": "Wrong person"}, format="json"
    ).json()
    supervisor.post(f"/api/v1/access/approvals/{reversal['reversal_approval']}/approve/")
    document.refresh_from_db()
    assert str(document.patient_id) == unknown["id"]
    assert Consent.objects.filter(patient_id=unknown["id"]).count() == 1
