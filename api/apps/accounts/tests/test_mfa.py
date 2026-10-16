import time
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pyotp
import pytest
import time_machine
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import MfaDevice, RecoveryCode
from apps.audit.models import AuditEvent

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DPA-06")]

PASSWORD = "correct-horse-battery-staple-42"
USERS = "/api/v1/accounts/users/"


def browser(ip="127.0.0.1"):
    return APIClient(enforce_csrf_checks=True, REMOTE_ADDR=ip)


def csrf(client):
    return (
        client.cookies["csrftoken"].value
        if "csrftoken" in client.cookies
        else client.get("/api/v1/auth/csrf").json()["csrf_token"]
    )


def post(client, url, data=None):
    return client.post(url, data or {}, format="json", HTTP_X_CSRFTOKEN=csrf(client))


def sign_in(client, user):
    client.get("/api/v1/auth/csrf")
    return post(client, "/api/v1/auth/login", {"email": user.email, "password": PASSWORD})


def enrol(client):
    setup = post(client, "/api/v1/auth/mfa/totp/setup").json()
    secret = parse_qs(urlparse(setup["otpauth_uri"]).query)["secret"][0]
    assert secret == setup["secret"]
    confirm = post(client, "/api/v1/auth/mfa/totp/confirm", {"code": pyotp.TOTP(secret).now()})
    assert confirm.status_code == 200, confirm.json()
    return secret, confirm.json()["recovery_codes"]


def next_code(secret):
    """A code for the next 30-second step, so the replay guard sees a new step."""
    return pyotp.TOTP(secret).at(int(time.time()) + 30)


@pytest.fixture
def admin(make_user, facility, grant):
    user = make_user(password=PASSWORD)
    grant(user, "facility_admin", facility)
    return user


@pytest.fixture
def cashier(make_user, facility, grant):
    user = make_user(password=PASSWORD)
    grant(user, "cashier", facility)
    return user


def test_mfa_required_role_reaches_nothing_but_enrolment_until_enrolled(admin):
    client = browser()
    assert sign_in(client, admin).status_code == 200
    blocked = client.get(USERS)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "mfa_enrolment_required"
    me = client.get("/api/v1/me").json()
    assert me["mfa"] == {"enrolled": False, "required": True, "verified": False}
    _secret, codes = enrol(client)
    assert len(codes) == 10 and len(set(codes)) == 10
    assert client.get(USERS).status_code == 200
    assert {"auth.mfa.setup_started", "auth.mfa.enrolled", "auth.mfa.recovery_codes_issued"} <= set(
        AuditEvent.objects.values_list("action", flat=True)
    )


def test_secrets_are_encrypted_and_recovery_codes_hashed(admin):
    client = browser()
    sign_in(client, admin)
    secret, codes = enrol(client)
    with connection.cursor() as cursor:
        cursor.execute("SELECT secret FROM accounts_mfadevice WHERE user_id = %s", [admin.pk])
        raw = cursor.fetchone()[0]
    assert raw.startswith("v1.") and secret not in raw
    stored = set(RecoveryCode.objects.filter(user=admin).values_list("code_hash", flat=True))
    assert not stored & set(codes)


def test_enrolled_users_need_the_second_factor_to_get_a_session(admin):
    first = browser()
    sign_in(first, admin)
    secret, _codes = enrol(first)

    client = browser()
    challenge = sign_in(client, admin)
    assert challenge.json() == {"status": "mfa_required"}
    assert client.get("/api/v1/me").status_code in (401, 403)  # no session yet
    wrong = post(client, "/api/v1/auth/mfa/verify", {"code": "000000"})
    assert wrong.status_code == 401 and wrong.json()["code"] == "invalid_code"
    ok = post(client, "/api/v1/auth/mfa/verify", {"code": next_code(secret)})
    assert ok.status_code == 200
    assert ok.json()["mfa"]["verified"] is True
    assert client.get(USERS).status_code == 200


def test_totp_codes_cannot_be_replayed(admin):
    first = browser()
    sign_in(first, admin)
    secret, _ = enrol(first)
    code = next_code(secret)
    a, b = browser(), browser()
    sign_in(a, admin)
    sign_in(b, admin)
    assert post(a, "/api/v1/auth/mfa/verify", {"code": code}).status_code == 200
    assert post(b, "/api/v1/auth/mfa/verify", {"code": code}).status_code == 401


def test_recovery_codes_work_once(admin):
    first = browser()
    sign_in(first, admin)
    _secret, codes = enrol(first)
    client = browser()
    sign_in(client, admin)
    assert post(client, "/api/v1/auth/mfa/verify", {"recovery_code": codes[0]}).status_code == 200
    again = browser()
    sign_in(again, admin)
    assert post(again, "/api/v1/auth/mfa/verify", {"recovery_code": codes[0]}).status_code == 401
    assert RecoveryCode.objects.filter(user=admin, used_at__isnull=False).count() == 1


def test_regenerating_recovery_codes_revokes_old_ones(admin):
    client = browser()
    sign_in(client, admin)
    _secret, old = enrol(client)
    fresh = post(client, "/api/v1/auth/mfa/recovery-codes").json()["recovery_codes"]
    assert set(fresh).isdisjoint(old)
    other = browser()
    sign_in(other, admin)
    assert post(other, "/api/v1/auth/mfa/verify", {"recovery_code": old[1]}).status_code == 401


def test_pending_login_expires_and_too_many_wrong_codes_reset_it(admin):
    first = browser()
    sign_in(first, admin)
    enrol(first)
    client = browser()
    sign_in(client, admin)
    for _ in range(4):
        assert (
            post(client, "/api/v1/auth/mfa/verify", {"code": "000000"}).json()["code"]
            == "invalid_code"
        )
    assert (
        post(client, "/api/v1/auth/mfa/verify", {"code": "000000"}).json()["code"]
        == "mfa_session_expired"
    )
    late = browser()
    sign_in(late, admin)
    with time_machine.travel(timezone.now() + timedelta(minutes=6)):
        assert (
            post(late, "/api/v1/auth/mfa/verify", {"code": "123456"}).json()["code"]
            == "mfa_session_expired"
        )


def test_outside_the_facility_network_everyone_needs_mfa(cashier):
    inside = browser("127.0.0.1")
    sign_in(inside, cashier)
    assert inside.get("/api/v1/me").json()["mfa"]["required"] is False
    assert inside.get("/api/v1/facilities/departments/").status_code == 403  # policy, not MFA
    assert inside.get("/api/v1/accounts/users/me/").status_code == 200

    outside = browser("203.0.113.9")
    sign_in(outside, cashier)
    response = outside.get("/api/v1/accounts/users/me/")
    assert response.status_code == 403 and response.json()["code"] == "mfa_enrolment_required"


def test_allowlisted_lan_counts_as_inside(cashier, settings):
    settings.FACILITY_NETWORK_ALLOWLIST = ["10.20.0.0/16"]
    client = browser("10.20.3.4")
    sign_in(client, cashier)
    assert client.get("/api/v1/accounts/users/me/").status_code == 200


def test_facility_setting_can_require_mfa_for_everyone(cashier, facility):
    facility.require_mfa_for_all = True
    facility.save()
    client = browser()
    sign_in(client, cashier)
    assert client.get("/api/v1/accounts/users/me/").json()["code"] == "mfa_enrolment_required"
    enrol(client)
    assert client.get("/api/v1/accounts/users/me/").status_code == 200


def test_replacing_a_device_needs_the_current_one(admin):
    first = browser()
    sign_in(first, admin)
    enrol(first)
    assert (
        post(first, "/api/v1/auth/mfa/totp/setup").status_code == 200
    )  # verified session may re-enrol
    attacker = browser()
    sign_in(attacker, admin)  # password only → pending challenge, no session
    assert post(attacker, "/api/v1/auth/mfa/totp/setup").status_code in (401, 403)


def test_confirm_rejects_a_wrong_code(cashier):
    client = browser()
    sign_in(client, cashier)
    post(client, "/api/v1/auth/mfa/totp/setup")
    response = post(client, "/api/v1/auth/mfa/totp/confirm", {"code": "000000"})
    assert response.status_code == 400
    assert not MfaDevice.objects.filter(user=cashier, confirmed_at__isnull=False).exists()


def test_admin_reset_removes_mfa_enrolment(admin, facility, api_as):
    client = browser()
    sign_in(client, admin)
    enrol(client)
    other_admin = api_as("facility_admin", facility=facility)
    other_admin.post(f"/api/v1/accounts/users/{admin.pk}/reset-credentials/")
    assert not MfaDevice.objects.filter(user=admin, removed_at__isnull=True).exists()


def test_dev_bypass_lets_seeded_admins_in_without_a_device_only_in_dev(admin, settings):
    settings.MFA_DEV_BYPASS = True
    settings.DJANGO_ENV = "test"
    client = browser()
    sign_in(client, admin)
    assert client.get(USERS).json()["code"] == "mfa_enrolment_required"  # not dev: no bypass
    settings.DJANGO_ENV = "dev"
    assert client.get(USERS).status_code == 200
    assert client.get("/api/v1/me").json()["mfa"]["required"] is False
    secret, _codes = enrol(client)  # once enrolled, the second factor is asked again
    fresh = browser()
    assert sign_in(fresh, admin).json() == {"status": "mfa_required"}
    assert post(fresh, "/api/v1/auth/mfa/verify", {"code": next_code(secret)}).status_code == 200
