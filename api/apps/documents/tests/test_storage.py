import base64
import hashlib
import io
import json
import os
from typing import Any

import pytest
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured, ValidationError
from PIL import Image

from apps.access import breakglass, care_team
from apps.audit.models import AuditEvent
from apps.core.sensitivity import PLACEHOLDER, SensitiveRecord
from apps.documents import envelope, services, storage
from apps.documents.models import Document
from apps.patients.tests.factories import PatientFactory

from .conftest import BUCKET, pdf_bytes, upload_file

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DHA-05")]
URL = "/api/v1/documents/"
REASON = "Seen in casualty, chart needed"


@pytest.fixture
def patient(facility):
    return PatientFactory.create(facility=facility)


@pytest.fixture
def clinician(staff, patient):
    user = staff("clinical_officer")
    care_team.add_member(patient=patient, user=user, source="visit", source_id="v1")
    return user


def store(user, patient, data=None, **fields):
    return services.upload(
        actor=user,
        facility_id=patient.facility_id,
        content=upload_file(data or pdf_bytes()),
        filename=fields.pop("filename", "scan.pdf"),
        category=fields.pop("category", "lab_report"),
        patient=patient,
        **fields,
    )


def stored_bytes(document):
    return b"".join(storage.read(document.storage_backend, document.storage_key))


def content(document):
    return b"".join(services.plaintext(document))


@pytest.mark.req("KE-DPA-06")
def test_objects_are_encrypted_in_the_selected_backend(
    backend, clinician, patient, local_store, settings
):
    data = pdf_bytes(envelope.CHUNK * 2 + 123)  # three chunks
    document = store(clinician, patient, data)
    assert document.storage_backend == backend
    raw = stored_bytes(document)
    assert data[:200] not in raw and len(raw) == len(data) + 3 * envelope.TAG
    assert (
        document.sha256_cipher
        == hashlib.sha256(raw).hexdigest()
        == storage.stored_sha256(backend, document.storage_key)
    )
    assert document.sha256_plain == hashlib.sha256(data).hexdigest()
    assert content(document) == data
    assert document.storage_key.startswith(f"test/f{patient.facility_id}/lab_report/")
    assert (
        patient.mrn not in document.storage_key and patient.family_name not in document.storage_key
    )
    if backend == "local":
        assert (local_store / document.storage_key).is_file()
    assert document.original_filename == "scan.pdf"


def test_new_files_follow_the_switch_and_old_ones_stay_readable(
    s3_store, clinician, patient, settings
):
    settings.STORAGE_BACKEND = "local"
    on_local = store(clinician, patient)
    settings.STORAGE_BACKEND = "s3"
    on_s3 = store(clinician, patient)
    assert (on_local.storage_backend, on_s3.storage_backend) == ("local", "s3")
    assert s3_store.head_object(Bucket=BUCKET, Key=on_s3.storage_key)["ContentLength"] > 0
    assert content(on_local).startswith(b"%PDF") and content(on_s3).startswith(b"%PDF")


def test_s3_over_http_with_a_configured_endpoint(s3_http_store, clinician, patient):
    data = pdf_bytes(envelope.CHUNK + 1)
    document = store(clinician, patient, data)
    head = s3_http_store.head_object(Bucket=BUCKET, Key=document.storage_key)
    assert head["ContentLength"] == len(data) + 2 * envelope.TAG
    assert content(document) == data
    assert storage.stored_sha256("s3", document.storage_key) == document.sha256_cipher


def test_local_objects_default_to_data_dir(settings):
    from django.conf import settings as live

    stores: Any = live.STORAGES
    assert str(stores["local"]["OPTIONS"]["location"]) == str(live.DATA_DIR / "objects")
    assert live.STORAGE_BACKEND == "local" and live.STORAGE_ENCRYPTION is True


def test_unencrypted_mode_for_development(local_store, clinician, patient, settings):
    settings.STORAGE_ENCRYPTION = False
    data = pdf_bytes()
    document = store(clinician, patient, data)
    assert not document.encrypted and stored_bytes(document) == data == content(document)


def test_image_metadata_is_stripped(local_store, clinician, patient):
    image = Image.new("RGB", (8, 8), "white")
    exif = image.getexif()
    exif[0x010F] = "Synthetic camera maker"  # Make
    exif[0x0112] = 1  # Orientation
    raw = io.BytesIO()
    image.save(raw, format="JPEG", exif=exif.tobytes())
    assert b"Synthetic camera maker" in raw.getvalue()
    document = store(clinician, patient, raw.getvalue(), filename="photo.png", category="other")
    clean = content(document)
    assert document.content_type == "image/jpeg"  # by magic bytes, not by name
    assert b"Synthetic camera maker" not in clean
    assert dict(Image.open(io.BytesIO(clean)).getexif()) == {}


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"just some text pretending to be a pdf", "Upload a PDF"),
        (b"", "empty"),
        (b"\x89PNG\r\n\x1a\n" + b"not really an image", "could not be read"),
    ],
)
def test_type_checks(local_store, clinician, patient, data, message):
    with pytest.raises(ValidationError, match=message):
        services.upload(
            actor=clinician,
            facility_id=patient.facility_id,
            content=upload_file(data),
            filename="x.pdf",
            category="lab_report",
            patient=patient,
        )
    assert not Document.objects.exists()


def test_size_limit_and_allowed_types(local_store, clinician, patient, settings):
    settings.DOCUMENT_MAX_BYTES = 100
    with pytest.raises(ValidationError, match="larger"):
        store(clinician, patient, pdf_bytes(200))
    settings.DOCUMENT_MAX_BYTES = 10_000
    settings.DOCUMENT_ALLOWED_TYPES = ["image/png"]
    with pytest.raises(ValidationError, match="Upload a PDF"):
        store(clinician, patient)


def test_upload_rules(local_store, clinician, patient, staff, facility):
    from apps.facilities.tests.factories import FacilityFactory

    with pytest.raises(ValidationError):
        store(clinician, patient, category="audit_anchor")
    with pytest.raises(ValidationError):
        store(clinician, patient, sensitivity="secret")
    with pytest.raises(ValidationError):
        services.upload(
            actor=clinician,
            facility_id=patient.facility_id,
            content=upload_file(pdf_bytes()),
            filename="x.pdf",
            category="lab_report",
            patient=PatientFactory.create(facility=FacilityFactory.create()),
        )
    from django.core.exceptions import PermissionDenied

    with pytest.raises(PermissionDenied):
        store(staff("receptionist"), patient)
    unrelated = staff("nurse")
    unrelated_patient = PatientFactory.create(facility=facility)
    document = store(unrelated, unrelated_patient)  # summary access is enough to file a document
    assert document.patient == unrelated_patient


def test_superseding_keeps_both_versions(local_store, clinician, patient):
    first = store(clinician, patient)
    second = store(clinician, patient, supersedes=first)
    first.refresh_from_db()
    assert first.superseded_by == second
    with pytest.raises(ValidationError):
        store(clinician, patient, supersedes=first)  # no longer the current version


@pytest.mark.req("KE-DHA-06")
def test_s3_unavailable_on_write_leaves_no_row(s3_store, clinician, patient):
    s3_store.delete_bucket(Bucket=BUCKET)
    with pytest.raises(storage.StorageUnavailable):
        store(clinician, patient)
    assert not Document.objects.exists()


def test_existing_key_is_never_overwritten(local_store, clinician, patient):
    document = store(clinician, patient)
    with pytest.raises(storage.StorageUnavailable):
        storage.write("local", document.storage_key, [b"other bytes"])
    assert stored_bytes(document) != b"other bytes"


def test_storage_errors_surface_as_unavailable(local_store, clinician, patient):
    document = store(clinician, patient)
    storage.delete("local", document.storage_key)
    assert not storage.exists("local", document.storage_key)
    with pytest.raises(storage.StorageUnavailable):
        content(document)
    with pytest.raises(ValueError):
        storage.get_backend("ftp")


def test_corrupted_object_fails_its_integrity_check(local_store, api_as, clinician, patient):
    document = store(clinician, patient)
    path = local_store / document.storage_key
    corrupted = bytearray(path.read_bytes())
    corrupted[40] ^= 0xFF
    path.write_bytes(bytes(corrupted))
    with pytest.raises(envelope.EnvelopeError):
        content(document)
    response = api_as(facility=patient.facility, user=clinician).get(f"{URL}{document.pk}/content/")
    assert response.status_code == 500 and response.json()["code"] == "document_unreadable"


def test_truncated_object_is_detected(local_store, clinician, patient):
    document = store(clinician, patient, pdf_bytes(envelope.CHUNK + 10))
    path = local_store / document.storage_key
    path.write_bytes(path.read_bytes()[: envelope.CHUNK + envelope.TAG])  # drop the final chunk
    with pytest.raises(envelope.EnvelopeError):
        content(document)


def test_wrong_master_key_is_an_error_not_a_leak(local_store, api_as, clinician, patient, settings):
    settings.STORAGE_MASTER_KEYS = json.dumps({"k1": base64.b64encode(os.urandom(32)).decode()})
    document = store(clinician, patient)
    settings.STORAGE_MASTER_KEYS = json.dumps({"k2": base64.b64encode(os.urandom(32)).decode()})
    with pytest.raises(envelope.EnvelopeError):
        content(document)
    settings.STORAGE_MASTER_KEYS = json.dumps({"k1": base64.b64encode(os.urandom(32)).decode()})
    with pytest.raises(envelope.EnvelopeError):
        content(document)
    response = api_as(facility=patient.facility, user=clinician).get(f"{URL}{document.pk}/content/")
    assert response.status_code == 500 and b"%PDF" not in response.content


@pytest.mark.req("KE-DHA-06")
@pytest.mark.req("KE-DPA-07")
def test_residency_guard_strict_refuses_a_foreign_bucket(settings):
    settings.DATA_RESIDENCY_MODE = "strict"
    settings.STORAGE_BACKEND = "s3"
    settings.S3_ENDPOINT_URL = "https://eu2.contabostorage.com"
    settings.RESIDENCY_ALLOWED_HOSTS = ["objects.example.ke"]
    with pytest.raises(ImproperlyConfigured, match="Object storage"):
        apps.get_app_config("documents").ready()
    settings.RESIDENCY_ALLOWED_HOSTS = ["eu2.contabostorage.com"]
    apps.get_app_config("documents").ready()


def test_residency_guard_warn_disables_s3(settings):
    settings.DATA_RESIDENCY_MODE = "warn"
    settings.STORAGE_BACKEND = "s3"
    settings.S3_ENDPOINT_URL = "https://eu2.contabostorage.com"
    settings.RESIDENCY_ALLOWED_HOSTS = []
    with pytest.raises(storage.StorageUnavailable):
        storage.get_backend("s3")
    settings.STORAGE_BACKEND = "local"
    settings.S3_ENDPOINT_URL = ""
    assert storage.check_residency() is True
    settings.STORAGE_BACKEND = "nowhere"
    with pytest.raises(storage.StorageUnavailable):
        storage.default_backend_name()


# --- reading through the API -------------------------------------------------------------------


def test_content_is_streamed_with_safe_headers_and_audited(backend, api_as, clinician, patient):
    data = pdf_bytes(envelope.CHUNK + 5)
    document = store(clinician, patient, data)
    response = api_as(facility=patient.facility, user=clinician).get(f"{URL}{document.pk}/content/")
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == data
    assert response["Content-Type"] == "application/pdf"
    assert response["Cache-Control"] == "no-store"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert "scan" not in response["Content-Disposition"]
    viewed = AuditEvent.objects.get(action="documents.document.viewed")
    assert (str(viewed.patient_id), viewed.detail["level"]) == (str(patient.pk), "full")


def test_upload_and_list_through_the_api(local_store, api_as, clinician, patient):
    client = api_as(facility=patient.facility, user=clinician)
    created = client.post(
        URL,
        {
            "file": upload_file(pdf_bytes(), "Result.pdf"),
            "category": "lab_report",
            "patient": str(patient.pk),
        },
        format="multipart",
    )
    assert created.status_code == 201, created.json()
    assert (
        created.json()["filename"] == "Result.pdf" and created.json()["storage_backend"] == "local"
    )
    listed = client.get(URL, {"patient": str(patient.pk)}).json()["results"]
    assert [row["id"] for row in listed] == [created.json()["id"]]
    assert client.get(f"{URL}{created.json()['id']}/").json()["category"] == "lab_report"
    assert client.post(URL, {"category": "lab_report"}, format="multipart").status_code == 400
    bad = client.post(
        URL,
        {
            "file": upload_file(pdf_bytes()),
            "category": "lab_report",
            "patient": "0190f7a0-0000-7000-8000-000000000000",
        },
        format="multipart",
    )
    assert bad.status_code == 400
    assert (
        client.post(
            URL,
            {
                "file": upload_file(pdf_bytes()),
                "category": "lab_report",
                "supersedes": "0190f7a0-0000-7000-8000-000000000000",
            },
            format="multipart",
        ).status_code
        == 400
    )
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "documents.document.uploaded",
        "documents.document.listed",
        "documents.document.metadata_viewed",
    } <= actions


def test_clinician_off_the_care_team_needs_break_glass_for_clinical_documents(
    local_store, api_as, staff, clinician, patient
):
    document = store(clinician, patient)
    other = staff("clinical_officer")
    client = api_as(facility=patient.facility, user=other)
    refused = client.get(f"{URL}{document.pk}/content/")
    assert refused.status_code == 403 and refused.json()["break_glass_available"] is True
    assert AuditEvent.objects.filter(action="documents.document.denied").exists()
    breakglass.request_access(user=other, patient=patient, reason="emergency", justification=REASON)
    allowed = client.get(f"{URL}{document.pk}/content/")
    assert allowed.status_code == 200
    viewed = AuditEvent.objects.filter(action="documents.document.viewed").latest("ts")
    assert viewed.severity == "high" and viewed.detail["break_glass_id"]


def test_administrative_documents_need_only_demographic_access(
    local_store, api_as, staff, clinician, patient, grant
):
    id_scan = store(clinician, patient, category="id_scan")
    lab = store(clinician, patient)
    clerk = staff("receptionist")
    grant(clerk, "hrio", patient.facility)  # summary access, documents.document.read
    client = api_as(facility=patient.facility, user=clerk)
    assert client.get(f"{URL}{id_scan.pk}/content/").status_code == 200
    assert client.get(f"{URL}{lab.pk}/content/").status_code == 403
    assert [
        row["id"] for row in client.get(URL, {"patient": str(patient.pk)}).json()["results"]
    ] == [str(id_scan.pk)]


# --- sensitive categories (P1-UAC-09) ------------------------------------------------------------


@pytest.mark.req("KE-DPA-01")
def test_sensitive_documents_are_placeholders_without_the_permission(
    local_store, api_as, staff, clinician, patient
):
    hidden = store(clinician, patient, sensitivity="hiv")
    normal = store(clinician, patient)
    client = api_as(facility=patient.facility, user=clinician)  # care team, full, no read_sensitive
    listed = client.get(URL, {"patient": str(patient.pk)}).json()["results"]
    by_id = {row["id"]: row for row in listed}
    assert by_id[str(hidden.pk)] == {
        "id": str(hidden.pk),
        "kind": "document",
        "hidden": "sensitive",
        "label": PLACEHOLDER,
    }
    assert by_id[str(normal.pk)]["category"] == "lab_report"
    chart = client.get(f"/api/v1/patients/{patient.pk}/chart/").json()
    assert {
        "id": str(hidden.pk),
        "kind": "document",
        "hidden": "sensitive",
        "label": PLACEHOLDER,
    } in chart["record"]["documents"]
    assert client.get(f"{URL}{hidden.pk}/content/").status_code == 403
    assert client.get(f"{URL}{hidden.pk}/").status_code == 403

    supt = staff("medical_superintendent")
    care_team.add_member(patient=patient, user=supt, source="visit", source_id="v1")
    revealed = api_as(facility=patient.facility, user=supt)
    assert revealed.get(f"{URL}{hidden.pk}/content/").status_code == 200
    rows = revealed.get(URL, {"patient": str(patient.pk)}).json()["results"]
    assert {row.get("sensitivity") for row in rows} == {"hiv", "normal"}


@pytest.mark.req("KE-DPA-01")
def test_break_glass_does_not_reveal_sensitive_documents(
    local_store, api_as, staff, clinician, patient
):
    hidden = store(clinician, patient, sensitivity="mental_health")
    nurse = staff("nurse")
    breakglass.request_access(user=nurse, patient=patient, reason="emergency", justification=REASON)
    client = api_as(facility=patient.facility, user=nurse)
    assert client.get(f"{URL}{hidden.pk}/content/").status_code == 403
    chart = client.get(f"/api/v1/patients/{patient.pk}/chart/").json()
    assert chart["record"]["documents"][0]["hidden"] == "sensitive"


@pytest.mark.req("KE-DPA-01")
def test_notes_diagnoses_results_and_documents_carry_a_sensitivity_flag():
    clinical = [
        model
        for model in apps.get_models()
        if model.__name__.endswith(("Note", "NoteVersion", "Diagnosis", "Result", "Document"))
        and model._meta.app_label not in ("sales", "products")
    ]
    assert Document in clinical
    assert [m.__name__ for m in clinical if not issubclass(m, SensitiveRecord)] == []


def test_process_documents_need_their_own_permission(local_store, api_as, clinician, patient):
    document = store(clinician, patient)
    Document.objects.filter(pk=document.pk).update(category="dsar_export")
    response = api_as(facility=patient.facility, user=clinician).get(f"{URL}{document.pk}/content/")
    assert response.status_code == 403
    assert (
        api_as(facility=patient.facility, user=clinician)
        .get(URL, {"patient": str(patient.pk)})
        .json()["results"]
        == []
    )


def test_documents_of_other_facilities_are_invisible(local_store, api_as, clinician, patient):
    from apps.facilities.tests.factories import FacilityFactory

    document = store(clinician, patient)
    elsewhere = api_as("clinical_officer", facility=FacilityFactory.create())
    assert elsewhere.get(f"{URL}{document.pk}/content/").status_code == 404
