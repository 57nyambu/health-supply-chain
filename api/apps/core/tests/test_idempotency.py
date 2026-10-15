import threading
from datetime import timedelta

import pytest
import time_machine
from django.db import connection
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.idempotency import _request_hash, purge_expired_records
from apps.core.models import IdempotencyRecord
from apps.core.tests import probe_urls

pytestmark = [pytest.mark.urls("apps.core.tests.probe_urls"), pytest.mark.django_db]

URL = "/api/test/counting/"


@pytest.fixture(autouse=True)
def reset_counter():
    probe_urls.CALLS["count"] = 0


@pytest.fixture
def client():
    return APIClient()


def post(client, key, body, url=URL):
    headers = {"HTTP_IDEMPOTENCY_KEY": key} if key is not None else {}
    return client.post(url, body, format="json", **headers)


def test_replay_returns_the_same_response_and_runs_once(client):
    first = post(client, "key-1", {"amount": "100.00"})
    second = post(client, "key-1", {"amount": "100.00"})
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json() == {"calls": 1, "echo": "100.00"}
    assert second["Idempotent-Replayed"] == "true"
    assert probe_urls.CALLS["count"] == 1


def test_same_key_with_different_body_is_422(client):
    post(client, "key-2", {"amount": "100.00"})
    response = post(client, "key-2", {"amount": "999.00"})
    assert response.status_code == 422
    assert response.json()["code"] == "idempotency_key_reused"
    assert probe_urls.CALLS["count"] == 1


def test_4xx_responses_are_stored_too(client):
    first = post(client, "key-3", {"status": 409})
    second = post(client, "key-3", {"status": 409})
    assert first.status_code == second.status_code == 409
    assert probe_urls.CALLS["count"] == 1


def test_5xx_responses_are_not_stored_so_the_client_may_retry(client):
    post(client, "key-4", {"status": 503})
    post(client, "key-4", {"status": 503})
    assert probe_urls.CALLS["count"] == 2
    assert not IdempotencyRecord.objects.filter(key="key-4").exists()


def test_without_key_each_request_executes(client):
    post(client, None, {"amount": "1"})
    post(client, None, {"amount": "1"})
    assert probe_urls.CALLS["count"] == 2


def test_required_key_missing_is_428(client):
    response = post(client, None, {"amount": "1"}, url="/api/test/required-key/")
    assert response.status_code == 428
    assert response.json()["code"] == "idempotency_key_required"
    assert probe_urls.CALLS["count"] == 0


def test_invalid_key_is_rejected(client):
    response = post(client, "x" * 300, {"amount": "1"})
    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_invalid"


def test_record_expires_after_24_hours(client):
    post(client, "key-5", {"amount": "1"})
    with time_machine.travel(timezone.now() + timedelta(hours=24, minutes=1)):
        response = post(client, "key-5", {"amount": "2"})
        assert response.status_code == 201
        assert purge_expired_records() == 0  # the expired record was replaced, not left behind
    assert probe_urls.CALLS["count"] == 2


def test_purge_deletes_expired_records(client):
    post(client, "key-6", {"amount": "1"})
    with time_machine.travel(timezone.now() + timedelta(hours=25)):
        assert purge_expired_records() == 1


def test_in_progress_key_is_409(client):
    body = b'{"amount":"1"}'
    pending = RequestFactory().post(URL, data=body, content_type="application/json")
    IdempotencyRecord.objects.create(
        principal="anon",
        key="key-7",
        method="POST",
        path=URL,
        request_hash=_request_hash(pending),
        expires_at=timezone.now() + timedelta(hours=1),
    )
    response = client.post(
        URL, data=body, content_type="application/json", HTTP_IDEMPOTENCY_KEY="key-7"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "idempotency_in_progress"
    assert probe_urls.CALLS["count"] == 0


def test_keys_are_scoped_per_principal(client, django_user_model):
    user = django_user_model.objects.create_user(email="clerk@example.test", password="x" * 16)
    other = APIClient()
    other.force_login(user)
    post(client, "shared-key", {"amount": "1"})
    response = post(other, "shared-key", {"amount": "1"})
    assert response.status_code == 201
    assert probe_urls.CALLS["count"] == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_requests_with_one_key_execute_once():
    results = []

    def worker():
        try:
            results.append(post(APIClient(), "race-key", {"amount": "5"}).status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert probe_urls.CALLS["count"] == 1
    assert results.count(201) >= 1
    assert set(results) <= {201, 409}
