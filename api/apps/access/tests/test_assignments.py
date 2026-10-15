import importlib
from datetime import timedelta

import pytest
import time_machine
from django.apps import apps as live_apps
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.access import approvals, policies
from apps.access.assignments import grant_role, revoke_assignment
from apps.access.models import ApprovalRequest, Role, RoleAssignment
from apps.accounts.models import UserSession, WorkerProfile
from apps.accounts.services import deactivate_user
from apps.audit.models import AuditEvent
from apps.facilities.tests.factories import DepartmentFactory, FacilityFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admins(make_user, facility, grant):
    first, second = make_user(), make_user()
    grant(first, "facility_admin", facility)
    grant(second, "facility_admin", facility)
    return first, second


def role(code):
    return Role.objects.get(code=code)


def test_non_privileged_grant_is_active_at_once_and_audited(admins, make_user, facility):
    nurse = make_user()
    assignment = grant_role(
        granted_by=admins[0], user=nurse, role=role("nurse"), facility=facility, reason="New hire"
    )
    assert assignment.status == RoleAssignment.Status.ACTIVE
    assert (
        policies.has_permission(nurse, "clinical.vitals.record", facility=facility) is False
    )  # licence pending
    assert policies.has_permission(nurse, "patients.patient.read", facility=facility)
    event = AuditEvent.objects.get(action="access.assignment.granted")
    assert event.detail == {"user_id": nurse.pk, "role": "nurse", "privileged": False}


def test_privileged_grant_needs_a_second_facility_admin(admins, make_user, facility):
    first, second = admins
    target = make_user()
    assignment = grant_role(
        granted_by=first,
        user=target,
        role=role("medical_superintendent"),
        facility=facility,
        reason="Appointed MS",
    )
    assert assignment.status == RoleAssignment.Status.PENDING_APPROVAL
    assert not policies.has_permission(target, "visits.gate.override", facility=facility)
    request = assignment.approval
    assert request is not None
    with pytest.raises(PermissionDenied, match="own request"):
        approvals.approve(request, approver=first)
    approvals.approve(request, approver=second)
    assignment.refresh_from_db()
    assert assignment.status == RoleAssignment.Status.ACTIVE
    assert assignment.approved_by == second
    assert policies.has_permission(target, "visits.gate.override", facility=facility)


def test_nobody_approves_a_privileged_role_for_themselves(admins, make_user, facility, grant):
    first, second = admins
    request_assignment = grant_role(
        granted_by=first,
        user=second,
        role=role("finance_manager"),
        facility=facility,
        reason="Acting FM",
    )
    request = request_assignment.approval
    assert request is not None
    with pytest.raises(PermissionDenied, match="yourself"):
        approvals.approve(request, approver=second)
    request.refresh_from_db()
    assert request.status == ApprovalRequest.Status.PENDING


def test_granter_needs_assignment_permissions(make_user, facility, grant):
    clerk, target = make_user(), make_user()
    grant(clerk, "receptionist", facility)
    with pytest.raises(PermissionDenied):
        grant_role(
            granted_by=clerk, user=target, role=role("cashier"), facility=facility, reason="x"
        )


def test_grant_needs_permission_in_the_target_facility(admins, make_user):
    with pytest.raises(PermissionDenied):
        grant_role(
            granted_by=admins[0],
            user=make_user(),
            role=role("cashier"),
            facility=FacilityFactory.create(),
            reason="x",
        )


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"role": "public_api_client"}, "role"),
        ({"reason": " "}, "reason"),
        ({"other_department": True}, "department"),
    ],
)
def test_grant_validation(admins, make_user, facility, kwargs, field):
    values = {
        "granted_by": admins[0],
        "user": make_user(),
        "role": role(kwargs.get("role", "cashier")),
        "facility": facility,
        "reason": kwargs.get("reason", "ok"),
    }
    if kwargs.get("other_department"):
        values["department"] = DepartmentFactory.create()
    with pytest.raises(ValidationError) as excinfo:
        grant_role(**values)
    assert field in excinfo.value.message_dict


def test_time_bound_assignment_expires(admins, make_user, facility):
    locum = make_user()
    now = timezone.now()
    grant_role(
        granted_by=admins[0],
        user=locum,
        role=role("cashier"),
        facility=facility,
        reason="Locum",
        valid_from=now,
        valid_to=now + timedelta(days=7),
    )
    assert policies.has_permission(locum, "payments.receive.cash", facility=facility)
    with time_machine.travel(now + timedelta(days=8)):
        assert not policies.has_permission(locum, "payments.receive.cash", facility=facility)
        assert policies.effective_permissions(locum, facility=facility) == set()


def test_revocation_takes_effect_and_is_audited(admins, make_user, facility):
    cashier = make_user()
    assignment = grant_role(
        granted_by=admins[0], user=cashier, role=role("cashier"), facility=facility, reason="x"
    )
    with pytest.raises(ValidationError):
        revoke_assignment(assignment, revoked_by=admins[0], reason="")
    revoke_assignment(assignment, revoked_by=admins[0], reason="Left the facility")
    assert not policies.has_permission(cashier, "payments.receive.cash", facility=facility)
    revoke_assignment(assignment, revoked_by=admins[0], reason="again")  # idempotent
    assert AuditEvent.objects.filter(action="access.assignment.revoked").count() == 1


def test_deactivating_a_user_revokes_all_sessions_immediately(admins, make_user, facility, grant):
    clerk = make_user()
    grant(clerk, "receptionist", facility)
    browser, phone = APIClient(), APIClient()
    browser.force_login(clerk)
    phone.force_login(clerk)
    keys = list(UserSession.objects.filter(user=clerk).values_list("session_key", flat=True))
    assert len(keys) == 2 and Session.objects.filter(session_key__in=keys).count() == 2

    deactivate_user(clerk, by=admins[0], reason="Contract ended", facility=facility)

    assert Session.objects.filter(session_key__in=keys).count() == 0
    assert set(UserSession.objects.filter(user=clerk).values_list("end_reason", flat=True)) == {
        "deactivated"
    }
    response = browser.get("/api/v1/analytics/inventory-alerts/")
    assert response.status_code in (401, 403)
    event = AuditEvent.objects.get(action="admin.user.deactivated")
    assert event.detail == {"sessions_ended": 2}


def test_deactivation_rules(admins, make_user, facility, grant):
    clerk = make_user()
    grant(clerk, "receptionist", facility)
    with pytest.raises(PermissionDenied):
        deactivate_user(admins[0], by=clerk, reason="x", facility=facility)
    with pytest.raises(ValidationError):
        deactivate_user(admins[0], by=admins[0], reason="x", facility=facility)
    with pytest.raises(ValidationError):
        deactivate_user(clerk, by=admins[0], reason=" ", facility=facility)


def test_logout_ends_the_tracked_session(make_user):
    user = make_user()
    client = APIClient()
    client.force_login(user)
    client.logout()
    assert UserSession.objects.get(user=user).end_reason == "logout"


def test_legacy_roles_are_migrated_to_assignments(make_user, facility):
    migration = importlib.import_module("apps.access.migrations.0003_legacy_role_assignments")
    cashier = make_user(role="CASHIER")
    admin = make_user(role="ADMIN")
    orphan = make_user(role="REPORTER")
    WorkerProfile.objects.create(user=cashier, branch=facility.branch)
    WorkerProfile.objects.create(user=admin, branch=facility.branch)
    migration.forwards(live_apps, None)
    migration.forwards(live_apps, None)  # idempotent
    assert policies.role_codes(cashier, facility=facility) == ["cashier"]
    assert policies.role_codes(admin, facility=facility) == ["facility_admin", "system_admin"]
    assert policies.role_codes(orphan) == []
    migration.backwards(live_apps, None)
    assert not RoleAssignment.objects.filter(reason=migration.REASON).exists()
