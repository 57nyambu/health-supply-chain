"""Staff notifications (DESIGN §14): stored now, e-mailed by the outbox job. Never put
clinical details in bodies.

``notify_user`` only writes the ``Notification`` row inside the caller's transaction, so no
request — least of all an emergency (break-glass) — ever waits on a mail server or a broker
(ADR-016 outbox). ``deliver_pending`` runs every minute from Celery beat, sends what is
unsent with a bounded SMTP timeout, and retries failures for ``RETRY_HOURS``.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.integrations.models import Notification

logger = logging.getLogger(__name__)

RETRY_HOURS = 48
BATCH = 200


def notify_user(user, *, subject: str, message: str) -> Notification:
    return Notification.objects.create(
        user=user, notification_type="email", subject=subject, message=message
    )


def deliver_pending(*, now=None, limit: int = BATCH) -> tuple[int, int]:
    """E-mail unsent notifications from the last ``RETRY_HOURS``; return (sent, failed)."""
    now = now or timezone.now()
    pending = (
        Notification.objects.filter(
            notification_type="email",
            sent_at__isnull=True,
            created_at__gte=now - timedelta(hours=RETRY_HOURS),
        )
        .select_related("user")
        .order_by("created_at")[:limit]
    )
    sent = failed = 0
    for notification in pending:
        if not notification.user.email:
            continue
        try:
            send_mail(
                notification.subject,
                notification.message,
                settings.DEFAULT_FROM_EMAIL,
                [notification.user.email],
            )
        except Exception:
            failed += 1
            logger.exception(
                "Notification e-mail failed", extra={"notification_id": notification.pk}
            )
            continue
        Notification.objects.filter(pk=notification.pk).update(sent_at=timezone.now())
        sent += 1
    return sent, failed
