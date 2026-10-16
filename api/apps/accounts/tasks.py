from celery import shared_task

from apps.accounts.licences import notify_expiring


@shared_task
def warn_expiring_licences() -> int:
    return notify_expiring()
