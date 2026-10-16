from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone

from apps.integrations import notify
from apps.integrations.models import Notification
from apps.integrations.tasks import deliver_notifications

pytestmark = pytest.mark.django_db


def test_notify_only_stores_and_the_outbox_sends(make_user):
    user = make_user()
    notice = notify.notify_user(user, subject="Synthetic subject", message="Synthetic body")
    assert notice.sent_at is None and not mail.outbox
    assert deliver_notifications() == {"sent": 1, "failed": 0}
    assert [m.to for m in mail.outbox] == [[user.email]]
    notice.refresh_from_db()
    assert notice.sent_at is not None
    assert notify.deliver_pending() == (0, 0)  # never twice


def test_a_mail_outage_never_blocks_and_is_retried(make_user):
    notice = notify.notify_user(make_user(), subject="Synthetic", message="Synthetic")
    with mock.patch.object(notify, "send_mail", side_effect=ConnectionRefusedError):
        assert notify.deliver_pending() == (0, 1)
    notice.refresh_from_db()
    assert notice.sent_at is None
    assert notify.deliver_pending() == (1, 0)  # next run, server back


def test_old_or_addressless_notices_are_not_retried(make_user):
    stale = notify.notify_user(make_user(), subject="Old", message="Old")
    Notification.objects.filter(pk=stale.pk).update(
        created_at=timezone.now() - timedelta(hours=notify.RETRY_HOURS + 1)
    )
    nobody = make_user()
    nobody.email = ""
    nobody.save(update_fields=["email"])
    notify.notify_user(nobody, subject="No address", message="No address")
    assert notify.deliver_pending() == (0, 0)
    assert not mail.outbox
