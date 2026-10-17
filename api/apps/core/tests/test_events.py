import pytest
from django.db import transaction

from apps.core import events
from apps.core.models import EventDelivery, OutboxEvent
from apps.core.tasks import relay_outbox

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated_consumers(monkeypatch):
    monkeypatch.setattr(events, "_CONSUMERS", {})


def emit(topic="test.thing.happened", **payload):
    with transaction.atomic():
        return events.emit(topic, aggregate=("test.thing", "42"), payload=payload, facility=7)


def test_emit_records_the_event_in_the_callers_transaction():
    event = emit(visit_id="v-1", amount="100.00")
    assert (event.topic, event.aggregate_type, event.aggregate_id, event.facility_id) == (
        "test.thing.happened",
        "test.thing",
        "42",
        7,
    )
    assert event.payload == {"visit_id": "v-1", "amount": "100.00"}
    with transaction.atomic():
        try:
            events.emit("test.rolled.back", aggregate=("test.thing", "43"))
            raise RuntimeError("abort")
        except RuntimeError:
            transaction.set_rollback(True)
    assert not OutboxEvent.objects.filter(topic="test.rolled.back").exists()


@pytest.mark.django_db(transaction=True)
def test_emit_needs_the_transaction_that_makes_the_change():
    with pytest.raises(events.EventError, match="inside the transaction"):
        events.emit("test.thing.happened", aggregate=("test.thing", "1"))


def test_emit_refuses_personal_data():
    for payload in (
        {"patient_name": "x"},
        {"lines": [{"phone": "x"}]},
        {"meta": {"national_id": "x"}},
    ):
        with pytest.raises(events.EventError, match="personal data"), transaction.atomic():
            events.emit("test.thing.happened", aggregate=("test.thing", "1"), payload=payload)


def test_relay_delivers_each_event_to_each_consumer_once():
    seen: list[tuple[str, str]] = []

    @events.consumer("test.thing.happened", name="first")
    def first(event):
        seen.append(("first", event.aggregate_id))

    @events.consumer("test.thing.happened", name="second")
    def second(event):
        seen.append(("second", event.aggregate_id))

    event = emit()
    emit("test.nobody.listens")
    assert relay_outbox() == {"delivered": 2, "failed": 0}
    assert sorted(seen) == [("first", "42"), ("second", "42")]
    assert events.relay() == (0, 0)
    assert OutboxEvent.objects.filter(relayed_at__isnull=True).count() == 0
    assert EventDelivery.objects.filter(event=event, delivered_at__isnull=False).count() == 2


def test_a_failing_consumer_is_retried_then_parked(monkeypatch):
    calls = {"n": 0}

    @events.consumer("test.thing.happened", name="flaky")
    def flaky(event):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("down")

    event = emit()
    assert events.relay() == (0, 1)
    assert OutboxEvent.objects.get(pk=event.pk).relayed_at is None
    assert events.relay() == (1, 0)
    assert EventDelivery.objects.get(event=event).attempts == 1

    @events.consumer("test.broken", name="broken")
    def broken(event):
        raise ValueError("always")

    monkeypatch.setattr(events, "MAX_ATTEMPTS", 2)
    stuck = emit("test.broken")
    events.relay()
    events.relay()
    delivery = EventDelivery.objects.get(event=stuck)
    assert (delivery.attempts, delivery.last_error) == (2, "parked:ValueError")
    assert OutboxEvent.objects.get(pk=stuck.pk).relayed_at is not None
    assert events.relay() == (0, 0)


def test_consumer_names_are_unique_per_topic():
    events.consumer("test.thing.happened", name="one")(lambda event: None)
    with pytest.raises(events.EventError, match="already registered"):
        events.consumer("test.thing.happened", name="one")(lambda event: None)
