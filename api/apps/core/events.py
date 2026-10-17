"""Domain events through a transactional outbox (ADR-016, docs/agent/lanes/SEAMS.md).

    from apps.core import events

    events.emit("billing.invoice.finalized", aggregate=invoice, payload={"visit_id": "…"})

    @events.consumer("billing.invoice.finalized", name="insurance.open_claim")
    def open_claim(event: OutboxEvent) -> None: ...

``emit`` runs inside the caller's transaction, so an event exists exactly when its change
does. ``relay`` (Celery beat, every minute) hands each event to every consumer of its topic,
each in its own transaction, at least once: consumers must be idempotent (the delivery row
is written in the same transaction as the consumer's work, so a crash replays it). Payloads
hold IDs and codes only; keys that look like PHI are refused.
"""

import logging
from collections.abc import Callable
from typing import Any

from django.db import models, transaction
from django.utils import timezone

from apps.core.models import EventDelivery, OutboxEvent
from apps.core.scrubbing import is_sensitive_key

logger = logging.getLogger(__name__)

Handler = Callable[[OutboxEvent], None]
_CONSUMERS: dict[str, dict[str, Handler]] = {}
BATCH = 500
# After this many failures a delivery is parked (``last_error`` starts "parked:") so one
# broken consumer cannot hold the queue; parked deliveries need an operator.
MAX_ATTEMPTS = 20


class EventError(ValueError):
    pass


def _check_payload(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                raise EventError(f"Event payload key {path}{key!r} looks like personal data.")
            _check_payload(item, f"{path}{key}.")
    elif isinstance(value, list | tuple):
        for item in value:
            _check_payload(item, path)


def emit(
    topic: str,
    *,
    aggregate: Any,
    payload: dict[str, Any] | None = None,
    facility: Any = None,
) -> OutboxEvent:
    """Record an event in the current transaction. ``aggregate`` is a model instance or an
    ``(aggregate_type, id)`` pair; ``facility`` an instance or id (defaults to the
    aggregate's ``facility_id``)."""
    if not transaction.get_connection().in_atomic_block:
        raise EventError("emit() must run inside the transaction that makes the change.")
    payload = payload or {}
    _check_payload(payload)
    if isinstance(aggregate, tuple):
        aggregate_type, aggregate_id = aggregate
    else:
        aggregate_type = aggregate._meta.label_lower
        aggregate_id = aggregate.pk
    facility_id = getattr(facility, "pk", facility)
    if facility_id is None and not isinstance(aggregate, tuple):
        facility_id = getattr(aggregate, "facility_id", None)
    return OutboxEvent.objects.create(
        topic=topic,
        aggregate_type=str(aggregate_type),
        aggregate_id=str(aggregate_id),
        facility_id=facility_id,
        payload=payload,
    )


def consumer(topic: str, *, name: str) -> Callable[[Handler], Handler]:
    """Register ``fn`` for ``topic`` under a stable ``name`` (renaming it re-delivers)."""

    def register(fn: Handler) -> Handler:
        handlers = _CONSUMERS.setdefault(topic, {})
        if name in handlers and handlers[name] is not fn:
            raise EventError(f"Consumer name {name!r} is already registered for {topic!r}.")
        handlers[name] = fn
        return fn

    return register


def consumers_of(topic: str) -> dict[str, Handler]:
    return dict(_CONSUMERS.get(topic, {}))


def relay(*, limit: int = BATCH) -> tuple[int, int]:
    """Deliver pending events to their consumers; return (deliveries, failures)."""
    delivered = failed = 0
    pending = OutboxEvent.objects.filter(relayed_at__isnull=True).order_by("created_at")[:limit]
    for event in pending:
        complete = True
        for name, handler in consumers_of(event.topic).items():
            settled = EventDelivery.objects.filter(event=event, consumer=name).filter(
                models.Q(delivered_at__isnull=False) | models.Q(last_error__startswith="parked:")
            )
            if settled.exists():
                continue
            try:
                with transaction.atomic():
                    handler(event)
                    EventDelivery.objects.update_or_create(
                        event=event,
                        consumer=name,
                        defaults={"delivered_at": timezone.now(), "last_error": ""},
                    )
                delivered += 1
            except Exception as exc:
                failed += 1
                row, _ = EventDelivery.objects.get_or_create(event=event, consumer=name)
                attempts = row.attempts + 1
                parked = attempts >= MAX_ATTEMPTS
                error = f"{'parked:' if parked else ''}{type(exc).__name__}"[:100]
                EventDelivery.objects.filter(pk=row.pk).update(attempts=attempts, last_error=error)
                complete = complete and parked
                logger.exception(
                    "Event consumer failed",
                    extra={
                        "event_id": str(event.pk),
                        "consumer": name,
                        "topic": event.topic,
                        "parked": parked,
                    },
                )
        if complete:
            OutboxEvent.objects.filter(pk=event.pk).update(relayed_at=timezone.now())
    return delivered, failed
