import gzip
import importlib
from datetime import timedelta

import pytest
import time_machine
from django.apps import apps as live_apps
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import passwords
from apps.accounts.models import User, UserSession
from apps.audit.models import AuditEvent

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DPA-06")]

PASSWORD = "correct-horse-battery-staple-42"


@pytest.fixture
def staff(make_user, facility, grant):
    user = make_user(password=PASSWORD)
    grant(user, "store_keeper", facility)
    return user


def browser():
    """A client that enforces CSRF like a real browser session."""
    return APIClient(enforce_csrf_checks=True)


def sign_in(client, email, password=PASSWORD):
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return client.post(
        "/api/v1/auth/login",
        {"email": email, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )


def actions():
    return list(AuditEvent.objects.order_by("ts").values_list("action", flat=True))


# --- sessions, CSRF, no bearer tokens ---------------------------------------------------------


def test_login_creates_an_httponly_lax_session(staff, facility):
    client = browser()
    response = sign_in(client, staff.email)
    assert response.status_code == 200
    body = response.json()
    assert body["facility"]["id"] == facility.pk
    assert "inventory.store.read" in body["permissions"]
    assert body["roles"] == ["store_keeper"]
    cookie = response.cookies["sessionid"]
    assert cookie["httponly"] and cookie["samesite"] == "Lax"
    assert "access" not in body and "refresh" not in body
    assert client.get("/api/v1/warehouses/warehouses/").status_code == 200
    assert UserSession.objects.filter(user=staff, ended_at__isnull=True).count() == 1


def test_login_requires_the_csrf_token(staff):
    client = browser()
    client.get("/api/v1/auth/csrf")
    response = client.post(
        "/api/v1/auth/login", {"email": staff.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_failed"


def test_login_from_an_untrusted_origin_is_refused(staff, settings):
    settings.CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:3000"]
    client = browser()
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    body = {"email": staff.email, "password": PASSWORD}
    foreign = client.post(
        "/api/v1/auth/login",
        body,
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="http://evil.example.test",
    )
    assert foreign.status_code == 403 and foreign.json()["code"] == "csrf_failed"
    trusted = client.post(
        "/api/v1/auth/login",
        body,
        format="json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="http://127.0.0.1:3000",
    )
    assert trusted.status_code == 200


def test_unsafe_requests_need_csrf_once_signed_in(staff, facility):
    client = browser()
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    sign_in(client, staff.email)
    token = client.cookies["csrftoken"].value
    refused = client.post("/api/v1/me/facility", {"facility": facility.pk}, format="json")
    assert refused.status_code == 403
    accepted = client.post(
        "/api/v1/me/facility", {"facility": facility.pk}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert accepted.status_code == 200


def test_bearer_tokens_are_not_accepted(staff):
    access = str(RefreshToken.for_user(staff).access_token)
    client = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get("/api/v1/me").status_code in (401, 403)


def test_legacy_refresh_tokens_are_revoked_by_migration(staff):
    migration = importlib.import_module("apps.accounts.migrations.0006_revoke_legacy_jwt")
    RefreshToken.for_user(staff)
    RefreshToken.for_user(staff)
    migration.blacklist_all(live_apps, None)
    migration.blacklist_all(live_apps, None)  # idempotent
    assert OutstandingToken.objects.count() == 2
    assert BlacklistedToken.objects.count() == 2


def test_logout_ends_the_session(staff):
    client = browser()
    sign_in(client, staff.email)
    token = client.cookies["csrftoken"].value
    assert client.post("/api/v1/auth/logout", HTTP_X_CSRFTOKEN=token).status_code == 204
    assert client.get("/api/v1/me").status_code in (401, 403)
    assert UserSession.objects.get(user=staff).end_reason == "logout"
    assert "auth.logout" in actions()


# --- passwords ---------------------------------------------------------------------------------------


def test_passwords_are_hashed_with_argon2id(make_user):
    user = make_user(password=PASSWORD)
    assert user.password.startswith("argon2$argon2id$")


def test_legacy_pbkdf2_hashes_are_upgraded_at_sign_in(make_user, facility, grant):
    user = make_user()
    User.objects.filter(pk=user.pk).update(password=make_password(PASSWORD, hasher="pbkdf2_sha256"))
    grant(user, "cashier", facility)
    assert sign_in(browser(), user.email).status_code == 200
    user.refresh_from_db()
    assert user.password.startswith("argon2$argon2id$")


@pytest.mark.parametrize(
    ("candidate", "message"),
    [
        ("Short-pass1", "at least 12"),
        ("password1234", "too common"),
        ("123456789012345", "entirely numeric"),
    ],
)
def test_password_policy(candidate, message):
    with pytest.raises(ValidationError, match=message):
        validate_password(candidate)


def test_twelve_character_strong_password_is_accepted():
    validate_password("kiwi-mango-77!")


def test_extra_breached_list_is_checked(settings, tmp_path_factory):
    path = tmp_path_factory.mktemp("lists") / "breached.txt.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("Nairobi-2026-Sunrise\n")
    settings.BREACHED_PASSWORDS_FILE = str(path)
    passwords._extra_breached.cache_clear()
    try:
        with pytest.raises(ValidationError, match="breached"):
            validate_password("nairobi-2026-sunrise")
    finally:
        passwords._extra_breached.cache_clear()


# --- lockout -----------------------------------------------------------------------------------------


def test_unknown_user_and_wrong_password_look_the_same(staff):
    unknown = sign_in(browser(), "nobody@example.test")
    wrong = sign_in(browser(), staff.email, "wrong-password-123")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["code"] == wrong.json()["code"] == "invalid_credentials"


def test_progressive_delay_then_lock_then_admin_unlock(staff, facility, api_as):
    start = timezone.now()
    with time_machine.travel(start, tick=False) as clock:
        for _ in range(5):
            assert sign_in(browser(), staff.email, "wrong-password-123").status_code == 401
        throttled = sign_in(browser(), staff.email, PASSWORD)
        assert throttled.status_code == 429
        assert throttled.json()["code"] == "login_throttled"
        assert throttled["Retry-After"] == "1"
        for _ in range(5):
            clock.shift(timedelta(seconds=61))
            assert sign_in(browser(), staff.email, "wrong-password-123").status_code == 401
        clock.shift(timedelta(seconds=61))
        staff.refresh_from_db()
        assert staff.account_locked and staff.failed_login_attempts == 10
        assert sign_in(browser(), staff.email, "wrong-password-123").status_code == 401
        locked = sign_in(browser(), staff.email, PASSWORD)
        assert locked.status_code == 423
        assert locked.json()["code"] == "account_locked"

    admin = api_as("facility_admin", facility=facility)
    assert admin.post(f"/api/v1/accounts/users/{staff.pk}/unlock/").status_code == 200
    assert sign_in(browser(), staff.email).status_code == 200
    log = actions()
    for action in (
        "auth.login.failed",
        "auth.login.throttled",
        "auth.account.locked",
        "auth.account.unlocked",
        "auth.login.succeeded",
    ):
        assert action in log
    assert AuditEvent.objects.get(action="auth.account.locked").severity == "high"


def test_a_successful_login_resets_the_failure_count(staff):
    for _ in range(3):
        sign_in(browser(), staff.email, "wrong-password-123")
    assert sign_in(browser(), staff.email).status_code == 200
    staff.refresh_from_db()
    assert staff.failed_login_attempts == 0


def test_unlock_needs_the_permission(staff, facility, api_as):
    clerk = api_as("cashier", facility=facility)
    assert clerk.post(f"/api/v1/accounts/users/{staff.pk}/unlock/").status_code == 403


# --- idle and absolute expiry ------------------------------------------------------------------------


def test_idle_sessions_expire_on_the_server(staff):
    start = timezone.now()
    with time_machine.travel(start, tick=False) as clock:
        client = browser()
        sign_in(client, staff.email)
        clock.shift(timedelta(minutes=29))
        assert client.get("/api/v1/me").status_code == 200
        clock.shift(timedelta(minutes=31))
        response = client.get("/api/v1/me")
        assert response.status_code == 401
        assert response.json()["code"] == "session_expired"
    assert UserSession.objects.get(user=staff).end_reason == "idle"
    assert "auth.session.expired_idle" in actions()


def test_absolute_expiry_even_when_active(staff, facility):
    facility.workstation_lock_minutes = 30  # stay unlocked between the 20-minute steps
    facility.save()
    start = timezone.now()
    with time_machine.travel(start, tick=False) as clock:
        client = browser()
        sign_in(client, staff.email)
        for _ in range(12 * 3):  # active every 20 minutes for 12 hours
            clock.shift(timedelta(minutes=20))
            if client.get("/api/v1/me").status_code != 200:
                break
        clock.shift(timedelta(minutes=20))
        assert client.get("/api/v1/me").json()["code"] == "session_expired"
    assert UserSession.objects.get(user=staff).end_reason == "absolute"


def test_facility_sets_shorter_idle_limit(staff, facility):
    facility.session_idle_minutes = 10
    facility.save()
    start = timezone.now()
    with time_machine.travel(start, tick=False) as clock:
        client = browser()
        sign_in(client, staff.email)
        clock.shift(timedelta(minutes=11))
        assert client.get("/api/v1/me").status_code == 401


# --- me, password change, forced change, admin reset --------------------------------------------------


def test_me_lists_facilities_and_switching_needs_a_role_there(staff, facility, grant):
    from apps.facilities.tests.factories import FacilityFactory

    second, stranger = FacilityFactory.create(), FacilityFactory.create()
    grant(staff, "report_viewer", second)
    client = APIClient()
    client.force_login(staff)
    me = client.get("/api/v1/me").json()
    assert me["facility"] is None and len(me["facilities"]) == 2
    switched = client.post("/api/v1/me/facility", {"facility": second.pk}, format="json").json()
    assert switched["facility"]["id"] == second.pk and switched["roles"] == ["report_viewer"]
    assert (
        client.post("/api/v1/me/facility", {"facility": stranger.pk}, format="json").status_code
        == 403
    )
    assert "auth.facility.switched" in actions()


def test_password_change(staff):
    client = APIClient()
    client.force_login(staff)
    wrong = client.post(
        "/api/v1/auth/password",
        {"current_password": "nope", "new_password": "kiwi-mango-77!"},
        format="json",
    )
    assert wrong.status_code == 400
    same = client.post(
        "/api/v1/auth/password",
        {"current_password": PASSWORD, "new_password": PASSWORD},
        format="json",
    )
    assert same.status_code == 400
    weak = client.post(
        "/api/v1/auth/password",
        {"current_password": PASSWORD, "new_password": "short"},
        format="json",
    )
    assert weak.status_code == 400
    ok = client.post(
        "/api/v1/auth/password",
        {"current_password": PASSWORD, "new_password": "kiwi-mango-77!"},
        format="json",
    )
    assert ok.status_code == 204
    staff.refresh_from_db()
    assert staff.check_password("kiwi-mango-77!") and staff.password_changed_at is not None
    assert {"auth.password.change_failed", "auth.password.changed"} <= set(actions())


def test_admin_reset_forces_a_password_change(staff, facility, api_as):
    victim_session = APIClient()
    victim_session.force_login(staff)
    admin = api_as("facility_admin", facility=facility)
    temporary = admin.post(f"/api/v1/accounts/users/{staff.pk}/reset-credentials/").json()[
        "temporary_password"
    ]
    assert victim_session.get("/api/v1/me").status_code in (401, 403)  # sessions ended
    client = browser()
    assert sign_in(client, staff.email, temporary).json()["must_change_password"] is True
    blocked = client.get("/api/v1/warehouses/warehouses/")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "password_change_required"
    assert client.get("/api/v1/me").status_code == 200
    token = client.cookies["csrftoken"].value
    client.post(
        "/api/v1/auth/password",
        {"current_password": temporary, "new_password": "kiwi-mango-77!"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert client.get("/api/v1/warehouses/warehouses/").status_code == 200
    assert "admin.user.credentials_reset" in actions()


def test_admin_cannot_reset_own_credentials(facility, api_as):
    admin = api_as("facility_admin", facility=facility)
    assert (
        admin.post(f"/api/v1/accounts/users/{admin.user.pk}/reset-credentials/").status_code == 400
    )


def test_deactivate_through_the_api(staff, facility, api_as):
    admin = api_as("facility_admin", facility=facility)
    response = admin.post(
        f"/api/v1/accounts/users/{staff.pk}/deactivate/", {"reason": "Left"}, format="json"
    )
    assert response.status_code == 200
    staff.refresh_from_db()
    assert staff.is_active is False
    assert sign_in(browser(), staff.email).status_code == 401
