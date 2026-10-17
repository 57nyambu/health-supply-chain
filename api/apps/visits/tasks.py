from celery import shared_task

from apps.visits import services


@shared_task
def flag_idle_tickets() -> int:
    """Left-before-seen candidates: tickets idle past the facility's limit (idempotent)."""
    return services.flag_idle_tickets()
