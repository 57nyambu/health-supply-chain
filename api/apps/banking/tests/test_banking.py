"""Bank and card vendor parts in fake mode (P3-BNK-01, P3-BNK-02, P3-CRD-01 vendor parts;
PAYMENTS.md §4-6): signing with documented test strings, IPN verification vectors (valid,
bad signature or credentials, duplicate, amount mismatch, unknown reference), status
queries before anything is confirmed, Pesapal hosted checkout."""

import json
from decimal import Decimal

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from apps.banking import fakes, notifications, providers, signing
from apps.banking.models import BankNotification
from apps.core.models import OutboxEvent
from apps.integrations import webhooks
from apps.integrations.models import ExchangeLog, WebhookInbox

pytestmark = pytest.mark.django_db
HOOK = "/api/v1/hooks"


@pytest.fixture(autouse=True)
def _fake_banks(settings):
    settings.JENGA_MODE = settings.BUNI_MODE = settings.PESAPAL_MODE = "fake"
    settings.JENGA_IPN_TOKEN, settings.BUNI_IPN_TOKEN, settings.PESAPAL_IPN_TOKEN = (
        "jt-syn",
        "bt-syn",
        "pt-syn",
    )
    settings.JENGA_IPN_USER, settings.JENGA_IPN_PASSWORD = "syn-ipn", "syn-ipn-password"
    settings.BUNI_IPN_ALLOWED_IPS = ["127.0.0.1/32"]
    fakes._jenga = fakes._pesapal = None
    providers._PesapalToken.value = ""


# --- signing -------------------------------------------------------------------------------


def test_jenga_signature_strings_follow_the_documented_examples():
    assert (
        signing.balance_message("0011547896523", "KE", "2018-08-09") == "0011547896523KE2018-08-09"
    )
    assert (
        signing.payment_link_message("2024-03-22", Decimal("400"), "KES", "OPEN", "123456789")
        == "2024-03-22400KESOPEN123456789"
    )
    assert signing.jenga_amount(Decimal("400.00")) == "400"
    assert signing.jenga_amount(Decimal("400.50")) == "400.5"
    assert signing.transaction_details_message("10120120098767") == "10120120098767"


def test_signatures_are_sha256_rsa_and_verify_only_unchanged_messages(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    message = signing.balance_message("0011547896523", "KE", "2018-08-09")
    signature = signing.sign(message, key)
    assert signature == signing.sign(message, key)  # PKCS#1 v1.5 is deterministic
    assert signing.verify(message.encode(), signature, key.public_key())
    assert not signing.verify(b"0011547896523KE2018-08-10", signature, key.public_key())
    assert not signing.verify(message.encode(), "not base64!", key.public_key())
    from cryptography.hazmat.primitives import serialization

    pem = tmp_path / "key.pem"
    pem.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    assert signing.sign(message, signing.load_private_key(pem)) == signature


# --- IPN vectors ---------------------------------------------------------------------------


def post(client, provider, token, body, **headers):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return client.post(
        f"{HOOK}/{provider}/{token}/", raw, content_type="application/json", **headers
    )


def jenga_auth(user="syn-ipn", password="syn-ipn-password"):  # noqa: S107 - synthetic
    return {"HTTP_AUTHORIZATION": fakes.basic_auth(user, password)}


def test_jenga_ipn_is_confirmed_by_the_status_query(client):
    fakes.shared_jenga().record("SYN-JG-0001", Decimal("1500.00"))
    assert (
        post(
            client,
            "jenga",
            "jt-syn",
            fakes.jenga_ipn("SYN-JG-0001", "1500", "INV-SYN-1"),
            **jenga_auth(),
        ).status_code
        == 200
    )
    assert webhooks.process_pending() == (1, 0)
    row = BankNotification.objects.get()
    assert (row.status, row.amount, row.confirmed_amount, row.account_reference) == (
        "confirmed",
        Decimal("1500.00"),
        Decimal("1500.00"),
        "INV-SYN-1",
    )
    event = OutboxEvent.objects.get(topic="banking.notification.confirmed")
    assert event.payload["amount"] == "1500.00" and event.payload["provider"] == "jenga"
    calls = fakes.shared_jenga().calls
    assert calls[-1][1].endswith("/transactions/details/SYN-JG-0001") and calls[-1][2]["signature"]
    stored = " ".join(f"{r.request_body} {r.response_body}" for r in ExchangeLog.objects.all())
    assert "fake-jenga-token" not in stored  # bearer headers are redacted


@pytest.mark.parametrize(
    "auth, token",
    [(jenga_auth(password="wrong"), "jt-syn"), (jenga_auth(), "wrong-token"), ({}, "jt-syn")],
)
def test_jenga_ipn_with_bad_credentials_is_rejected(client, auth, token):
    assert (
        post(client, "jenga", token, fakes.jenga_ipn("SYN-JG-0002", "10", "B"), **auth).status_code
        == 403
    )
    assert WebhookInbox.objects.get().status == "rejected"
    assert not BankNotification.objects.exists()


def test_duplicate_jenga_ipn_is_stored_once(client):
    fakes.shared_jenga().record("SYN-JG-0003", Decimal("10.00"))
    body = fakes.jenga_ipn("SYN-JG-0003", "10", "B")
    post(client, "jenga", "jt-syn", body, **jenga_auth())
    post(client, "jenga", "jt-syn", body, **jenga_auth())
    assert sorted(WebhookInbox.objects.values_list("status", flat=True)) == [
        "duplicate",
        "received",
    ]
    webhooks.process_pending()
    assert BankNotification.objects.count() == 1


def test_amount_mismatch_and_unknown_reference_never_confirm(client):
    fakes.shared_jenga().record("SYN-JG-0004", Decimal("900.00"))
    post(client, "jenga", "jt-syn", fakes.jenga_ipn("SYN-JG-0004", "1000", "B"), **jenga_auth())
    post(client, "jenga", "jt-syn", fakes.jenga_ipn("SYN-JG-0005", "1000", "B"), **jenga_auth())
    webhooks.process_pending()
    assert dict(BankNotification.objects.values_list("reference", "status")) == {
        "SYN-JG-0004": "mismatch",
        "SYN-JG-0005": "unknown",
    }
    assert not OutboxEvent.objects.filter(topic="banking.notification.confirmed").exists()


def test_buni_ipn_signature_and_ip_allowlist(client):
    body, signature = fakes.buni_ipn("SYN-KCB-0001", "250.00", "INV-SYN-2")
    assert post(client, "buni", "bt-syn", body, HTTP_SIGNATURE=signature).status_code == 200
    tampered, bad = fakes.buni_ipn("SYN-KCB-0002", "250.00", "INV-SYN-3", tamper=True)
    assert post(client, "buni", "bt-syn", tampered, HTTP_SIGNATURE=bad).status_code == 403
    assert (
        post(
            client, "buni", "bt-syn", body, HTTP_SIGNATURE=signature, REMOTE_ADDR="10.9.9.9"
        ).status_code
        == 403
    )
    assert post(client, "buni", "bt-syn", body).status_code == 403  # no signature
    webhooks.process_pending()
    row = BankNotification.objects.get()
    # Buni's query API is not documented to us (GAP-BUNI-001): received, not confirmed.
    assert (row.reference, row.status, row.amount) == (
        "SYN-KCB-0001",
        "received",
        Decimal("250.00"),
    )


# --- Pesapal --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "amount, status",
    [
        ("2500.00", "confirmed"),
        ("2500.02", "failed"),
        ("2500.03", "reversed"),
        ("2500.04", "received"),
    ],
)
def test_pesapal_checkout_then_ipn_then_query(client, amount, status):
    pesapal = providers.Pesapal()
    ipn_id = pesapal.register_ipn("https://hospital.example.test/api/v1/hooks/pesapal/pt-syn/")
    tracking, redirect = pesapal.submit_order(
        reference="INV-SYN-9",
        amount=Decimal(amount),
        description="Synthetic invoice",
        callback_url="https://hospital.example.test/return",
        notification_id=ipn_id,
        email="payer@example.test",
    )
    assert redirect.endswith(tracking)
    assert (
        post(client, "pesapal", "pt-syn", fakes.pesapal_ipn(tracking, "INV-SYN-9")).status_code
        == 200
    )
    webhooks.process_pending()
    row = BankNotification.objects.get()
    assert row.status == status and row.account_reference == "INV-SYN-9"
    sent = json.loads(
        next(r.request_body for r in ExchangeLog.objects.filter(operation="submit_order"))
    )
    assert (
        sent["json"]["amount"] == float(amount)
        and sent["json"]["billing_address"]["email_address"] == "[redacted]"
    )


def test_pesapal_amount_is_an_exact_json_number():
    assert providers.dumps({"amount": Decimal("100.10")}) == b'{"amount": 100.10}'


def test_pesapal_notification_again_updates_the_same_row(client):
    pesapal = providers.Pesapal()
    tracking, _ = pesapal.submit_order(
        reference="INV-SYN-10",
        amount=Decimal("10.00"),
        description="x",
        callback_url="https://h.example.test/r",
        notification_id="fake-ipn-1",
        phone="0700000000",
    )
    for _ in range(2):
        post(client, "pesapal", "pt-syn", fakes.pesapal_ipn(tracking, "INV-SYN-10"))
    assert webhooks.process_pending() == (2, 0)
    assert BankNotification.objects.count() == 1
    assert OutboxEvent.objects.filter(topic="banking.notification.confirmed").count() == 1


def test_pesapal_needs_a_contact_and_a_bad_tracking_id_is_unknown(client):
    pesapal = providers.Pesapal()
    with pytest.raises(ValueError):
        pesapal.submit_order(
            reference="X",
            amount=Decimal("1.00"),
            description="x",
            callback_url="https://h.example.test/r",
            notification_id="fake-ipn-1",
        )
    post(client, "pesapal", "pt-syn", fakes.pesapal_ipn("fake-nope", "X"))
    webhooks.process_pending()
    assert BankNotification.objects.get().status == "unknown"


# --- modes ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, cls, gap",
    [
        ("JENGA_MODE", providers.Jenga, "JENGA"),
        ("BUNI_MODE", providers.Buni, "BUNI"),
        ("PESAPAL_MODE", providers.Pesapal, "PESAPAL"),
    ],
)
def test_sandbox_refuses_without_credentials_or_spec(settings, name, cls, gap):
    setattr(settings, name, "sandbox")
    with pytest.raises(providers.ProviderNotConfigured, match=f"{gap}_"):
        cls()


def test_jenga_and_buni_refuse_even_with_credentials_until_their_gaps_close(settings, tmp_path):
    settings.JENGA_MODE = settings.BUNI_MODE = "live"
    for name in (
        "JENGA_BASE_URL",
        "JENGA_MERCHANT_CODE",
        "JENGA_API_KEY",
        "JENGA_CONSUMER_SECRET",
        "JENGA_PRIVATE_KEY_PATH",
        "BUNI_BASE_URL",
        "BUNI_CONSUMER_KEY",
        "BUNI_CONSUMER_SECRET",
        "BUNI_IPN_PUBLIC_KEY_PATH",
    ):
        setattr(settings, name, "set")
    with pytest.raises(providers.ProviderNotConfigured, match="GAP-JENGA-002"):
        providers.Jenga()
    with pytest.raises(providers.ProviderNotConfigured, match="GAP-BUNI-001"):
        providers.Buni()


def test_provider_outage_leaves_the_notification_for_retry(client, monkeypatch):
    def down(self, notice):
        raise providers.ProviderUnavailable("down")

    monkeypatch.setattr(providers.Jenga, "query", down)
    post(client, "jenga", "jt-syn", fakes.jenga_ipn("SYN-JG-0009", "10", "B"), **jenga_auth())
    assert webhooks.process_pending() == (0, 1)
    assert WebhookInbox.objects.get().status == "failed"
    assert not BankNotification.objects.exists()
    notifications.register()  # idempotent re-registration
