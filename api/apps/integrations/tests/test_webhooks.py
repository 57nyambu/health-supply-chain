import hmac

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.integrations import webhooks
from apps.integrations.models import WebhookInbox
from apps.integrations.tasks import process_webhooks

pytestmark = pytest.mark.django_db
SECRET = "synthetic-path-token"


@pytest.fixture(autouse=True)
def isolated_providers(monkeypatch):
    monkeypatch.setattr(webhooks, "_PROVIDERS", {})


@pytest.fixture
def handled():
    seen: list[str] = []

    def handle(row):
        if row.reference == "boom":
            raise RuntimeError("handler failed")
        seen.append(row.reference)

    webhooks.register(
        "synthetic",
        verify=lambda request, token: hmac.compare_digest(token, SECRET),
        reference=lambda payload: payload.get("TransID"),
        handle=handle,
    )
    return seen


def post(body, token=SECRET, provider="synthetic"):
    return APIClient().post(
        f"/api/v1/hooks/{provider}/{token}/",
        body,
        format="json",
        HTTP_AUTHORIZATION="Bearer synthetic",
    )


def test_notifications_are_stored_encrypted_and_answered_at_once(handled):
    response = post({"TransID": "SYN123", "MSISDN": "254708374149", "Amount": "100.00"})
    assert response.status_code == 200 and response.json() == {"status": "accepted"}
    row = WebhookInbox.objects.get()
    assert (row.provider, row.reference, row.status) == ("synthetic", "SYN123", "received")
    assert row.headers["Authorization"] == "[redacted]"
    assert handled == []  # nothing processed in the request
    with connection.cursor() as cursor:
        cursor.execute("SELECT raw_body FROM integrations_webhookinbox")
        assert "254708374149" not in cursor.fetchone()[0]


def test_failed_verification_and_unknown_providers(handled):
    assert post({"TransID": "SYN1"}, token="wrong").status_code == 403
    assert WebhookInbox.objects.get().status == "rejected"
    assert post({"TransID": "SYN1"}, provider="nobody").status_code == 404
    assert process_webhooks() == {"processed": 0, "failed": 0}


def test_duplicates_are_kept_but_handled_once(handled):
    post({"TransID": "SYN9"})
    post({"TransID": "SYN9"})
    assert list(WebhookInbox.objects.values_list("status", flat=True)) == ["received", "duplicate"]
    assert process_webhooks() == {"processed": 1, "failed": 0}
    assert handled == ["SYN9"]
    assert webhooks.process_pending() == (0, 0)


def test_handler_failures_are_retried_then_parked(handled, monkeypatch):
    post({"TransID": "boom"})
    assert webhooks.process_pending() == (0, 1)
    row = WebhookInbox.objects.get()
    assert (row.status, row.attempts, row.last_error) == ("failed", 1, "RuntimeError")
    monkeypatch.setattr(webhooks, "MAX_ATTEMPTS", 2)
    webhooks.process_pending()
    assert WebhookInbox.objects.get().status == "parked"
    assert webhooks.process_pending() == (0, 0)


def test_providers_register_once():
    def verify(request, token):
        return True

    webhooks.register("x", verify=verify, reference=lambda p: None, handle=lambda r: None)
    with pytest.raises(ValueError, match="already registered"):
        webhooks.register(
            "x", verify=lambda r, t: False, reference=lambda p: None, handle=lambda r: None
        )
