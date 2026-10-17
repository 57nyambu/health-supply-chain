"""The HIE transport (INSURANCE.md §3.1; P3-SHA-01 acceptance 1; KE-DHA-09)."""

import threading

import httpx
import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.integrations.models import ExchangeLog
from apps.interop.hie import client as hie
from apps.interop.hie.client import HieClient, HieConfig, TokenCache, config_from_settings, redact
from apps.interop.hie.errors import (
    HieAuthError,
    HieConfigurationError,
    HieForbidden,
    HieNotFound,
    HieOutcomeUnknown,
    HieRejected,
    HieUnavailable,
)
from apps.interop.hie.fake import FakeHie

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DHA-09")]


def make(fake=None, *, scope="facility", tokens=None, sleeps=None):
    fake = fake or FakeHie()
    config = HieConfig(
        "fake", hie.FAKE_BASE_URL, "test-client", "test-secret", "FID-SYN-000001", scope=scope
    )
    client = HieClient(
        config,
        transport=fake.transport(),
        tokens=tokens or TokenCache(),
        sleep=(sleeps.append if sleeps is not None else (lambda s: None)),
    )
    return client, fake


def eligibility(client):
    return client.get(
        "/patients/eligibility",
        params={"identification_number": "10000011", "identification_type": "National ID"},
        operation="eligibility",
    )


def test_token_is_fetched_once_and_reused():
    client, fake = make()
    eligibility(client)
    eligibility(client)
    assert [c for c in fake.calls if c[1] == "/tenants/token"] == [("POST", "/tenants/token")]
    assert client._tokens.fetches == 1


def test_concurrent_callers_share_a_single_refresh():
    tokens = TokenCache()
    gate = threading.Barrier(8)
    fetched = []

    def fetch():
        fetched.append(1)
        return "tok", 3600

    def worker():
        gate.wait()
        assert tokens.get(("u", "c"), fetch) == "tok"

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(fetched) == 1


def test_token_refreshes_at_eighty_percent_of_its_lifetime():
    now = [1000.0]
    tokens = TokenCache(clock=lambda: now[0])
    values = iter(["first", "second"])
    fetch = lambda: (next(values), 100)  # noqa: E731
    assert tokens.get(("u", "c"), fetch) == "first"
    now[0] += 79
    assert tokens.get(("u", "c"), fetch) == "first"
    now[0] += 2  # 81 % of the lifetime
    assert tokens.get(("u", "c"), fetch) == "second"


def test_a_401_refreshes_once_and_replays_once():
    client, fake = make()
    eligibility(client)
    fake.revoke_tokens()  # the HIE expired our token early
    assert eligibility(client)["memberCrNumber"].startswith("CR-SYN-")
    assert [c[1] for c in fake.calls].count("/tenants/token") == 2

    calls = []

    def always_401(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/tenants/token"):
            return httpx.Response(200, json={"access_token": f"t{len(calls)}", "expires_in": 600})
        return httpx.Response(401, json={"error": "unauthorized", "message": "Unauthorized"})

    other = HieClient(
        HieConfig("fake", hie.FAKE_BASE_URL, "c", "s"),
        transport=httpx.MockTransport(always_401),
        tokens=TokenCache(),
    )
    with pytest.raises(HieAuthError):
        eligibility(other)
    assert [p.rsplit("/", 1)[-1] for p in calls] == ["token", "eligibility", "token", "eligibility"]


def test_wrong_credentials_are_an_auth_error():
    fake = FakeHie()
    config = HieConfig("fake", hie.FAKE_BASE_URL, "test-client", "wrong", "FID-SYN-000001")
    client = HieClient(config, transport=fake.transport(), tokens=TokenCache())
    with pytest.raises(HieAuthError):
        eligibility(client)


def test_facility_headers_only_for_multi_facility_credentials():
    client, fake = make(scope="facility")
    eligibility(client)
    assert "x-facility-id" not in fake.headers_seen[-1]
    client, fake = make(scope="multi_facility")
    eligibility(client)
    assert fake.headers_seen[-1]["x-facility-id"] == "FID-SYN-000001"
    assert fake.headers_seen[-1]["x-facility-id-type"] == "fr-code"


def test_reads_are_retried_with_backoff_then_give_up():
    sleeps: list[float] = []
    client, fake = make(sleeps=sleeps)
    fake.fail_next["/patients/eligibility"] = "500"
    assert eligibility(client)["schemes"]
    assert len(sleeps) == 1
    with pytest.raises(HieUnavailable):
        client.get(
            "/patients/eligibility",
            params={"identification_number": "99999999", "identification_type": "National ID"},
            operation="eligibility",
        )
    assert len(sleeps) == 1 + hie.READ_ATTEMPTS - 1


def test_writes_are_never_retried_and_a_timeout_is_outcome_unknown():
    sleeps: list[float] = []
    client, fake = make(sleeps=sleeps)
    fake.fail_next["/claims/visit"] = "timeout"
    body = {
        "intervention_codes": ["SYN-SHA-OP-001"],
        "patient_id": "CR-SYN-N10000011",
        "service_type": "OUTPATIENT",
        "otp": "123456",
    }
    with pytest.raises(HieOutcomeUnknown):
        client.post("/claims/visit", json=body, operation="start_visit")
    assert [c for c in fake.calls if c[1] == "/claims/visit"] == [("POST", "/claims/visit")]
    assert sleeps == []
    fake.fail_next["/claims/visit"] = "500"
    with pytest.raises(HieOutcomeUnknown):
        client.post("/claims/visit", json=body, operation="start_visit")
    fake.fail_next["/claims/visit"] = "connect"  # never sent: plainly unavailable
    with pytest.raises(HieUnavailable):
        client.post("/claims/visit", json=body, operation="start_visit")


def test_status_codes_map_to_errors():
    client, _fake = make()
    with pytest.raises(HieNotFound):
        client.get(
            "/patients",
            params={"identification_number": "10000097", "identification_type": "National ID"},
            operation="find",
        )
    with pytest.raises(HieRejected) as caught:
        client.get("/patients", params={"identification_number": "1"}, operation="find")
    assert caught.value.payer_message.startswith("Bad Request")
    forbidden = httpx.MockTransport(
        lambda r: (
            httpx.Response(200, json={"access_token": "t", "expires_in": 60})
            if r.url.path.endswith("/token")
            else httpx.Response(
                403, json={"error": "forbidden", "message": "Forbidden - Tenant context required"}
            )
        )
    )
    other = HieClient(
        HieConfig("fake", hie.FAKE_BASE_URL, "c", "s"), transport=forbidden, tokens=TokenCache()
    )
    with pytest.raises(HieForbidden):
        other.get("/patients", params={}, operation="find")


def test_exchange_log_never_holds_secrets_or_identifiers():
    client, _fake = make()
    client.post(
        "/claims/visit",
        json={
            "intervention_codes": ["SYN-SHA-OP-001"],
            "patient_id": "CR-SYN-N10000011",
            "service_type": "OUTPATIENT",
            "otp": "123456",
        },
        operation="start_visit",
    )
    eligibility(client)
    rows = ExchangeLog.objects.all()
    stored = " ".join(f"{r.request_headers} {r.request_body} {r.response_body}" for r in rows)
    assert "123456" not in stored  # the OTP
    assert "FAKEVC" not in stored  # the consent token (authorization_code)
    assert "test-secret" not in stored and "fakehie." not in stored  # credentials, bearer
    assert "10000011" not in stored.replace("CR-SYN-N10000011", "")  # the national ID
    assert {r.integration for r in rows} >= {"hie", "hie.auth"}


def test_redact_walks_nested_payloads():
    assert redact({"a": [{"otp": "1"}], "Phone": "+2547", "x-facility-id": "F"}) == {
        "a": [{"otp": "[redacted]"}],
        "Phone": "[redacted]",
        "x-facility-id": "F",
    }


def test_sandbox_and_live_refuse_without_credentials(settings):
    settings.SHA_MODE = "sandbox"
    settings.SHA_CLIENT_ID = ""
    with pytest.raises(HieConfigurationError, match=r"SHA_CLIENT_ID.*GAP-HIE-001"):
        config_from_settings()
    settings.SHA_MODE = "nonsense"
    with pytest.raises(HieConfigurationError):
        config_from_settings()
    settings.SHA_MODE = "live"
    settings.SHA_BASE_URL = "https://hie.example.test/api/v1"
    settings.SHA_CLIENT_ID = "id"
    settings.SHA_CLIENT_SECRET = "secret"
    settings.SHA_FACILITY_ID = "FID-1"
    config = config_from_settings()
    assert config.mode == "live" and "secret" not in repr(config)


def test_registry_factories_build_the_hie_adapters_in_sandbox(settings):
    from apps.accounts.adapters.hwr import get_registry as hwr
    from apps.accounts.adapters.hwr.hie import HieHealthWorkerRegistry
    from apps.patients.adapters.client_registry import get_registry as cr
    from apps.patients.adapters.client_registry.hie import HieClientRegistry

    settings.CLIENT_REGISTRY_MODE = settings.HWR_MODE = "sandbox"
    with pytest.raises(ImproperlyConfigured, match="GAP-CR-001"):
        cr()
    settings.SHA_BASE_URL = hie.UAT_BASE_URL
    settings.SHA_CLIENT_ID, settings.SHA_CLIENT_SECRET, settings.SHA_FACILITY_ID = (
        "id",
        "s",
        "FID-1",
    )
    assert isinstance(cr(), HieClientRegistry)
    assert isinstance(hwr(), HieHealthWorkerRegistry)
