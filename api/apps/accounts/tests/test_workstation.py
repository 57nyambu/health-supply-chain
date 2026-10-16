from datetime import timedelta

import pytest
import time_machine
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserSession, WorkstationSession
from apps.audit.models import AuditEvent

pytestmark = pytest.mark.django_db

PASSWORD = "correct-horse-battery-staple-42"
PIN_A, PIN_B = "482915", "730264"
CATEGORY = "/api/v1/products/categories/"


def token(client):
    if "csrftoken" not in client.cookies:
        client.get("/api/v1/auth/csrf")
    return client.cookies["csrftoken"].value


def post(client, url, data=None):
    return client.post(url, data or {}, format="json", HTTP_X_CSRFTOKEN=token(client))


def sign_in(client, user):
    return post(client, "/api/v1/auth/login", {"email": user.email, "password": PASSWORD})


@pytest.fixture
def keepers(make_user, facility, grant):
    a, b = make_user(password=PASSWORD), make_user(password=PASSWORD)
    for user in (a, b):
        grant(user, "store_keeper", facility)
    return a, b


def set_pin(client, pin):
    return post(client, "/api/v1/auth/pin", {"pin": pin, "password": PASSWORD})


def ready(user, pin):
    """A workstation where ``user`` signed in fully and set a PIN."""
    client = APIClient(enforce_csrf_checks=True)
    sign_in(client, user)
    assert set_pin(client, pin).status_code == 204
    return client


def test_pins_are_hashed_and_validated(keepers):
    a, _ = keepers
    client = APIClient(enforce_csrf_checks=True)
    sign_in(client, a)
    for bad in ("12345", "abcdef", "111111", "123456", "987654"):
        assert set_pin(client, bad).status_code == 400
    assert post(client, "/api/v1/auth/pin", {"pin": PIN_A, "password": "wrong"}).status_code == 400
    assert set_pin(client, PIN_A).status_code == 204
    a.refresh_from_db()
    assert a.pin_hash.startswith("argon2$argon2id$") and PIN_A not in a.pin_hash


def test_workstation_locks_after_idle_and_unlocks_with_pin(keepers):
    a, _ = keepers
    start = timezone.now()
    with time_machine.travel(start, tick=False) as clock:
        client = ready(a, PIN_A)
        clock.shift(timedelta(minutes=4))
        assert client.get(CATEGORY).status_code == 200
        clock.shift(timedelta(minutes=6))
        locked = client.get(CATEGORY)
        assert locked.status_code == 423 and locked.json()["code"] == "workstation_locked"
        assert client.get("/api/v1/me").json()["workstation"]["locked"] is True
        assert (
            post(client, "/api/v1/auth/unlock", {"pin": "000001"}).json()["code"] == "invalid_pin"
        )
        assert post(client, "/api/v1/auth/unlock", {"pin": PIN_A}).status_code == 200
        assert client.get(CATEGORY).status_code == 200
    log = list(AuditEvent.objects.values_list("action", flat=True))
    assert {"auth.workstation.locked", "auth.pin.failed", "auth.workstation.unlocked"} <= set(log)


def test_lock_minutes_follow_the_facility_setting(keepers, facility):
    facility.workstation_lock_minutes = 2
    facility.save()
    a, _ = keepers
    start = timezone.now()
    with time_machine.travel(start, tick=False) as clock:
        client = ready(a, PIN_A)
        clock.shift(timedelta(minutes=3))
        assert client.get(CATEGORY).status_code == 423


def test_manual_lock(keepers):
    client = ready(keepers[0], PIN_A)
    assert post(client, "/api/v1/auth/lock").json()["workstation"]["locked"] is True
    assert post(client, CATEGORY, {"name": "Antibiotics"}).status_code == 423


def test_switch_user_keeps_the_device_but_attributes_actions_to_the_new_user(keepers):
    a, b = keepers
    device = ready(b, PIN_B)  # B signed in fully on this workstation earlier
    workstation = device.cookies["workstation_id"].value
    post(device, "/api/v1/auth/logout")
    sign_in(device, a)
    set_pin(device, PIN_A)
    assert post(device, CATEGORY, {"name": "By A"}).status_code == 201
    post(device, "/api/v1/auth/lock")

    switched = post(device, "/api/v1/auth/switch", {"email": b.email, "pin": PIN_B})
    assert switched.status_code == 200
    assert switched.json()["email"] == b.email
    assert device.cookies["workstation_id"].value == workstation  # same device
    assert post(device, CATEGORY, {"name": "By B"}).status_code == 201

    created = list(AuditEvent.objects.filter(action="inventory.category.created").order_by("ts"))
    assert [event.actor_id for event in created] == [a.pk, b.pk]
    device_id = workstation.split(":")[0]  # the cookie is signed: "<id>:<signature>"
    assert {event.workstation_id for event in created} == {device_id}
    assert UserSession.objects.filter(user=a, end_reason="switched").exists()
    assert AuditEvent.objects.filter(action="auth.workstation.switched_in", actor_id=b.pk).exists()


def test_switch_needs_a_recent_full_sign_in_on_this_workstation(keepers):
    a, b = keepers
    ready(b, PIN_B)  # B signed in on another device only
    device = ready(a, PIN_A)
    post(device, "/api/v1/auth/lock")
    response = post(device, "/api/v1/auth/switch", {"email": b.email, "pin": PIN_B})
    assert response.status_code == 401 and response.json()["code"] == "full_login_required"


def test_pin_window_is_twelve_hours(keepers, facility):
    facility.session_absolute_hours = 24
    facility.workstation_lock_minutes = 30
    facility.session_idle_minutes = 120
    facility.save()
    _a, b = keepers
    start = timezone.now()
    with time_machine.travel(start, tick=False) as clock:
        device = ready(b, PIN_B)
        post(device, "/api/v1/auth/logout")
        clock.shift(timedelta(hours=12, minutes=1))
        response = post(device, "/api/v1/auth/switch", {"email": b.email, "pin": PIN_B})
        assert response.json()["code"] == "full_login_required"


def test_five_wrong_pins_force_a_full_sign_in(keepers):
    a, _ = keepers
    client = ready(a, PIN_A)
    post(client, "/api/v1/auth/lock")
    for _ in range(4):
        assert (
            post(client, "/api/v1/auth/unlock", {"pin": "000001"}).json()["code"] == "invalid_pin"
        )
    fifth = post(client, "/api/v1/auth/unlock", {"pin": "000001"})
    assert fifth.json()["code"] == "full_login_required"
    assert client.get("/api/v1/me").status_code in (401, 403)  # session ended
    assert not WorkstationSession.objects.filter(user=a, ended_at__isnull=True).exists()
    assert AuditEvent.objects.get(action="auth.pin.locked_out").severity == "high"
    again = ready(a, PIN_A)  # a full sign-in restores PIN use
    post(again, "/api/v1/auth/lock")
    assert post(again, "/api/v1/auth/unlock", {"pin": PIN_A}).status_code == 200


def test_unknown_users_cannot_switch_in(keepers):
    device = ready(keepers[0], PIN_A)
    post(device, "/api/v1/auth/lock")
    response = post(device, "/api/v1/auth/switch", {"email": "nobody@example.test", "pin": PIN_A})
    assert response.json()["code"] == "invalid_pin"


def test_unlock_without_a_pin_needs_the_password(keepers):
    a, _ = keepers
    client = APIClient(enforce_csrf_checks=True)
    sign_in(client, a)
    post(client, "/api/v1/auth/lock")
    assert (
        post(client, "/api/v1/auth/unlock", {"pin": PIN_A}).json()["code"] == "full_login_required"
    )
    assert User.objects.get(pk=a.pk).pin_hash == ""
