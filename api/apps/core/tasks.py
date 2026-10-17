from celery import shared_task

from apps.core.idempotency import purge_expired_records


@shared_task
def purge_expired_idempotency_records() -> int:
    return purge_expired_records()


@shared_task
def relay_outbox():
    """Deliver domain events to their consumers (apps.core.events, ADR-016)."""
    from apps.core.events import relay

    delivered, failed = relay()
    return {"delivered": delivered, "failed": failed}
