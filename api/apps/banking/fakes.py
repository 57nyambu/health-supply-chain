"""In-process fakes of Jenga, KCB Buni and Pesapal (synthetic data only; ADR-073, ADR-075).

The Jenga and Pesapal fakes are ``httpx.MockTransport``s answering the documented
endpoints, so fake mode runs the real clients. Buni's fake is a throwaway RSA key pair
generated per process: test vectors are signed with its private half and verified with its
public half exactly as KCB's key will be used.

Test vectors (``jenga_ipn``, ``buni_ipn``, ``pesapal_ipn``) cover: valid, bad signature or
credentials, duplicate, amount mismatch (the bank's query reports a different amount) and
unknown reference (the bank does not know it). Pesapal outcomes follow the order amount's
cents: .00 completed · .02 failed · .03 reversed · .04 still pending.
"""

from __future__ import annotations

import base64
import json
import secrets
import threading
from decimal import Decimal
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qs

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa

from apps.banking import signing

# --- Jenga ---------------------------------------------------------------------------------


class FakeJenga:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.transactions: dict[str, tuple[int, Decimal]] = {}  # reference → (stateCode, amount)
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def record(self, reference: str, amount: Decimal, *, state_code: int = 2) -> None:
        with self._lock:
            self.transactions[reference] = (state_code, amount)

    def handle(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.calls.append((request.method, request.url.path, dict(request.headers)))
        if not request.headers.get("Authorization", "").startswith(
            "Bearer "
        ) or not request.headers.get("Signature"):
            return httpx.Response(
                401,
                json={
                    "status": False,
                    "code": 401,
                    "message": "Invalid or expired access token",
                    "error_code": "UNAUTHORIZED",
                },
            )
        prefix = "/v3-apis/transaction-api/v3.0/transactions/details/"
        if request.method == "GET" and request.url.path.startswith(prefix):
            reference = request.url.path[len(prefix) :]
            with self._lock:
                found = self.transactions.get(reference)
            if found is None:
                return httpx.Response(
                    200,
                    json={
                        "status": False,
                        "code": 111102,
                        "message": "Transaction with the passed reference cannot be found",
                    },
                )
            state_code, amount = found
            state = {2: "Success", 1: "Failed", -1: "Pending"}[state_code]
            return httpx.Response(
                200,
                json={
                    "status": True,
                    "code": 0,
                    "message": "success",
                    "data": {
                        "state": state,
                        "stateCode": state_code,
                        "amount": float(amount),
                        "transactionReference": reference,
                        "serviceName": "Bill Payment",
                    },
                },
            )
        return httpx.Response(404, json={"status": False, "code": 404, "message": "Not found"})


def jenga_ipn(reference: str, amount: str, bill: str, *, status: str = "SUCCESS") -> dict[str, Any]:
    """A synthetic Jenga IPN body in the documented shape (no real person)."""
    return {
        "callbackType": "IPN",
        "customer": {
            "name": "Synthetic Payer",
            "mobileNumber": "254700000001",
            "reference": "SYN-CUST-1",
        },
        "transaction": {
            "date": "2026-10-17 10:15:20",
            "reference": reference,
            "paymentMode": "MPESA",
            "amount": float(Decimal(amount)),
            "currency": "KES",
            "orderCurrency": "KES",
            "billNumber": bill,
            "orderAmount": float(Decimal(amount)),
            "serviceCharge": 0,
            "status": status,
            "remarks": "00:Approved",
        },
        "bank": {"reference": reference, "transactionType": "C", "account": None},
    }


# --- KCB Buni --------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _buni_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def buni_test_public_key() -> rsa.RSAPublicKey:
    return _buni_key().public_key()


def buni_ipn(reference: str, amount: str, bill: str, *, tamper: bool = False) -> tuple[bytes, str]:
    """A synthetic Buni IPN body and its signature (tampered bodies fail verification)."""
    body = json.dumps(
        {
            "transactionReference": reference,
            "billReference": bill,
            "amount": amount,
            "currency": "KES",
            "channel": "MPESA",
            "timestamp": "2026-10-17T10:15:20+03:00",
        }
    ).encode()
    signature = signing.sign(body, _buni_key())
    if tamper:
        body = body.replace(amount.encode(), b"1")
    return body, signature


# --- Pesapal -----------------------------------------------------------------------------------

PESAPAL_CENTS = {"00": 1, "02": 2, "03": 3, "04": 0}


class FakePesapal:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.orders: dict[str, dict[str, Any]] = {}  # tracking id → order
        self.ipns: dict[str, str] = {}
        self.tokens: set[str] = set()

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/v3")
        body = json.loads(request.content) if request.content else {}
        if path == "/api/Auth/RequestToken":
            if not body.get("consumer_key") or not body.get("consumer_secret"):
                return httpx.Response(
                    200,
                    json={
                        "token": None,
                        "error": {"code": "invalid_consumer_key_or_secret_provided"},
                        "status": "500",
                    },
                )
            token = "fakepesapal." + secrets.token_hex(8)
            with self._lock:
                self.tokens.add(token)
            return httpx.Response(
                200,
                json={
                    "token": token,
                    "expiryDate": "2026-10-17T12:29:30Z",
                    "error": None,
                    "status": "200",
                    "message": "Request processed successfully",
                },
            )
        with self._lock:
            authorised = (
                request.headers.get("Authorization", "").removeprefix("Bearer ") in self.tokens
            )
        if not authorised:
            return httpx.Response(401, json={"error": {"code": "invalid_token"}, "status": "401"})
        if path == "/api/URLSetup/RegisterIPN":
            ipn_id = "fake-ipn-" + secrets.token_hex(4)
            with self._lock:
                self.ipns[ipn_id] = body.get("url", "")
            return httpx.Response(
                200,
                json={
                    "ipn_id": ipn_id,
                    "url": body.get("url"),
                    "ipn_status": 1,
                    "error": None,
                    "status": "200",
                },
            )
        if path == "/api/Transactions/SubmitOrderRequest":
            if body.get("notification_id") not in self.ipns and not str(
                body.get("notification_id", "")
            ).startswith("fake-ipn-"):
                return httpx.Response(
                    200, json={"error": {"code": "invalid_notification_id"}, "status": "500"}
                )
            tracking = "fake-" + secrets.token_hex(8)
            with self._lock:
                self.orders[tracking] = body
            return httpx.Response(
                200,
                json={
                    "order_tracking_id": tracking,
                    "merchant_reference": body.get("id"),
                    "redirect_url": f"https://pesapal.fake.invalid/pay/{tracking}",
                    "error": None,
                    "status": "200",
                },
            )
        if path == "/api/Transactions/GetTransactionStatus" and request.method == "GET":
            tracking = {k: v[0] for k, v in parse_qs(request.url.query.decode()).items()}.get(
                "orderTrackingId", ""
            )
            with self._lock:
                order = self.orders.get(tracking)
            if order is None:
                return httpx.Response(
                    200, json={"error": {"code": "order_not_found"}, "status": "500"}
                )
            amount = Decimal(str(order["amount"]))
            code = PESAPAL_CENTS.get(f"{amount:.2f}"[-2:], 1)
            description = {0: "INVALID", 1: "Completed", 2: "Failed", 3: "Reversed"}[code]
            return httpx.Response(
                200,
                json={
                    "payment_method": "Visa",
                    "amount": float(amount),
                    "confirmation_code": "SYN" + tracking[-8:].upper(),
                    "payment_status_description": description,
                    "payment_account": "476173**0010",
                    "status_code": code,
                    "merchant_reference": order.get("id"),
                    "currency": "KES",
                    "error": {"error_type": None, "code": None, "message": None},
                    "status": "200",
                },
            )
        return httpx.Response(404, json={"error": {"code": "not_found"}, "status": "404"})


def pesapal_ipn(tracking: str, merchant_reference: str) -> dict[str, str]:
    # Parameter names from Pesapal's documented callback URL (GetTransactionStatus example);
    # other IPN fields are not documented to us (GAP-PESAPAL-001).
    return {"OrderTrackingId": tracking, "OrderMerchantReference": merchant_reference}


_jenga: FakeJenga | None = None
_pesapal: FakePesapal | None = None
_shared_lock = threading.Lock()


def shared_jenga() -> FakeJenga:
    global _jenga
    with _shared_lock:
        _jenga = _jenga or FakeJenga()
        return _jenga


def shared_pesapal() -> FakePesapal:
    global _pesapal
    with _shared_lock:
        _pesapal = _pesapal or FakePesapal()
        return _pesapal


def basic_auth(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
