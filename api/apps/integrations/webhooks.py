"""Inbound callbacks and IPNs (DESIGN §17; PAYMENTS.md §1; seam for the parallel lanes).

A provider app registers how its notifications are verified, referenced and handled::

    from apps.integrations import webhooks

    webhooks.register(
        "mpesa",
        verify=verify_mpesa,        # (request, token) -> bool: signature / basic auth / secret
        reference=mpesa_reference,  # (payload) -> str | None: the provider's own reference
        handle=handle_mpesa,        # (inbox: WebhookInbox) -> None, idempotent
    )

``POST /api/v1/hooks/<provider>/<token>/`` stores every notification encrypted, rejects
those that fail verification (403), answers duplicates and new ones with 200 at once, and
``process_pending`` (Celery beat, every minute) calls ``handle`` outside the request.
A callback alone never moves money: handlers confirm with the provider's query API first.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.integrations.exchange import redact_headers
from apps.integrations.models import WebhookInbox

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 20
BATCH = 200


@dataclass(frozen=True)
class Provider:
    code: str
    verify: Callable[[Any, str], bool]
    reference: Callable[[Any], str | None]
    handle: Callable[[WebhookInbox], None]


_PROVIDERS: dict[str, Provider] = {}


def register(
    code: str,
    *,
    verify: Callable[[Any, str], bool],
    reference: Callable[[Any], str | None],
    handle: Callable[[WebhookInbox], None],
) -> Provider:
    existing = _PROVIDERS.get(code)
    provider = Provider(code, verify, reference, handle)
    if existing is not None and existing != provider:
        raise ValueError(f"Webhook provider {code!r} is already registered.")
    _PROVIDERS[code] = provider
    return provider


def provider(code: str) -> Provider | None:
    return _PROVIDERS.get(code)


def _payload(body: str) -> Any:
    try:
        return json.loads(body) if body else {}
    except ValueError:
        return {"raw": True}


def receive(code: str, request: Any, token: str) -> tuple[int, WebhookInbox | None]:
    """Store one notification; return (HTTP status, row). Unknown providers get 404."""
    entry = provider(code)
    if entry is None:
        return 404, None
    body = request.body.decode("utf-8", "replace")
    headers = redact_headers({k: v for k, v in request.headers.items()})
    row = WebhookInbox(
        provider=code,
        remote_addr=request.META.get("REMOTE_ADDR") or None,
        headers=headers,
        raw_body=body,
    )
    try:
        verified = bool(entry.verify(request, token))
    except Exception:
        logger.exception("Webhook verification raised", extra={"provider": code})
        verified = False
    if not verified:
        row.status = WebhookInbox.Status.REJECTED
        row.save()
        return 403, row
    reference = entry.reference(_payload(body)) or ""
    row.reference = reference[:128]
    with transaction.atomic():
        if (
            reference
            and WebhookInbox.objects.filter(provider=code, reference=row.reference)
            .exclude(status__in=[WebhookInbox.Status.REJECTED, WebhookInbox.Status.DUPLICATE])
            .exists()
        ):
            row.status = WebhookInbox.Status.DUPLICATE
        try:
            row.save()
        except IntegrityError:  # pragma: no cover - defensive
            row.status = WebhookInbox.Status.DUPLICATE
            row.save()
    return 200, row


def process_pending(*, limit: int = BATCH) -> tuple[int, int]:
    """Hand stored notifications to their provider's handler; return (processed, failed)."""
    done = failed = 0
    pending = WebhookInbox.objects.filter(
        status__in=[WebhookInbox.Status.RECEIVED, WebhookInbox.Status.FAILED]
    ).order_by("received_at")[:limit]
    for row in pending:
        entry = provider(row.provider)
        if entry is None:
            continue
        try:
            with transaction.atomic():
                entry.handle(row)
                WebhookInbox.objects.filter(pk=row.pk).update(
                    status=WebhookInbox.Status.PROCESSED,
                    processed_at=timezone.now(),
                    attempts=row.attempts + 1,
                    last_error="",
                )
            done += 1
        except Exception as exc:
            failed += 1
            attempts = row.attempts + 1
            status = (
                WebhookInbox.Status.PARKED
                if attempts >= MAX_ATTEMPTS
                else WebhookInbox.Status.FAILED
            )
            WebhookInbox.objects.filter(pk=row.pk).update(
                status=status, attempts=attempts, last_error=type(exc).__name__[:100]
            )
            logger.exception(
                "Webhook handler failed",
                extra={
                    "provider": row.provider,
                    "inbox_id": str(row.pk),
                    "parked": status == "parked",
                },
            )
    return done, failed
