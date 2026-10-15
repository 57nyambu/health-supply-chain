from celery import shared_task

from apps.core.idempotency import purge_expired_records


@shared_task
def purge_expired_idempotency_records() -> int:
    return purge_expired_records()
