from datetime import timedelta

import pytest
import time_machine
from django.utils import timezone

from apps.access import policies
from apps.access.models import RoleAssignment
from apps.facilities.tests.factories import DepartmentFactory, FacilityFactory, WardFactory

pytestmark = pytest.mark.django_db


def test_assignment_grants_its_role_permissions_in_its_facility(make_user, facility, grant):
    user = make_user()
    grant(user, "receptionist", facility)
    assert policies.has_permission(user, "patients.patient.create", facility=facility)
    assert not policies.has_permission(user, "patients.merge.approve", facility=facility)
    assert not policies.has_permission(
        user, "patients.patient.create", facility=FacilityFactory.create()
    )


def test_no_assignment_no_permission_and_no_superuser_bypass(make_user, facility):
    admin = make_user(is_superuser=True, is_staff=True)
    assert not policies.has_permission(admin, "admin.user.create", facility=facility)
    assert policies.effective_permissions(admin, facility=facility) == set()


def test_unknown_codes_are_denied(make_user, facility, grant):
    user = make_user()
    grant(user, "facility_admin", facility)
    assert not policies.has_permission(user, "admin.user.obliterate", facility=facility)


def test_inactive_users_and_revoked_assignments_grant_nothing(make_user, facility, grant):
    user = make_user()
    assignment = grant(user, "receptionist", facility)
    assignment.status = RoleAssignment.Status.REVOKED
    assignment.save()
    assert not policies.has_permission(user, "patients.patient.read", facility=facility)
    other = make_user(is_active=False)
    grant(other, "receptionist", facility)
    assert not policies.has_permission(other, "patients.patient.read", facility=facility)


def test_validity_window_is_enforced_with_time_travel(make_user, facility, grant):
    user = make_user()
    now = timezone.now()
    grant(
        user,
        "cashier",
        facility,
        valid_from=now + timedelta(days=1),
        valid_to=now + timedelta(days=3),
    )
    assert not policies.has_permission(user, "payments.receive.cash", facility=facility)
    with time_machine.travel(now + timedelta(days=2)):
        assert policies.has_permission(user, "payments.receive.cash", facility=facility)
    with time_machine.travel(now + timedelta(days=3, seconds=1)):
        assert not policies.has_permission(user, "payments.receive.cash", facility=facility)
    assert policies.has_permission(
        user, "payments.receive.cash", facility=facility, at=now + timedelta(days=2)
    )


def test_department_and_ward_scope(make_user, facility, grant):
    maternity = DepartmentFactory.create(facility=facility)
    surgery = DepartmentFactory.create(facility=facility)
    ward = WardFactory.create(facility=facility, department=maternity)
    other_ward = WardFactory.create(facility=facility, department=maternity)
    user = make_user()
    grant(user, "nurse_in_charge", facility, department=maternity, ward=ward)
    code = "facilities.bed.update_status"
    assert policies.has_permission(user, code, facility=facility, ward=ward)
    assert not policies.has_permission(user, code, facility=facility, ward=other_ward)
    assert not policies.has_permission(user, code, facility=facility, department=surgery)
    assert policies.has_permission(user, code, facility=facility)  # facility-level resource


def test_licensed_permissions_need_a_licence(make_user, facility, grant, monkeypatch):
    user = make_user()
    grant(user, "clinical_officer", facility)
    assert not policies.has_permission(user, "clinical.note.write", facility=facility)
    assert "clinical.note.write" not in policies.effective_permissions(user, facility=facility)
    assert policies.has_permission(user, "patients.patient.read", facility=facility)
    monkeypatch.setattr(policies, "licence_checker", lambda user, code, at: True)
    assert policies.has_permission(user, "clinical.note.write", facility=facility)
    assert "clinical.note.write" in policies.effective_permissions(user, facility=facility)


def test_addon_roles_combine_with_base_roles(make_user, facility, grant):
    user = make_user()
    grant(user, "hrio", facility)
    grant(user, "hrio_supervisor", facility)
    assert policies.has_permission(user, "patients.merge.request", facility=facility)
    assert policies.has_permission(user, "patients.merge.approve", facility=facility)
    assert policies.role_codes(user, facility=facility) == ["hrio", "hrio_supervisor"]
    assert policies.facilities_for(user) == [facility.pk]


def test_audit_events_carry_the_actor_roles(make_user, facility, grant):
    from apps.audit.services import record

    user = make_user()
    grant(user, "cashier", facility)
    assert record("x.y.z", actor=user).actor_role == "cashier"
