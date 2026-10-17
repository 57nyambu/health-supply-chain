from celery import shared_task

from apps.etims import services


@shared_task
def transmit_due() -> tuple[int, int]:
    """Send queued eTIMS documents whose retry time has come (beat ``p3-etims-retry``)."""
    return services.transmit_due()
