"""Staff notifications (DESIGN §14): stored, then e-mailed. Never put clinical details in bodies."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.integrations.models import Notification

logger = logging.getLogger(__name__)


def notify_user(user, *, subject: str, message: str) -> Notification:
    notification = Notification.objects.create(
        user=user, notification_type="email", subject=subject, message=message
    )
    if user.email:
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception:
            logger.exception(
                "Notification e-mail failed", extra={"notification_id": notification.pk}
            )
            return notification
        Notification.objects.filter(pk=notification.pk).update(sent_at=timezone.now())
    return notification
