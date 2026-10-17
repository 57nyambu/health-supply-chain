"""Bank and card notifications through ``apps.integrations.webhooks`` (SEAMS §6;
PAYMENTS.md §1, §4-6; ADR-075).

``POST /api/v1/hooks/<jenga|buni|pesapal>/<token>/`` — the path token must match the
provider's ``*_IPN_TOKEN``; then:

- Jenga: HTTP Basic credentials registered with the IPN URL (``JENGA_IPN_USER``/``…PASSWORD``);
- Buni: ``Signature`` header, SHA256withRSA over the raw body with KCB's public key, and the
  source IP in ``BUNI_IPN_ALLOWED_IPS``;
- Pesapal: the secret path only (Pesapal says its IPs change); the IPN carries no status.

Every check fails closed. The handler stores a ``BankNotification`` and asks the provider
for the payment's status; only that answer confirms money (never the notification alone).
Duplicates are dropped by the inbox (Jenga, Buni) or update the same row (Pesapal, which
notifies again when a status changes).
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.banking.models import BankNotification
from apps.banking.providers import Buni, ConfirmationState, Notice, body_of, provider, setting
from apps.core import events
from apps.integrations import webhooks
from apps.integrations.models import WebhookInbox

logger = logging.getLogger(__name__)

STATE = {
    ConfirmationState.COMPLETED: BankNotification.Status.CONFIRMED,
    ConfirmationState.FAILED: BankNotification.Status.FAILED,
    ConfirmationState.REVERSED: BankNotification.Status.REVERSED,
    ConfirmationState.NOT_FOUND: BankNotification.Status.UNKNOWN,
    ConfirmationState.PENDING: BankNotification.Status.RECEIVED,
}


def _same(given: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(given.encode(), expected.encode())


def _token_ok(setting: str, token: str) -> bool:
    return _same(token, str(getattr(settings, setting, "") or ""))


def _ip_allowed(request: Any, setting: str) -> bool:
    allowed = list(getattr(settings, setting, []) or [])
    try:
        address = ipaddress.ip_address(request.META.get("REMOTE_ADDR") or "")
    except ValueError:
        return False
    return any(address in ipaddress.ip_network(net, strict=False) for net in allowed)


def verify_jenga(request: Any, token: str) -> bool:
    if not _token_ok("JENGA_IPN_TOKEN", token):
        return False
    import base64

    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        user, _, password = base64.b64decode(header[6:]).decode().partition(":")
    except (ValueError, UnicodeDecodeError):
        return False
    return _same(user, setting("JENGA_IPN_USER")) and _same(password, setting("JENGA_IPN_PASSWORD"))


def verify_buni(request: Any, token: str) -> bool:
    if not _token_ok("BUNI_IPN_TOKEN", token) or not _ip_allowed(request, "BUNI_IPN_ALLOWED_IPS"):
        return False
    return Buni().verify(request.body, request.headers.get("Signature", ""))


def verify_pesapal(request: Any, token: str) -> bool:
    return _token_ok("PESAPAL_IPN_TOKEN", token)


def _reference(path: tuple[str, ...]) -> Any:
    def find(payload: Any) -> str | None:
        value = payload
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        return str(value) if value else None

    return find


def _summary(notice: Notice) -> str:
    return json.dumps(
        {"channel": notice.channel, "reported": notice.reported_status, **notice.summary}
    )


def handle(inbox: WebhookInbox) -> None:
    """Record the notification and confirm it with the provider (idempotent)."""
    client = provider(inbox.provider)
    notice = client.parse(body_of(inbox.raw_body))
    if not notice.reference:
        logger.warning("Bank notification without a reference", extra={"inbox_id": str(inbox.pk)})
        return
    confirmation = client.query(notice)  # ProviderUnavailable → the inbox retries later
    status = STATE[confirmation.state]
    if (
        status == BankNotification.Status.CONFIRMED
        and notice.amount is not None
        and confirmation.amount is not None
        and notice.amount != confirmation.amount
    ):
        status = BankNotification.Status.MISMATCH
    with transaction.atomic():
        row, _created = BankNotification.objects.select_for_update().get_or_create(
            provider=inbox.provider,
            reference=notice.reference[:128],
            defaults={"inbox_id": inbox.pk},
        )
        was = row.status
        row.account_reference = notice.account_reference[:100]
        row.amount = notice.amount if notice.amount is not None else row.amount
        row.currency = notice.currency[:3]
        row.channel = notice.channel[:30]
        row.occurred_at = notice.occurred_at or row.occurred_at
        row.summary = _summary(notice)
        row.status = status
        row.provider_status = confirmation.provider_status[:60]
        row.confirmed_amount = confirmation.amount
        if status == BankNotification.Status.CONFIRMED and row.confirmed_at is None:
            row.confirmed_at = timezone.now()
        row.save()
        if status == BankNotification.Status.CONFIRMED and was != status:
            events.emit(
                "banking.notification.confirmed",
                aggregate=row,
                payload={
                    "notification_id": str(row.pk),
                    "provider": row.provider,
                    "amount": str(row.confirmed_amount),
                    "bill_reference": row.account_reference,
                },
            )


jenga_reference = _reference(("transaction", "reference"))
buni_reference = _reference(("transactionReference",))


def pesapal_reference(payload: Any) -> str | None:
    """Pesapal notifies again when a status changes: no inbox dedupe; the handler updates
    the same row."""
    return None


def register() -> None:
    webhooks.register("jenga", verify=verify_jenga, reference=jenga_reference, handle=handle)
    webhooks.register("buni", verify=verify_buni, reference=buni_reference, handle=handle)
    webhooks.register("pesapal", verify=verify_pesapal, reference=pesapal_reference, handle=handle)
