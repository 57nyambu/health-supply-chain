import pytest

from apps.access.models import RoleAssignment
from apps.audit.models import AuditEvent
from apps.facilities.tests.factories import FacilityFactory

pytestmark = pytest.mark.django_db
URL = "/api/v1/access/"


@pytest.fixture
def admin(api_as, facility):
    return api_as("facility_admin", facility=facility)


def test_roles_are_listed_with_their_permissions(admin):
    roles = {row["code"]: row for row in admin.get(f"{URL}roles/").json()}
    assert (
        "receptionist" in roles
        and "patients.patient.search" in roles["receptionist"]["permissions"]
    )
    assert roles["facility_admin"]["privileged"] is True


def test_role_reads_need_the_permission(api_as, facility):
    assert api_as("receptionist", facility=facility).get(f"{URL}roles/").status_code == 403


def test_grant_list_and_revoke_a_role(admin, facility, make_user):
    nurse = make_user()
    response = admin.post(
        f"{URL}assignments/",
        {"user": nurse.pk, "role": "nurse", "reason": "New hire"},
        format="json",
    )
    assert response.status_code == 201, response.json()
    assignment = response.json()
    assert assignment["status"] == "active" and assignment["granted_by"] == admin.user.pk
    listed = admin.get(f"{URL}assignments/", {"user": nurse.pk}).json()["results"]
    assert [row["id"] for row in listed] == [assignment["id"]]
    revoked = admin.post(
        f"{URL}assignments/{assignment['id']}/revoke/",
        {"reason": "Left the facility"},
        format="json",
    )
    assert revoked.status_code == 200 and revoked.json()["status"] == "revoked"
    assert {"access.assignment.granted", "access.assignment.revoked"} <= set(
        AuditEvent.objects.values_list("action", flat=True)
    )


def test_privileged_roles_wait_for_a_second_admin(admin, api_as, facility, make_user):
    target = make_user()
    pending = admin.post(
        f"{URL}assignments/",
        {"user": target.pk, "role": "facility_admin", "reason": "Cover"},
        format="json",
    )
    assert pending.status_code == 201 and pending.json()["status"] == "pending_approval"
    approval = pending.json()["approval"]
    assert (
        admin.post(f"{URL}approvals/{approval}/approve/").status_code == 403
    )  # maker cannot check
    second = api_as("facility_admin", facility=facility)
    decided = second.post(
        f"{URL}approvals/{approval}/approve/", {"comment": "Confirmed with HR"}, format="json"
    )
    assert decided.status_code == 200 and decided.json()["status"] == "approved"
    assert RoleAssignment.objects.get(pk=pending.json()["id"]).status == "active"


def test_rejecting_an_approval(admin, api_as, facility, make_user):
    approval = admin.post(
        f"{URL}assignments/",
        {"user": make_user().pk, "role": "facility_admin", "reason": "x"},
        format="json",
    ).json()["approval"]
    second = api_as("facility_admin", facility=facility)
    assert (
        second.post(
            f"{URL}approvals/{approval}/reject/", {"comment": "Not agreed"}, format="json"
        ).json()["status"]
        == "rejected"
    )


def test_assignments_are_scoped_to_the_facility(admin, api_as, make_user):
    other = FacilityFactory.create()
    elsewhere = api_as("facility_admin", facility=other)
    created = elsewhere.post(
        f"{URL}assignments/",
        {"user": make_user().pk, "role": "nurse", "reason": "x"},
        format="json",
    ).json()
    assert admin.get(f"{URL}assignments/{created['id']}/").status_code == 404
    assert (
        admin.post(
            f"{URL}assignments/", {"user": make_user().pk, "role": "nurse"}, format="json"
        ).status_code
        == 400
    )


def test_the_inbox_shows_only_requests_the_user_made_or_may_decide(
    admin, api_as, facility, make_user
):
    approval = admin.post(
        f"{URL}assignments/",
        {"user": make_user().pk, "role": "facility_admin", "reason": "x"},
        format="json",
    ).json()["approval"]
    nurse = api_as("nurse", facility=facility)
    assert nurse.get(f"{URL}approvals/").json()["results"] == []
    assert nurse.post(f"{URL}approvals/{approval}/approve/").status_code == 404
    assert [row["id"] for row in admin.get(f"{URL}approvals/").json()["results"]] == [approval]
