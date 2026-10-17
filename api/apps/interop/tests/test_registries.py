"""HIE registries through the real adapters against the fake HIE (P3-SHA-01 acceptance 2;
KE-DHA-04): Client Registry (reception), Health Worker Registry (licences), Facility
Registry (facility set-up)."""

from datetime import date

import httpx
import pytest
from django.core.exceptions import ValidationError

from apps.accounts.adapters.hwr.hie import HieHealthWorkerRegistry
from apps.interop.hie.client import FAKE_BASE_URL, HieClient, HieConfig, TokenCache
from apps.interop.hie.errors import HieUnavailable
from apps.interop.hie.fake import FakeHie
from apps.interop.registries import facility_record
from apps.patients.adapters.client_registry import RegistryUnavailable
from apps.patients.adapters.client_registry.hie import HieClientRegistry

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DHA-04")]


@pytest.fixture
def fake():
    return FakeHie()


@pytest.fixture
def hie(fake):
    return HieClient(
        HieConfig("fake", FAKE_BASE_URL, "c", "s", "FID-SYN-000001"),
        transport=fake.transport(),
        tokens=TokenCache(),
        sleep=lambda s: None,
    )


def test_client_registry_returns_the_cr_id_and_demographics(hie):
    registry = HieClientRegistry(hie)
    person = registry.find("national_id", "10000001")
    assert person is not None
    assert person.cr_id == "CR-SYN-000001"
    assert (person.given_name, person.family_name, person.sex) == (
        "Achieng",
        "Syntheticus",
        "female",
    )
    assert person.date_of_birth == date(1988, 3, 14)
    assert ("national_id", "10000001") in person.identifiers
    generated = registry.find("national_id", "190000123")
    assert generated is not None
    assert generated.cr_id == "CR-SYN-G190000123"


def test_client_registry_not_found_and_outages(hie):
    registry = HieClientRegistry(hie)
    assert registry.find("national_id", "10000097") is None
    with pytest.raises(RegistryUnavailable):
        registry.find("national_id", "99999999")
    with pytest.raises(RegistryUnavailable):
        registry.find("national_id", "10000095")  # timeout
    with pytest.raises(RegistryUnavailable):
        registry.find("maisha_namba", "500000000002")  # no HIE type yet (GAP-HIE-004)


def test_reception_lookup_works_through_the_hie_adapter(
    settings, hie, facility, make_user, grant, monkeypatch
):
    from apps.patients import registry as reception

    clerk = make_user()
    grant(clerk, "receptionist", facility)
    monkeypatch.setattr(reception, "get_registry", lambda: HieClientRegistry(hie))
    found = reception.lookup(
        actor=clerk, facility_id=facility.pk, identifier_type="national_id", number="10000001"
    )
    assert found.status == "found" and found.person is not None
    assert found.person.cr_id == "CR-SYN-000001"
    down = reception.lookup(
        actor=clerk, facility_id=facility.pk, identifier_type="national_id", number="99999999"
    )
    assert down.status == "unavailable"


def test_health_worker_registry_gives_puid_licence_and_activity(hie):
    registry = HieHealthWorkerRegistry(hie)
    active = registry.lookup("KMPDC", "test-1001")
    assert active is not None and active.puid.startswith("PUID-") and active.active
    assert active.licence_valid_to == date(date.today().year + 1, 12, 31)
    expired = registry.lookup("NCK", "EXPIRED-7")
    assert expired is not None and expired.licence_valid_to == date(date.today().year - 1, 12, 31)
    suspended = registry.lookup("PPB", "SUSP-1")
    assert suspended is not None and suspended.active is False
    assert registry.lookup("KMPDC", "12345") is None
    assert registry.lookup("UNKNOWN", "TEST-1") is None


def test_health_worker_registry_outage_is_a_message_not_a_crash(hie, fake):
    def down(request):
        if request.url.path.endswith("/professionals"):
            raise httpx.ConnectError("down", request=request)
        return fake.handle(request)

    client = HieClient(
        hie.config, transport=httpx.MockTransport(down), tokens=TokenCache(), sleep=lambda s: None
    )
    with pytest.raises(ValidationError, match="not answering"):
        HieHealthWorkerRegistry(client).lookup("KMPDC", "TEST-1")


def test_facility_registry_record(hie):
    record = facility_record("FID-SYN-000001", client=hie)
    assert record is not None
    assert record.fid == "FID-SYN-000001" and record.keph_level == "Level 4"
    assert record.sha_active and "SYN-SB-OP" in record.contracted_services
    suspended = facility_record("FID-SYN-000009", client=hie)
    assert suspended is not None
    assert suspended.sha_active is False
    assert facility_record("FID-47-000000", client=hie) is None
    with pytest.raises(ValueError):
        facility_record("X", "nonsense", client=hie)


def test_facility_registry_outage_raises(hie, fake):
    fake.fail_next["/facilities/search"] = "500"
    assert facility_record("FID-SYN-000001", client=hie)  # read retried once
    broken = HieClient(
        hie.config,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(503) if "facilities" in r.url.path else fake.handle(r)
        ),
        tokens=TokenCache(),
        sleep=lambda s: None,
    )
    with pytest.raises(HieUnavailable):
        facility_record("FID-SYN-000001", client=broken)
