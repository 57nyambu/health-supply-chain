"""Bank and card provider clients (PAYMENTS.md §4-6; ADR-075).

Each provider gives two things the notification handler needs:

- ``parse(body)`` → ``Notice``: the notification's documented fields, normalised;
- ``query(notice)`` → ``Confirmation``: the provider's own answer for that payment
  (a notification alone never marks money as received — PAYMENTS.md §1).

Field names come from the providers' published docs (DECISIONS.md, Phase 3 findings).
``*_MODE=fake`` (default) talks to in-process fakes (``fakes.py``) through the same code;
``sandbox``/``live`` refuse to start without credentials, and Jenga and Buni also refuse
until their spec gaps close (GAP-JENGA-002: token endpoint; GAP-BUNI-001: portal-only docs).
"""

from __future__ import annotations

import enum
import json
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.banking import signing
from apps.integrations.exchange import exchange
from apps.integrations.models import ExchangeLog

TIMEOUT = httpx.Timeout(30.0, connect=5.0)
REDACT = {
    "consumer_key",
    "consumer_secret",
    "token",
    "phone_number",
    "email_address",
    "mobileNumber",
    "name",
    "first_name",
    "last_name",
}


class ProviderNotConfigured(Exception):
    """The provider's mode needs credentials or a specification we do not have."""


class ProviderUnavailable(Exception):
    """The provider did not answer; try the query again later."""


class ConfirmationState(enum.StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    PENDING = "pending"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class Notice:
    reference: str  # the provider's reference (dedupe key)
    account_reference: str = ""  # our bill/invoice number as the payer gave it
    amount: Decimal | None = None
    currency: str = "KES"
    channel: str = ""
    reported_status: str = ""
    occurred_at: datetime | None = None
    summary: dict[str, Any] = field(default_factory=dict)  # no names, no phone numbers


@dataclass(frozen=True)
class Confirmation:
    state: ConfirmationState
    amount: Decimal | None = None
    provider_status: str = ""


def money(value: Any) -> Decimal | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


_DECIMAL = re.compile(r'"__decimal__(-?[0-9]+(?:\.[0-9]+)?)__"')


def dumps(value: Any) -> bytes:
    """JSON with Decimals written as exact numbers (never through float)."""

    def mark(item: Any) -> Any:
        if isinstance(item, Decimal):
            return f"__decimal__{item}__"
        if isinstance(item, dict):
            return {k: mark(v) for k, v in item.items()}
        if isinstance(item, list):
            return [mark(v) for v in item]
        return item

    return _DECIMAL.sub(lambda m: m.group(1), json.dumps(mark(value))).encode()


def _redacted(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[redacted]" if k in REDACT else _redacted(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redacted(v) for v in value]
    return value


def _mode(name: str) -> str:
    mode = str(getattr(settings, name, "fake"))
    if mode not in ("fake", "sandbox", "live"):
        raise ProviderNotConfigured(f"{name}={mode!r} is not one of fake, sandbox, live.")
    return mode


def setting(name: str) -> str:
    return str(getattr(settings, name, "") or "")


def _state_code(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _missing(*names: str) -> list[str]:
    return [n for n in names if not getattr(settings, n, "")]


class _Http:
    """GET/POST with exchange logging. Reads may be retried by callers; POSTs never are."""

    def __init__(
        self, integration: str, mode: str, base_url: str, transport: httpx.BaseTransport | None
    ):
        self.integration = integration
        self.mode = mode
        self.http = httpx.Client(base_url=base_url, timeout=TIMEOUT, transport=transport)

    def call(
        self,
        method: str,
        path: str,
        operation: str,
        *,
        headers: dict[str, str],
        params: dict[str, str] | None = None,
        body: Any = None,
    ) -> httpx.Response:
        with exchange(
            self.integration,
            operation,
            mode=self.mode,
            request={
                "method": method,
                "path": path,
                "params": params or {},
                "json": _redacted(json.loads(dumps(body))) if body is not None else None,
            },
            headers=headers,
        ) as call:
            try:
                content = None if body is None else dumps(body)
                if content is not None:
                    headers = {**headers, "Content-Type": "application/json"}
                response = self.http.request(
                    method, path, headers=headers, params=params, content=content
                )
            except httpx.HTTPError as exc:
                call.outcome = ExchangeLog.Outcome.UNAVAILABLE
                raise ProviderUnavailable(f"{self.integration} did not answer.") from exc
            call.http_status = response.status_code
            try:
                call.response = _redacted(response.json())
            except ValueError:
                call.response = None
            if response.status_code >= 500:
                call.outcome = ExchangeLog.Outcome.UNAVAILABLE
                raise ProviderUnavailable(f"{self.integration} failed to answer.")
            if response.status_code == 404:
                call.outcome = ExchangeLog.Outcome.NOT_FOUND
            elif response.status_code >= 400:
                call.outcome = ExchangeLog.Outcome.ERROR
            return response


JENGA_STATES = {
    2: ConfirmationState.COMPLETED,
    1: ConfirmationState.FAILED,
    -1: ConfirmationState.PENDING,
}


def nairobi_time(value: Any) -> datetime | None:
    """Provider timestamps without an offset are Kenyan local time."""
    parsed = parse_datetime(str(value or "").replace(" ", "T"))
    if parsed is not None and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, ZoneInfo("Africa/Nairobi"))
    return parsed


# --- Equity Bank: Jenga --------------------------------------------------------------------


class Jenga:
    """IPNs are verified by Basic Auth (Jenga's IPN guide); payments are confirmed with
    ``GET /v3-apis/transaction-api/v3.0/transactions/details/{ref}`` signed over ``ref``."""

    code = "jenga"

    def __init__(self, *, transport: httpx.BaseTransport | None = None, key: Any = None):
        self.mode = _mode("JENGA_MODE")
        if self.mode == "fake":
            from apps.banking.fakes import shared_jenga

            transport = transport or shared_jenga().transport()
            base_url, self._token = "https://jenga.fake.invalid", "fake-jenga-token"
            self._key = key
        else:
            missing = _missing(
                "JENGA_BASE_URL",
                "JENGA_MERCHANT_CODE",
                "JENGA_API_KEY",
                "JENGA_CONSUMER_SECRET",
                "JENGA_PRIVATE_KEY_PATH",
            )
            if missing:
                raise ProviderNotConfigured(
                    f"JENGA_MODE={self.mode} needs {', '.join(missing)} (JengaHQ onboarding — owner action)."
                )
            raise ProviderNotConfigured(
                "The Jenga token endpoint is not in the public guides read so far (GAP-JENGA-002); "
                "record it from the JengaHQ portal or sandbox traffic before enabling sandbox/live."
            )
        self.http = _Http("bank.jenga", self.mode, base_url, transport)

    def _signature(self, message: str) -> str:
        if self._key is None:  # fake mode without a key: the fake checks only presence
            return "fake-signature"
        return signing.sign(message, self._key)

    @staticmethod
    def parse(body: dict[str, Any]) -> Notice:
        transaction = body.get("transaction") or {}
        return Notice(
            reference=str(transaction.get("reference") or ""),
            account_reference=str(transaction.get("billNumber") or ""),
            amount=money(transaction.get("amount")),
            currency=str(transaction.get("currency") or "KES"),
            channel=str(transaction.get("paymentMode") or ""),
            reported_status=str(transaction.get("status") or ""),
            occurred_at=nairobi_time(transaction.get("date")),
            summary={
                "callback_type": body.get("callbackType", ""),
                "remarks": str(transaction.get("remarks") or "")[:60],
            },
        )

    def query(self, notice: Notice) -> Confirmation:
        path = f"/v3-apis/transaction-api/v3.0/transactions/details/{notice.reference}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Signature": self._signature(signing.transaction_details_message(notice.reference)),
        }
        response = self.http.call("GET", path, "transaction_details", headers=headers)
        body = response.json() if response.content else {}
        data = body.get("data") if isinstance(body, dict) else None
        if response.status_code == 404 or not body.get("status") or not isinstance(data, dict):
            return Confirmation(
                ConfirmationState.NOT_FOUND, provider_status=str(body.get("code", ""))
            )
        code = _state_code(data.get("stateCode"))
        state = (
            JENGA_STATES.get(code, ConfirmationState.PENDING)
            if code is not None
            else ConfirmationState.PENDING
        )
        return Confirmation(state, money(data.get("amount")), str(data.get("state") or ""))


# --- KCB: Buni -----------------------------------------------------------------------------


class Buni:
    """IPNs carry a ``Signature`` header: SHA256withRSA over the raw body with KCB's public
    key (PAYMENTS.md §5), plus a source-IP allowlist. Buni's IPN and query specs sit behind
    the developer portal (GAP-BUNI-001), so payloads are read with the documented minimum
    and notices stay unconfirmed until reconciliation matches a statement line."""

    code = "buni"

    def __init__(self) -> None:
        self.mode = _mode("BUNI_MODE")
        if self.mode != "fake":
            missing = _missing(
                "BUNI_BASE_URL",
                "BUNI_CONSUMER_KEY",
                "BUNI_CONSUMER_SECRET",
                "BUNI_IPN_PUBLIC_KEY_PATH",
            )
            if missing:
                raise ProviderNotConfigured(
                    f"BUNI_MODE={self.mode} needs {', '.join(missing)} (KCB request letter — owner action)."
                )
            raise ProviderNotConfigured(
                "KCB Buni's IPN payload and query API are documented only inside the Buni portal "
                "(GAP-BUNI-001); record them before enabling sandbox/live."
            )

    def public_key(self) -> Any:
        if self.mode == "fake":
            from apps.banking.fakes import buni_test_public_key

            return buni_test_public_key()
        return signing.load_public_key(setting("BUNI_IPN_PUBLIC_KEY_PATH"))

    def verify(self, raw_body: bytes, signature: str) -> bool:
        return bool(signature) and signing.verify(raw_body, signature, self.public_key())

    @staticmethod
    def parse(body: dict[str, Any]) -> Notice:
        # The fake's synthetic shape (GAP-BUNI-001): transactionReference, billReference,
        # amount, currency, channel, timestamp.
        return Notice(
            reference=str(body.get("transactionReference") or ""),
            account_reference=str(body.get("billReference") or ""),
            amount=money(body.get("amount")),
            currency=str(body.get("currency") or "KES"),
            channel=str(body.get("channel") or ""),
            reported_status="credited",
            occurred_at=nairobi_time(body.get("timestamp")),
        )

    def query(self, notice: Notice) -> Confirmation:
        return Confirmation(ConfirmationState.PENDING, provider_status="awaiting_statement")


# --- Cards: Pesapal API 3.0 --------------------------------------------------------------------

# 0 = INVALID: not (yet) a valid payment; re-query rather than call it failed (GAP-PESAPAL-002).
PESAPAL_STATES = {
    0: ConfirmationState.PENDING,
    1: ConfirmationState.COMPLETED,
    2: ConfirmationState.FAILED,
    3: ConfirmationState.REVERSED,
}


class _PesapalToken:
    lock = threading.Lock()
    value = ""
    until = 0.0


class Pesapal:
    """Hosted checkout (no card data ever reaches us). ``RequestToken`` (≈5 min) →
    ``RegisterIPN`` → ``SubmitOrderRequest`` → ``GetTransactionStatus``. The IPN carries only
    ``OrderTrackingId``/``OrderMerchantReference``; the status always comes from the query."""

    code = "pesapal"

    def __init__(self, *, transport: httpx.BaseTransport | None = None):
        self.mode = _mode("PESAPAL_MODE")
        if self.mode == "fake":
            from apps.banking.fakes import shared_pesapal

            transport = transport or shared_pesapal().transport()
            base_url, self._key, self._secret = (
                "https://pesapal.fake.invalid/v3",
                "fake-key",
                "fake-secret",
            )
        else:
            missing = _missing(
                "PESAPAL_BASE_URL",
                "PESAPAL_CONSUMER_KEY",
                "PESAPAL_CONSUMER_SECRET",
                "PESAPAL_IPN_ID",
            )
            if missing:
                raise ProviderNotConfigured(
                    f"PESAPAL_MODE={self.mode} needs {', '.join(missing)} (Pesapal merchant account — owner action)."
                )
            base_url = setting("PESAPAL_BASE_URL").rstrip("/")
            self._key, self._secret = (
                setting("PESAPAL_CONSUMER_KEY"),
                setting("PESAPAL_CONSUMER_SECRET"),
            )
        self.http = _Http("card.pesapal", self.mode, base_url, transport)

    def _token(self) -> str:
        with _PesapalToken.lock:
            if _PesapalToken.value and time.monotonic() < _PesapalToken.until:
                return _PesapalToken.value
            response = self.http.call(
                "POST",
                "/api/Auth/RequestToken",
                "token",
                headers={"Accept": "application/json"},
                body={"consumer_key": self._key, "consumer_secret": self._secret},
            )
            token = str((response.json() or {}).get("token") or "")
            if response.status_code != 200 or not token:
                raise ProviderNotConfigured("Pesapal refused the merchant credentials.")
            _PesapalToken.value, _PesapalToken.until = (
                token,
                time.monotonic() + 240,
            )  # tokens last ~5 min
            return token

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json", "Authorization": f"Bearer {self._token()}"}

    def register_ipn(self, url: str) -> str:
        response = self.http.call(
            "POST",
            "/api/URLSetup/RegisterIPN",
            "register_ipn",
            headers=self._headers(),
            body={"url": url, "ipn_notification_type": "POST"},
        )
        return str((response.json() or {}).get("ipn_id") or "")

    def submit_order(
        self,
        *,
        reference: str,
        amount: Decimal,
        description: str,
        callback_url: str,
        notification_id: str,
        email: str = "",
        phone: str = "",
    ) -> tuple[str, str]:
        """Start a hosted checkout; returns (order_tracking_id, redirect_url). Never retried."""
        if not (email or phone):
            raise ValueError("Pesapal needs the payer's e-mail address or phone number.")
        body = {
            "id": reference[:50],
            "currency": "KES",
            "amount": amount.quantize(Decimal("0.01")),  # a JSON number, written exactly
            "description": description[:100],
            "callback_url": callback_url,
            "notification_id": notification_id,
            "billing_address": {
                "email_address": email,
                "phone_number": phone,
                "country_code": "KE",
            },
        }
        response = self.http.call(
            "POST",
            "/api/Transactions/SubmitOrderRequest",
            "submit_order",
            headers=self._headers(),
            body=body,
        )
        data = response.json() or {}
        if response.status_code != 200 or not data.get("order_tracking_id"):
            raise ProviderUnavailable("Pesapal did not create the checkout.")
        return str(data["order_tracking_id"]), str(data.get("redirect_url") or "")

    @staticmethod
    def parse(body: dict[str, Any]) -> Notice:
        return Notice(
            reference=str(body.get("OrderTrackingId") or ""),
            account_reference=str(body.get("OrderMerchantReference") or ""),
            reported_status=str(body.get("OrderNotificationType") or ""),
        )

    def query(self, notice: Notice) -> Confirmation:
        response = self.http.call(
            "GET",
            "/api/Transactions/GetTransactionStatus",
            "transaction_status",
            headers=self._headers(),
            params={"orderTrackingId": notice.reference},
        )
        data = response.json() if response.content else {}
        if response.status_code == 404 or not isinstance(data, dict) or "status_code" not in data:
            return Confirmation(ConfirmationState.NOT_FOUND)
        code = _state_code(data.get("status_code"))
        state = (
            PESAPAL_STATES.get(code, ConfirmationState.PENDING)
            if code is not None
            else ConfirmationState.PENDING
        )
        return Confirmation(
            state, money(data.get("amount")), str(data.get("payment_status_description") or "")
        )


def provider(code: str) -> Jenga | Buni | Pesapal:
    if code == "jenga":
        return Jenga()
    if code == "buni":
        return Buni()
    if code == "pesapal":
        return Pesapal()
    raise ProviderNotConfigured(f"No bank provider {code!r}.")


def body_of(raw: str) -> dict[str, Any]:
    """JSON bodies, or a form/query string (Pesapal may notify by GET)."""
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        from urllib.parse import parse_qs

        return {k: v[0] for k, v in parse_qs(raw).items()}
    return value if isinstance(value, dict) else {}
