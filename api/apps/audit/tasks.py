from celery import shared_task

from apps.audit.services import anchor_finished_chains


@shared_task
def anchor_audit_chains() -> int:
    return len(anchor_finished_chains())
