"""Eligibility and payer consent through the API in fake mode (P3-SHA-01 acceptance 3,
P3-SHA-02; KE-SHA-01, KE-SHA-03, KE-SHA-04). SHA runs through the real HIE adapter against
the in-process fake HIE; SMART and Slade360 through their scripted fakes."""

import logging
import uuid

import pytest

from apps.audit.models import AuditEvent
from apps.core.models import OutboxEvent
from apps.insurance import consent
from apps.insurance.adapters import reset
from apps.insurance.models import Coverage, EligibilityCheck, PayerConsent
from apps.insurance.seed import payers_and_schemes
from apps.integrations.models import ExchangeLog
from apps.interop.hie import fake as hie_fake
from apps.patients import identifiers as ids
from apps.patients.models import PatientIdentifier
from apps.patients.tests.factories import PatientFactory

pytestmark = [pytest.mark.django_db, pytest.mark.sha]
URL = "/api/v1/insurance/"


@pytest.fixture(autouse=True)
def _fresh_gateways(settings):
    settings.SHA_MODE = settings.SMART_MODE = settings.SLADE360_MODE = "fake"
    reset()
    hie_fake._shared = None
    yield
    reset()


@pytest.fixture
def schemes():
    return payers_and_schemes()


@pytest.fixture
def reception(api_as, facility):
    return api_as("receptionist", facility=facility)


def key():
    return {"HTTP_IDEMPOTENCY_KEY": uuid.uuid4().hex}


def covered(facility, scheme, member, national_id=None):
    patient = PatientFactory.create(facility=facility)
    if national_id:
        PatientIdentifier.objects.create(
            patient=patient,
            facility_id=facility.pk,
            type="national_id",
            value=national_id,
            value_index=ids.index("national_id", national_id),
        )
    return Coverage.objects.create(
        facility_id=facility.pk,
        patient=patient,
        scheme=scheme,
        member_number=member,
        member_number_index=member,
    )


def check(client, coverage):
    return client.post(f"{URL}coverages/{coverage.pk}/eligibility/", **key())


@pytest.mark.req("KE-SHA-01")
def test_sha_eligibility_snapshot_verifies_cover_and_emits_event(reception, facility, schemes):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000011", "10000011")
    response = check(reception, coverage)
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "eligible" and body["verification"] == "verified"
    assert {s["name"] for s in body["schemes"]} == {"SHIF", "UHC"}
    assert "member_ref" not in body and "CR-SYN" not in response.content.decode()
    coverage.refresh_from_db()
    assert coverage.verification == "verified" and coverage.payer_member_ref == "CR-SYN-N10000011"
    snapshot = EligibilityCheck.objects.get()
    assert snapshot.gateway == "sha_hie" and snapshot.mode == "fake" and snapshot.request_hash
    assert OutboxEvent.objects.filter(topic="insurance.coverage.verified").get().payload == {
        "coverage_id": str(coverage.pk),
        "result": "eligible",
    }
    assert AuditEvent.objects.filter(action="insurance.eligibility.checked").exists()
    latest = reception.get(f"{URL}coverages/{coverage.pk}/eligibility/")
    assert latest.status_code == 200 and latest.json()["id"] == str(snapshot.pk)


@pytest.mark.parametrize(
    "national_id, status, verification",
    [
        ("10000097", "not_found", "failed"),
        ("10000096", "not_eligible", "failed"),
        ("10000098", "inactive", "failed"),
        ("99999999", "pending_verification", "unverified"),
        ("10000095", "pending_verification", "unverified"),
    ],
)
def test_sha_eligibility_outcomes(reception, facility, schemes, national_id, status, verification):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000012", national_id)
    body = check(reception, coverage).json()
    assert (body["status"], body["verification"]) == (status, verification)
    assert body["message"]
    if status == "inactive":
        assert "arrears" in body["message"]


def test_sha_eligibility_needs_an_identifier(reception, facility, schemes):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000013")
    response = check(reception, coverage)
    assert response.status_code == 400
    assert "national ID" in response.content.decode()


def test_eligibility_requires_idempotency_key_and_permission(api_as, facility, schemes, reception):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000014", "10000014")
    assert reception.post(f"{URL}coverages/{coverage.pk}/eligibility/").status_code == 428
    cashier = api_as("cashier", facility=facility)
    assert check(cashier, coverage).status_code == 403
    assert reception.get(f"{URL}coverages/{coverage.pk}/eligibility/").status_code == 404


def test_private_and_manual_eligibility(reception, facility, schemes):
    smart = covered(facility, schemes["syn-insurer-a/gold"], "SYN-A-00098")
    assert check(reception, smart).json()["status"] == "inactive"
    slade = covered(facility, schemes["syn-insurer-b/family"], "SYN-B-00010")
    assert check(reception, slade).json()["status"] == "eligible"
    manual = covered(facility, schemes["syn-employer/staff"], "SYN-E-00010")
    body = check(reception, manual).json()
    assert body["status"] == "pending_verification" and "confirm cover" in body["message"]


def test_payer_not_configured_is_503_naming_the_gap(reception, facility, schemes, settings):
    settings.SMART_MODE = "live"
    reset()
    coverage = covered(facility, schemes["syn-insurer-a/gold"], "SYN-A-00010")
    response = check(reception, coverage)
    assert response.status_code == 503 and "GAP-SMART-001" in response.content.decode()


@pytest.mark.req("KE-SHA-03")
def test_benefits_list_interventions_with_flags_and_unknown_tariffs(reception, facility, schemes):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000015", "10000015")
    check(reception, coverage)
    rows = reception.get(f"{URL}coverages/{coverage.pk}/benefits/").json()
    by_code = {r["code"]: r for r in rows}
    assert by_code["SYN-SHA-OP-002"]["needs_preauth"] is True
    assert by_code["SYN-SHA-OP-001"]["tariff"] == "1500.00"
    assert by_code["SYN-SHA-IP-001"]["tariff"] is None  # unknown per diem, not zero
    assert by_code["SYN-PHC-001"]["payment_mechanism"] == "CAPITATION"


def start(client, coverage, **extra):
    body = {
        "coverage": str(coverage.pk),
        "service_type": "outpatient",
        "codes": ["SYN-SHA-OP-001"],
        "method": "otp",
    }
    body.update(extra)
    return client.post(f"{URL}consents/", body, format="json", **key())


@pytest.mark.req("KE-SHA-04")
def test_sha_otp_consent_end_to_end(reception, facility, schemes, caplog):
    caplog.set_level(logging.DEBUG)
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000016", "10000016")
    check(reception, coverage)
    choose = start(reception, coverage)
    assert choose.status_code == 200 and choose.json()["status"] == "choose_contact"
    assert choose.json()["contacts"] == [
        {"contact_id": "1", "masked": "+254700***001", "confirmed": True}
    ]
    sent = start(reception, coverage, contact_id="1")
    assert sent.status_code == 201
    consent_id = sent.json()["consent"]["id"]
    url = f"{URL}consents/{consent_id}/complete/"
    wrong = reception.post(url, {"otp": "000000"}, format="json", **key())
    assert wrong.status_code == 400 and "not correct" in wrong.content.decode()
    done = reception.post(url, {"otp": "123456"}, format="json", **key())
    assert done.status_code == 200, done.content
    assert done.json()["status"] == "visit_open" and done.json()["has_token"] is True
    row = PayerConsent.objects.get(pk=consent_id)
    token = row.token_encrypted
    assert token.startswith("FAKEVC") and row.attempts == 1
    # The consent token and the OTP appear nowhere: not in responses, logs or exchange log.
    everything = done.content.decode() + caplog.text
    everything += " ".join(
        f"{r.request_body} {r.response_body} {r.request_headers}" for r in ExchangeLog.objects.all()
    )
    assert token not in everything and "123456" not in everything
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "select token_encrypted from insurance_payerconsent where id = %s", [consent_id]
        )
        assert token not in cursor.fetchone()[0]  # encrypted at rest


def test_expired_and_repeated_wrong_otps(reception, facility, schemes):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000017", "10000017")
    check(reception, coverage)
    consent_id = start(reception, coverage, contact_id="1").json()["consent"]["id"]
    url = f"{URL}consents/{consent_id}/complete/"
    expired = reception.post(url, {"otp": "111111"}, format="json", **key())
    assert expired.status_code == 400 and "expired" in expired.content.decode()
    assert PayerConsent.objects.get(pk=consent_id).status == "expired"
    consent_id = start(reception, coverage, contact_id="1").json()["consent"]["id"]
    url = f"{URL}consents/{consent_id}/complete/"
    for _ in range(consent.MAX_ATTEMPTS):
        reception.post(url, {"otp": "000000"}, format="json", **key())
    assert PayerConsent.objects.get(pk=consent_id).status == "rejected"


def test_member_without_a_phone_cannot_use_otp(reception, facility, schemes):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000018", "10000094")
    check(reception, coverage)
    response = start(reception, coverage)
    assert response.status_code == 400 and "fingerprints" in response.content.decode()


BIO = {
    "agent_id": "20000001",
    "device_os": "windows",
    "ekyc_provider_id": "Synthetic site",
    "work_station_id": "ws-syn-1",
}


def test_sha_biometric_consent_poll_and_visit(reception, facility, schemes):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000019", "10000019")
    check(reception, coverage)
    started = start(reception, coverage, method="biometric", biometric=BIO)
    assert started.status_code == 201
    body = started.json()
    assert body["status"] == "awaiting_biometric" and body["capture_url"].startswith(
        "https://hie.fake.invalid/"
    )
    consent_id = body["consent"]["id"]
    polled = reception.get(f"{URL}consents/{consent_id}/").json()
    assert polled["status"] == "authorized"
    done = reception.post(f"{URL}consents/{consent_id}/complete/", {}, format="json", **key())
    assert done.status_code == 200 and done.json()["status"] == "visit_open"


@pytest.mark.parametrize("national_id, fallback", [("10000093", False), ("10000092", True)])
def test_biometric_failures_and_otp_fallback(reception, facility, schemes, national_id, fallback):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000020", national_id)
    check(reception, coverage)
    consent_id = start(reception, coverage, method="biometric", biometric=BIO).json()["consent"][
        "id"
    ]
    polled = reception.get(f"{URL}consents/{consent_id}/").json()
    assert polled["status"] == "rejected" and polled["otp_fallback"] is fallback


def test_stuck_pending_authorisation_must_be_rejected_first(reception, facility, schemes):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000021", "10000091")
    check(reception, coverage)
    blocked = start(reception, coverage, contact_id="1")
    assert blocked.status_code == 409 and blocked.json()["code"] == "pending_authorisation"
    pending_url = f"{URL}coverages/{coverage.pk}/pending-authorisations/"
    assert reception.get(pending_url).json() == {"pending": 1}
    assert reception.post(f"{pending_url}reject/", **key()).status_code == 200
    assert reception.get(pending_url).json() == {"pending": 0}
    assert start(reception, coverage, contact_id="1").status_code == 201


def test_smart_member_code_consent(reception, facility, schemes):
    coverage = covered(facility, schemes["syn-insurer-a/gold"], "SYN-A-00011")
    started = start(reception, coverage, method="card_or_code", codes=["SYN-PVT-CONS"])
    assert started.status_code == 201 and started.json()["status"] == "awaiting_code"
    url = f"{URL}consents/{started.json()['consent']['id']}/complete/"
    assert reception.post(url, {"member_code": "0000"}, format="json", **key()).status_code == 400
    assert (
        reception.post(url, {"member_code": "1234"}, format="json", **key()).json()["status"]
        == "visit_open"
    )
    unsupported = start(reception, coverage, method="otp")
    assert unsupported.status_code == 400


def test_consent_can_be_cancelled_and_is_facility_scoped(reception, facility, schemes, api_as):
    coverage = covered(facility, schemes["sha/shif"], "SHA-SYN-000022", "10000022")
    check(reception, coverage)
    consent_id = start(reception, coverage, contact_id="1").json()["consent"]["id"]
    from apps.facilities.tests.factories import FacilityFactory

    elsewhere = api_as("receptionist", facility=FacilityFactory.create())
    assert elsewhere.get(f"{URL}consents/{consent_id}/").status_code in (403, 404)
    cancelled = reception.post(f"{URL}consents/{consent_id}/cancel/", **key())
    assert cancelled.json()["status"] == "cancelled"
    again = reception.post(
        f"{URL}consents/{consent_id}/complete/", {"otp": "123456"}, format="json", **key()
    )
    assert again.status_code == 400
