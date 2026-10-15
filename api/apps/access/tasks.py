from celery import shared_task

from apps.access.approvals import expire_overdue


@shared_task
def expire_approval_requests() -> int:
    return expire_overdue()
