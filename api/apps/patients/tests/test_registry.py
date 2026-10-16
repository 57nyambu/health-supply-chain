import threading
from datetime import date
from typing import Any

import pytest
from django.db import connection, transaction
from django.utils import timezone

from apps.access.models import ApprovalRequest
from apps.audit.models import AuditEvent
from apps.core.sequences import next_value
from apps.facilities.tests.factories import FacilityFactory
from apps.patients import services
from apps.patients.models import Patient, PatientIdentifier, PatientMerge

pytestmark = pytest.mark.django_db
URL = "/api/v1/patients/"
YY = f"{timezone.localdate().year % 100:02d}"

AMINA: dict[str, Any] = {
    "given_name": "Amina",
    "family_name": "Otieno",
    "sex": "female",
    "date_of_birth": "1990-04-12",
    "identifiers": [
        {"type": "national_id", "value": "00123456"},
        {"type": "sha_number", "value": "SHA-000-111"},
    ],
    "contacts": [{"kind": "phone", "value": "0700 000 111", "is_primary": True}],
    "next_of_kin": [{"name": "Baraka Otieno", "relationship": "brother", "phone": "0700000222"}],
    "privacy_notice": {"version": "2026-10", "method": "verbal"},
}


@pytest.fixture
def reception(api_as, facility):
    return api_as("receptionist", facility=facility)


def register(client, **overrides):
    return client.post(URL, {**AMINA, **overrides}, format="json")


@pytest.mark.req("KE-DHA-04")
def test_registration_with_identifiers_contacts_and_next_of_kin(reception, facility):
    response = register(reception)
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["mrn"] == f"{facility.mfl_code}-{YY}-000001"
    assert {i["type"] for i in body["identifiers"]} == {"national_id", "sha_number"}
    assert body["contacts"][0]["value"] == "+254700000111"  # E.164
    assert body["next_of_kin"][0]["relationship"] == "brother"
    created = AuditEvent.objects.get(action="patients.patient.created")
    assert created.patient_id is not None and "Amina" not in str(created.detail)


def test_mrn_is_gap_free_per_facility(reception, facility, api_as):
    first = register(reception).json()["mrn"]
    second = register(
        reception,
        given_name="Zawadi",
        family_name="Mwangi",
        date_of_birth="2001-01-01",
        identifiers=[],
        contacts=[],
        next_of_kin=[],
    ).json()["mrn"]
    assert (first[-6:], second[-6:]) == ("000001", "000002")
    other = FacilityFactory.create()
    elsewhere = register(api_as("receptionist", facility=other)).json()["mrn"]
    assert elsewhere.endswith("000001")


def test_a_rolled_back_registration_releases_its_number(facility):
    with pytest.raises(RuntimeError), transaction.atomic():
        next_value(facility_id=facility.pk, name="mrn", year=2026)
        raise RuntimeError("registration failed")
    with transaction.atomic():
        assert next_value(facility_id=facility.pk, name="mrn", year=2026) == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_numbering_has_no_gaps_or_repeats(facility):
    taken = []

    def worker():
        try:
            for _ in range(5):
                with transaction.atomic():
                    taken.append(next_value(facility_id=facility.pk, name="race", year=2026))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(taken) == list(range(1, 21))
    with pytest.raises(RuntimeError, match="inside the transaction"):
        next_value(facility_id=facility.pk, name="race", year=2026)


@pytest.mark.parametrize(
    ("identifier", "field"),
    [
        ({"type": "national_id", "value": "12AB"}, "value"),
        ({"type": "passport", "value": "!!"}, "value"),
        ({"type": "temporary", "value": "ER-2026-0001"}, "identifiers"),
        ({"type": "fingerprint", "value": "x"}, "identifiers"),
    ],
)
def test_identifiers_are_validated_by_type(reception, identifier, field):
    response = register(reception, identifiers=[identifier])
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == field
    assert identifier["value"] not in response.content.decode()


@pytest.mark.req("KE-DPA-06")
def test_no_plaintext_identifiers_contacts_or_kin_in_the_database(reception):
    register(reception)
    with connection.cursor() as cursor:
        cursor.execute("SELECT value, value_index FROM patients_patientidentifier")
        rows = cursor.fetchall()
        cursor.execute("SELECT value FROM patients_patientcontact")
        rows += cursor.fetchall()
        cursor.execute("SELECT name, phone FROM patients_nextofkin")
        rows += cursor.fetchall()
    dumped = " ".join(str(column) for row in rows for column in row)
    for secret in ("00123456", "SHA-000-111", "SHA000111", "700000111", "Baraka", "700000222"):
        assert secret not in dumped
    assert all(str(row[0]).startswith("v1.") for row in rows)


def test_search_by_identifier_phone_and_fuzzy_name(reception):
    patient_id = register(reception).json()["id"]
    by_id = reception.post(f"{URL}search/", {"q": "00123456"}, format="json").json()["results"]
    assert (
        by_id[0]["id"] == patient_id
        and by_id[0]["reasons"] == ["identifier"]
        and by_id[0]["score"] == 100
    )
    assert by_id[0]["identifiers"][0]["value"].endswith("456") and "00123456" not in str(by_id[0])
    by_phone = reception.post(f"{URL}search/", {"q": "+254 700 000111"}, format="json").json()[
        "results"
    ]
    assert by_phone[0]["reasons"] == ["phone"]
    fuzzy = reception.post(
        f"{URL}search/",
        {"q": "amina otiano", "date_of_birth": "1990-04-12", "sex": "female"},
        format="json",
    )
    best = fuzzy.json()["results"][0]
    assert best["id"] == patient_id and {"name", "date_of_birth", "sex"} <= set(best["reasons"])
    assert reception.post(f"{URL}search/", {"q": "zz"}, format="json").status_code == 400


@pytest.mark.req("KE-DPA-06")
def test_search_terms_never_travel_in_the_url(reception):
    """Names, IDs and phones in a query string would land in proxy access logs (ADR-023)."""
    refused = (403, 405)  # default-deny policy answers before method-not-allowed
    assert reception.get(f"{URL}search/", {"q": "Otieno"}).status_code in refused
    registry = reception.get(
        f"{URL}registry-search/", {"type": "national_id", "number": "10000001"}
    )
    assert registry.status_code in refused
    assert not AuditEvent.objects.filter(action__endswith=".searched").exists()


@pytest.mark.req("KE-DPA-06")
def test_searches_are_audited_with_an_hmac_of_the_term(reception):
    reception.post(f"{URL}search/", {"q": "Otieno"}, format="json")
    event = AuditEvent.objects.get(action="patients.patient.searched")
    assert len(event.detail["lookup_hmac"]) == 64
    assert "Otieno" not in str(event.detail)


def test_likely_duplicates_need_an_override_reason(reception):
    register(reception)
    again = {**AMINA, "identifiers": [], "contacts": [], "next_of_kin": [], "given_name": "Aminah"}
    response = reception.post(URL, again, format="json")
    assert response.status_code == 409
    assert response.json()["code"] == "likely_duplicate"
    assert response.json()["candidates"][0]["score"] > 60
    forced = reception.post(
        URL, {**again, "override_reason": "Different person, twin sister"}, format="json"
    )
    assert forced.status_code == 201
    assert AuditEvent.objects.filter(action="patients.duplicate.overridden").exists()


def test_the_same_identifier_cannot_be_registered_twice(reception):
    register(reception)
    response = register(
        reception,
        given_name="Other",
        family_name="Person",
        date_of_birth="1970-01-01",
        contacts=[],
        override_reason="x",
    )
    assert response.status_code == 400


def test_phone_match_is_a_likely_duplicate(reception):
    register(reception)
    response = register(
        reception,
        given_name="Juma",
        family_name="Kiprop",
        sex="male",
        date_of_birth="1980-02-02",
        identifiers=[],
        next_of_kin=[],
    )
    assert response.status_code == 409


def test_estimated_date_of_birth_from_age(reception):
    response = register(
        reception,
        given_name="Neema",
        family_name="Wanjiru",
        date_of_birth=None,
        age_years=3,
        age_months=6,
        identifiers=[],
        contacts=[],
        next_of_kin=[],
    )
    body = response.json()
    assert body["dob_estimated"] is True and body["age"] == "3y"
    assert services.estimate_dob(0, 7, today=date(2026, 10, 16)) == date(2026, 3, 16)


def test_future_dates_and_impossible_ages_are_refused(reception):
    assert (
        register(reception, date_of_birth="2999-01-01", identifiers=[], contacts=[]).status_code
        == 400
    )
    assert (
        register(
            reception, date_of_birth=None, age_years=200, identifiers=[], contacts=[]
        ).status_code
        == 400
    )


def test_reading_a_record_is_an_audited_chart_open(reception):
    patient_id = register(reception).json()["id"]
    body = reception.get(f"{URL}{patient_id}/", {"purpose": "registration"}).json()
    assert body["identifiers"][0]["value"] in ("00123456", "SHA-000-111")
    event = AuditEvent.objects.get(action="patients.chart.opened")
    assert (str(event.patient_id), event.purpose) == (patient_id, "registration")


def test_updates_use_optimistic_concurrency(reception):
    created = register(reception).json()
    ok = reception.patch(
        f"{URL}{created['id']}/", {"version": 1, "middle_name": "Achieng"}, format="json"
    )
    assert ok.status_code == 200 and ok.json()["version"] == 2
    stale = reception.patch(
        f"{URL}{created['id']}/", {"version": 1, "middle_name": "Other"}, format="json"
    )
    assert stale.status_code == 409 and stale.json()["code"] == "conflict"
    assert AuditEvent.objects.get(action="patients.patient.updated").detail == {
        "fields": ["middle_name"]
    }


def test_identifiers_contacts_and_kin_can_be_added(reception):
    patient_id = register(reception, identifiers=[], contacts=[], next_of_kin=[]).json()["id"]
    assert (
        reception.post(
            f"{URL}{patient_id}/identifiers/",
            {"type": "passport", "value": "ak1234567"},
            format="json",
        ).json()["value"]
        == "AK1234567"
    )
    assert (
        reception.post(
            f"{URL}{patient_id}/contacts/",
            {"kind": "email", "value": "Amina@Example.test"},
            format="json",
        ).json()["value"]
        == "amina@example.test"
    )
    assert (
        reception.post(
            f"{URL}{patient_id}/contacts/", {"kind": "phone", "value": "12"}, format="json"
        ).status_code
        == 400
    )
    kin = reception.post(
        f"{URL}{patient_id}/next-of-kin/",
        {"name": "Mama Amina", "relationship": "mother"},
        format="json",
    )
    assert kin.status_code == 201


def test_other_facilities_cannot_see_the_record(reception, api_as):
    patient_id = register(reception).json()["id"]
    elsewhere = api_as("receptionist", facility=FacilityFactory.create())
    assert elsewhere.get(f"{URL}{patient_id}/").status_code == 404
    assert elsewhere.post(f"{URL}search/", {"q": "00123456"}, format="json").json()["results"] == []


def test_roles_without_registry_rights_are_denied(api_as, facility):
    cashier = api_as("store_keeper", facility=facility)
    assert cashier.post(f"{URL}search/", {"q": "Otieno"}, format="json").status_code == 403
    assert cashier.post(URL, AMINA, format="json").status_code == 403


# --- unidentified patients and merges ---------------------------------------------------------------


def test_unidentified_emergency_registration(reception):
    response = reception.post(
        f"{URL}unidentified/", {"sex": "male", "approx_age_years": 30}, format="json"
    )
    body = response.json()
    assert response.status_code == 201
    temporary = body["identifiers"][0]["value"]
    assert temporary.startswith(f"ER-{timezone.localdate().year}-0001")
    assert body["display_name"] == f"Unknown male, approx. 30y, {temporary}"
    assert body["is_unidentified"] and body["dob_estimated"]


def test_merge_into_the_real_record_is_maker_checker_audited_and_reversible(
    api_as, facility, make_user, grant
):
    reception = api_as("receptionist", facility=facility)
    unknown = reception.post(f"{URL}unidentified/", {"sex": "female"}, format="json").json()
    real = register(reception).json()
    hrio = api_as("hrio", facility=facility)
    requested = hrio.post(
        f"{URL}{real['id']}/merge/",
        {"duplicate": unknown["id"], "reason": "Identified by family"},
        format="json",
    )
    assert requested.status_code == 201
    approval_id = requested.json()["approval"]
    assert (
        hrio.post(f"/api/v1/access/approvals/{approval_id}/approve/").status_code == 403
    )  # own request
    supervisor = api_as("hrio", "hrio_supervisor", facility=facility)
    inbox = supervisor.get("/api/v1/access/approvals/", {"status": "pending"}).json()["results"]
    assert [row["id"] for row in inbox] == [approval_id]
    assert (
        supervisor.post(f"/api/v1/access/approvals/{approval_id}/approve/").json()["status"]
        == "approved"
    )

    merged = Patient.objects.get(pk=unknown["id"])
    assert merged.status == "merged" and str(merged.merged_into_id) == real["id"]
    assert not PatientIdentifier.objects.filter(patient_id=unknown["id"], active=True).exists()
    merge = PatientMerge.objects.get()
    reversal = hrio.post(
        f"{URL}merges/{merge.pk}/unmerge/", {"reason": "Wrong patient"}, format="json"
    )
    reversal_id = reversal.json()["reversal_approval"]
    supervisor.post(f"/api/v1/access/approvals/{reversal_id}/approve/")
    restored = Patient.objects.get(pk=unknown["id"])
    assert restored.status == "active" and restored.merged_into_id is None
    assert PatientIdentifier.objects.filter(
        patient=restored, type="temporary", active=True
    ).exists()
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "patients.merge.requested",
        "patients.merge.completed",
        "patients.merge.reversal_requested",
        "patients.merge.reversed",
        "access.approval.approved",
    } <= actions


def test_merge_moves_identifiers_and_contacts(api_as, facility):
    reception = api_as("receptionist", facility=facility)
    survivor = register(reception, identifiers=[], contacts=[], next_of_kin=[]).json()
    duplicate = reception.post(
        URL,
        {
            **AMINA,
            "given_name": "Amina",
            "family_name": "Otieno",
            "override_reason": "pending check",
        },
        format="json",
    ).json()
    hrio = api_as("hrio", facility=facility)
    approval = hrio.post(
        f"{URL}{survivor['id']}/merge/",
        {"duplicate": duplicate["id"], "reason": "Same person"},
        format="json",
    ).json()["approval"]
    api_as("hrio_supervisor", facility=facility).post(
        f"/api/v1/access/approvals/{approval}/approve/"
    )
    kept = reception.get(f"{URL}{survivor['id']}/").json()
    assert {i["type"] for i in kept["identifiers"]} == {"national_id", "sha_number"}
    assert len(kept["contacts"]) == 1 and len(kept["next_of_kin"]) == 1
    assert ApprovalRequest.objects.get(pk=approval).status == "approved"


def test_merge_validation(api_as, facility):
    reception = api_as("receptionist", facility=facility)
    one = register(reception).json()
    hrio = api_as("hrio", facility=facility)
    assert (
        hrio.post(
            f"{URL}{one['id']}/merge/", {"duplicate": one["id"], "reason": "x"}, format="json"
        ).status_code
        == 400
    )
    other = api_as("receptionist", facility=FacilityFactory.create())
    stranger = register(other).json()
    assert (
        hrio.post(
            f"{URL}{one['id']}/merge/", {"duplicate": stranger["id"], "reason": "x"}, format="json"
        ).status_code
        == 400
    )
