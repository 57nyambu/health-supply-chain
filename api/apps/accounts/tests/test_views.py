import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, WorkerProfile
from apps.audit.models import AuditEvent
from apps.facilities.tests.factories import FacilityFactory
from apps.warehouses.tests.factories import WarehouseFactory

pytestmark = pytest.mark.django_db

STRONG = "correct-horse-battery-staple-42"


def test_admin_lists_only_users_linked_to_the_facility(api_as, facility, make_user, grant):
    admin = api_as("facility_admin", facility=facility)
    local = make_user()
    grant(local, "cashier", facility)
    profiled = make_user()
    WorkerProfile.objects.create(user=profiled, branch=facility.branch)
    stranger = make_user()
    grant(stranger, "cashier", FacilityFactory.create())
    emails = {row["email"] for row in admin.get("/api/v1/accounts/users/").json()["results"]}
    assert {local.email, profiled.email, admin.user.email} == emails
    assert admin.get(f"/api/v1/accounts/users/{stranger.pk}/").status_code == 404


def test_create_validates_password_links_profile_and_audits(api_as, facility):
    admin = api_as("facility_admin", facility=facility)
    weak = admin.post(
        "/api/v1/accounts/users/", {"email": "new@example.test", "password": "123"}, format="json"
    )
    assert weak.status_code == 400
    assert weak.json()["errors"][0]["field"] == "password"
    created = admin.post(
        "/api/v1/accounts/users/", {"email": "new@example.test", "password": STRONG}, format="json"
    )
    assert created.status_code == 201
    user = User.objects.get(email="new@example.test")
    assert user.check_password(STRONG)
    assert user.profile.branch == facility.branch
    assert AuditEvent.objects.filter(action="admin.user.created", resource_id=str(user.pk)).exists()


def test_update_is_audited_and_delete_is_refused(api_as, facility, make_user, grant):
    admin = api_as("facility_admin", facility=facility)
    clerk = make_user(first_name="Old")
    grant(clerk, "cashier", facility)
    assert (
        admin.patch(
            f"/api/v1/accounts/users/{clerk.pk}/", {"first_name": "New"}, format="json"
        ).status_code
        == 200
    )
    assert AuditEvent.objects.get(action="admin.user.updated").detail == {"fields": ["first_name"]}
    assert admin.delete(f"/api/v1/accounts/users/{clerk.pk}/").status_code in (403, 405)
    assert User.objects.filter(pk=clerk.pk).exists()


def test_profiles_are_scoped_and_updates_audited(api_as, facility, make_user):
    admin = api_as("facility_admin", facility=facility)
    clerk = make_user()
    profile = WorkerProfile.objects.create(user=clerk, branch=facility.branch)
    WorkerProfile.objects.create(user=make_user(), branch=FacilityFactory.create().branch)
    assert len(admin.get("/api/v1/accounts/profiles/").json()["results"]) == 1
    store = WarehouseFactory.create(branch=facility.branch)
    assert (
        admin.patch(
            f"/api/v1/accounts/profiles/{profile.pk}/", {"warehouse": store.pk}, format="json"
        ).status_code
        == 200
    )
    assert AuditEvent.objects.filter(action="admin.user.profile_updated").exists()


def test_me_is_available_to_any_signed_in_user(api_as, facility):
    client = api_as("cashier", facility=facility)
    assert client.get("/api/v1/accounts/users/me/").json()["email"] == client.user.email
    assert client.get("/api/v1/accounts/users/").status_code == 403


def test_legacy_jwt_login_endpoint_is_gone(make_user):
    """Browsers sign in at /api/v1/auth/login (session); the token endpoint was removed (P1-UAC-04)."""
    user = make_user(password=STRONG)
    response = APIClient().post(
        "/api/v1/accounts/auth/login/", {"email": user.email, "password": STRONG}, format="json"
    )
    assert response.status_code == 404
