from datetime import date, timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.insurance import selectors, services
from apps.insurance.models import Coverage, Payer, Scheme
from apps.insurance.seed import payers_and_schemes
from apps.patients.tests.factories import PatientFactory

pytestmark = pytest.mark.django_db
URL = "/api/v1/insurance/"


@pytest.fixture
def schemes():
    return payers_and_schemes()


@pytest.fixture
def patient(facility):
    return PatientFactory.create(facility=facility)


@pytest.fixture
def reception(api_as, facility):
    return api_as("receptionist", facility=facility)


def test_seeded_payers_are_sha_and_clearly_synthetic_others(schemes):
    assert {s.payer.code for s in schemes.values()} == {
        "sha",
        "syn-insurer-a",
        "syn-insurer-b",
        "syn-employer",
    }
    assert Scheme.objects.get(payer__code="sha", code="shif").kind == Scheme.Kind.SHIF
    assert all(p.name.startswith("Synthetic") for p in Payer.objects.exclude(code="sha"))
    assert payers_and_schemes().keys() == schemes.keys()  # idempotent


def test_add_coverage_encrypts_indexes_audits_and_is_idempotent(schemes, patient, staff):
    clerk = staff("receptionist")
    shif = schemes["sha/shif"]
    coverage = services.add_coverage(
        patient=patient, scheme=shif, member_number="sha-syn 000123", actor=clerk
    )
    assert coverage.member_number == "SHA-SYN000123"
    assert coverage.verification == Coverage.Verification.UNVERIFIED
    again = services.add_coverage(
        patient=patient, scheme=shif, member_number="SHA-SYN000123", actor=clerk
    )
    assert again.pk == coverage.pk
    event = AuditEvent.objects.get(action="insurance.coverage.added")
    assert event.patient_id == patient.pk
    assert event.detail == {"scheme_code": "shif", "payer_code": "sha"}
    with connection.cursor() as cursor:
        cursor.execute("SELECT member_number FROM insurance_coverage")
        assert "SYN000123" not in cursor.fetchone()[0]


def test_coverage_validation_and_permissions(schemes, patient, staff):
    shif = schemes["sha/shif"]
    clerk = staff("receptionist")
    with pytest.raises(ValidationError):
        services.add_coverage(patient=patient, scheme=shif, member_number="12", actor=clerk)
    with pytest.raises(ValidationError):
        services.add_coverage(
            patient=patient,
            scheme=shif,
            member_number="SHA-1234",
            actor=clerk,
            valid_from=date(2026, 2, 1),
            valid_to=date(2026, 1, 1),
        )
    with pytest.raises(ValidationError, match="principal or dependant"):
        services.add_coverage(
            patient=patient, scheme=shif, member_number="SHA-1234", actor=clerk, relationship="x"
        )
    shif.payer.active = False
    shif.payer.save(update_fields=["active"])
    with pytest.raises(ValidationError, match="not active"):
        services.add_coverage(patient=patient, scheme=shif, member_number="SHA-1234", actor=clerk)
    shif.payer.active = True
    shif.payer.save(update_fields=["active"])
    with pytest.raises(PermissionDenied):
        services.add_coverage(
            patient=patient, scheme=shif, member_number="SHA-1234", actor=staff("lab_technologist")
        )


def test_current_cover_and_ending_it(schemes, patient, staff):
    clerk = staff("receptionist")
    today = timezone.localdate()
    coverage = services.add_coverage(
        patient=patient,
        scheme=schemes["syn-insurer-a/gold"],
        member_number="SYN-A-00001",
        actor=clerk,
        valid_to=today - timedelta(days=1),
    )
    assert not selectors.is_current(coverage)
    assert selectors.is_current(coverage, on=today - timedelta(days=2))
    with pytest.raises(ValidationError):
        services.end_coverage(coverage, actor=clerk, reason=" ")
    ended = services.end_coverage(coverage, actor=clerk, reason="Left the employer")
    assert not ended.active and ended.version == 2
    assert list(selectors.coverages_for(patient)) == []
    assert list(selectors.coverages_for(patient, include_ended=True)) == [ended]


def test_api_lists_schemes_and_masked_cover_with_an_audited_read(schemes, patient, reception):
    listed = reception.get(f"{URL}schemes/").json()
    assert {row["payer"]["code"] for row in listed} >= {"sha", "syn-insurer-a"}
    shif = schemes["sha/shif"]
    created = reception.post(
        f"{URL}coverages/",
        {"patient": str(patient.pk), "scheme": str(shif.pk), "member_number": "SHA-SYN-000777"},
        format="json",
    )
    assert created.status_code == 201, created.json()
    assert created.json()["member_number"].endswith("777")
    assert "SHA-SYN-000777" not in str(created.json())
    rows = reception.get(f"{URL}coverages/", {"patient": str(patient.pk)}).json()
    assert [r["scheme"]["code"] for r in rows] == ["shif"] and rows[0]["current"] is True
    assert AuditEvent.objects.filter(action="insurance.coverage.listed", patient_id=patient.pk)
    ended = reception.post(
        f"{URL}coverages/{created.json()['id']}/end/", {"reason": "Wrong scheme"}, format="json"
    )
    assert ended.status_code == 200 and ended.json()["active"] is False


def test_api_permissions(schemes, patient, api_as, facility):
    cashier = api_as("cashier", facility=facility)
    assert cashier.get(f"{URL}coverages/", {"patient": str(patient.pk)}).status_code == 200
    payload = {
        "patient": str(patient.pk),
        "scheme": str(schemes["sha/shif"].pk),
        "member_number": "SHA-1",
    }
    assert cashier.post(f"{URL}coverages/", payload, format="json").status_code == 403
    store = api_as("store_keeper", facility=facility)
    assert store.get(f"{URL}schemes/").status_code == 403
