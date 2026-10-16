from datetime import date

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import connection

from apps.audit.models import AuditEvent
from apps.integrations.exchange import REDACTED, exchange, redact_headers
from apps.integrations.models import ExchangeLog
from apps.patients import identifiers as ids
from apps.patients.adapters.client_registry import (
    SEARCHABLE_TYPES,
    RegistryPerson,
    RegistryUnavailable,
    get_registry,
)
from apps.patients.adapters.client_registry.fake import RECORDS, FakeClientRegistry, generated
from apps.patients.models import Patient, PatientIdentifier

from .test_privacy import NOTICE
from .test_registry import AMINA

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DHA-04")]
URL = "/api/v1/patients/"
KNOWN = ("national_id", "10000001")
OUTAGE = ("national_id", "99999999")


# --- contract: every ClientRegistry implementation must pass these ------------------------------

REGISTRIES = [FakeClientRegistry()]


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: r.mode)
def test_contract_known_identifier_returns_cr_id_and_demographics(registry):
    person = registry.find(*KNOWN)
    assert isinstance(person, RegistryPerson)
    ids.validate(PatientIdentifier.Type.CLIENT_REGISTRY, person.cr_id)
    assert KNOWN in person.identifiers
    assert person.given_name and person.family_name
    assert person.sex in Patient.Sex.values
    assert person.date_of_birth is None or isinstance(person.date_of_birth, date)
    assert registry.find(KNOWN[0], " 10000001 ") == person  # deterministic, normalised


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: r.mode)
def test_contract_unknown_identifiers_return_none(registry):
    assert registry.find("national_id", "12345670") is None
    assert registry.find("passport", "AB1234567") is None  # not a registry search type


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: r.mode)
def test_contract_outage_raises_registry_unavailable(registry):
    with pytest.raises(RegistryUnavailable):
        registry.find(*OUTAGE)


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: r.mode)
@pytest.mark.req("KE-DPA-06")
def test_contract_every_call_is_logged_with_encrypted_bodies(registry):
    registry.find(*KNOWN)
    registry.find("national_id", "12345670")
    with pytest.raises(RegistryUnavailable):
        registry.find(*OUTAGE)
    outcomes = list(ExchangeLog.objects.order_by("started_at").values_list("outcome", flat=True))
    assert outcomes == ["success", "not_found", "unavailable"]
    log = ExchangeLog.objects.get(outcome="success")
    assert (log.integration, log.operation, log.mode, log.http_status) == (
        "hie.client_registry",
        "find",
        registry.mode,
        200,
    )
    assert log.provider_trace_id and len(log.correlation_id) == 32
    assert "10000001" in log.request_body and "CR-SYN-000001" in log.response_body
    with connection.cursor() as cursor:
        cursor.execute("SELECT request_body, response_body FROM integrations_exchangelog")
        raw = " ".join(value for row in cursor.fetchall() for value in row)
    assert "10000001" not in raw and "Syntheticus" not in raw


def test_fake_generated_range_is_deterministic_synthetic_and_valid():
    registry = FakeClientRegistry()
    person = registry.find("national_id", "191234567")
    assert person is not None and person == registry.find("national_id", "191234567")
    assert person == generated("191234567") and person.cr_id == "CR-SYN-G191234567"
    assert person.identifiers == (("national_id", "191234567"),) and not person.phone
    ids.validate("cr_id", person.cr_id)
    assert person.sex in Patient.Sex.values and person.date_of_birth is not None
    other = registry.find("national_id", "191234568")
    assert other is not None and other.family_name != person.family_name
    assert registry.find("national_id", "19123456") is None  # eight digits: not the range


def test_fake_records_are_synthetic_and_valid():
    for (type_, number), person in RECORDS.items():
        assert (type_, number) in person.identifiers
        assert type_ in SEARCHABLE_TYPES
        for identifier_type, value in person.identifiers:
            ids.validate(identifier_type, value)
        assert person.cr_id.startswith("CR-SYN-")


def test_only_the_fake_exists_until_phase_3(settings):
    assert isinstance(get_registry(), FakeClientRegistry)
    settings.CLIENT_REGISTRY_MODE = "live"
    with pytest.raises(ImproperlyConfigured, match="GAP-CR-001"):
        get_registry()


def test_exchange_headers_are_redacted_and_errors_recorded():
    assert redact_headers(
        {"Authorization": "Bearer x", "X-Api-Key": "k", "Accept": "application/json"}
    ) == {
        "Authorization": REDACTED,
        "X-Api-Key": REDACTED,
        "Accept": "application/json",
    }
    with (
        pytest.raises(RuntimeError),
        exchange("test.system", "boom", mode="fake", headers={"Cookie": "c"}),
    ):
        raise RuntimeError("down")
    log = ExchangeLog.objects.get(integration="test.system")
    assert log.outcome == "error" and log.request_headers == {"Cookie": REDACTED}


# --- reception: local first, then the registry ----------------------------------------------------


@pytest.fixture
def reception(api_as, facility):
    return api_as("receptionist", facility=facility)


def search(client, type_, number):
    return client.post(f"{URL}registry-search/", {"type": type_, "number": number}, format="json")


def test_search_shows_local_results_first_then_the_registry_match(reception):
    local = reception.post(
        URL,
        {
            **AMINA,
            "identifiers": [{"type": "national_id", "value": "10000001"}],
            "contacts": [],
            "next_of_kin": [],
        },
        format="json",
    ).json()
    body = search(reception, *KNOWN).json()
    assert [row["id"] for row in body["local"]] == [local["id"]]
    assert body["registry"]["status"] == "found"
    person = body["registry"]["person"]
    assert (person["cr_id"], person["family_name"]) == ("CR-SYN-000001", "Syntheticus")
    assert "10000001" not in str(person["identifiers"]) and person["phone"].endswith("001")
    assert body["registry"]["registered_patient"] is None  # same ID, but no CR ID linked yet
    event = AuditEvent.objects.get(action="patients.registry.searched")
    assert event.detail["outcome"] == "found" and "10000001" not in str(event.detail)


def test_registry_outage_never_blocks_reception(reception):
    local = reception.post(
        URL,
        {
            **AMINA,
            "identifiers": [{"type": "national_id", "value": "99999999"}],
            "contacts": [],
            "next_of_kin": [],
        },
        format="json",
    ).json()
    response = search(reception, *OUTAGE)
    assert response.status_code == 200
    assert response.json()["registry"] == {
        "status": "unavailable",
        "person": None,
        "registered_patient": None,
    }
    assert [row["id"] for row in response.json()["local"]] == [local["id"]]


def test_not_found_and_invalid_searches(reception):
    assert search(reception, "national_id", "12345670").json()["registry"]["status"] == "not_found"
    assert search(reception, "passport", "AB1234567").status_code == 400
    assert search(reception, "national_id", "12AB").status_code == 400


def test_import_creates_a_local_record_with_the_verified_cr_id(reception):
    created = reception.post(
        f"{URL}registry-import/",
        {"type": "national_id", "number": "10000001", "privacy_notice": NOTICE},
        format="json",
    )
    assert created.status_code == 201, created.json()
    body = created.json()
    assert (body["given_name"], body["family_name"], body["date_of_birth"]) == (
        "Achieng",
        "Syntheticus",
        "1988-03-14",
    )
    assert {i["type"] for i in body["identifiers"]} == {"cr_id", "national_id", "sha_number"}
    assert body["contacts"][0]["value"] == "+254700100001"
    assert body["consents"][0]["kind"] == "privacy_notice"
    cr = PatientIdentifier.objects.get(type="cr_id", patient_id=body["id"])
    assert cr.source == "client_registry" and cr.verified_at is not None
    assert AuditEvent.objects.get(action="patients.registry.imported").detail == {"mode": "fake"}
    again = search(reception, *KNOWN).json()
    assert again["registry"]["registered_patient"] == body["id"]
    assert [row["id"] for row in again["local"]] == [body["id"]]
    duplicate = reception.post(
        f"{URL}registry-import/",
        {"type": "national_id", "number": "10000001", "privacy_notice": NOTICE},
        format="json",
    )
    assert duplicate.status_code == 400


def test_import_without_a_date_of_birth_or_phone(reception):
    body = reception.post(
        f"{URL}registry-import/",
        {"type": "refugee_id", "number": "rf-300004", "privacy_notice": NOTICE},
        format="json",
    ).json()
    assert body["date_of_birth"] is None and body["contacts"] == []


def test_import_errors(reception):
    payload = {"type": "national_id", "privacy_notice": NOTICE}
    missing = reception.post(
        f"{URL}registry-import/", {**payload, "number": "12345670"}, format="json"
    )
    assert missing.status_code == 400
    down = reception.post(
        f"{URL}registry-import/", {**payload, "number": "99999999"}, format="json"
    )
    assert down.status_code == 503 and down.json()["code"] == "registry_unavailable"
    no_notice = reception.post(
        f"{URL}registry-import/", {"type": "national_id", "number": "10000002"}, format="json"
    )
    assert no_notice.status_code == 400
    assert not Patient.objects.exists()


def test_registry_needs_its_permissions(api_as, facility, make_user):
    store = api_as("store_keeper", facility=facility)
    assert search(store, *KNOWN).status_code == 403
    assert (
        store.post(
            f"{URL}registry-import/",
            {"type": "national_id", "number": "10000001", "privacy_notice": NOTICE},
            format="json",
        ).status_code
        == 403
    )
    from django.core.exceptions import PermissionDenied

    from apps.patients import registry

    with pytest.raises(PermissionDenied):
        registry.lookup(
            actor=make_user(),
            facility_id=facility.pk,
            identifier_type="national_id",
            number="10000001",
        )
