import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.audit.models import AuditEvent
from apps.facilities import services
from apps.facilities.models import Bed, ServicePoint, Ward
from apps.facilities.tests.factories import (
    BedFactory,
    BranchFactory,
    DepartmentFactory,
    FacilityFactory,
    WardFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_user(email="facility.admin@example.test")


@pytest.mark.req("KE-DHA-04")
def test_facility_stores_registry_identifiers(admin_user):
    branch = BranchFactory.create()
    facility = services.create_facility(
        branch=branch,
        actor=admin_user,
        mfl_code="99999",
        fid="FID-47-123456-7",
        keph_level=4,
        sha_contract_number="SHA-CTR-0001",
        odpc_controller_registration="ODPC-C-0001",
        odpc_processor_registration="ODPC-P-0002",
        slade_provider_code="SLADE-01",
    )
    assert facility.kra_pin == branch.kra_pin
    assert facility.branch == branch
    event = AuditEvent.objects.get(action="facilities.facility.created")
    assert event.facility_id == facility.pk


def test_facility_is_one_to_one_with_branch(admin_user):
    facility = FacilityFactory.create()
    with pytest.raises((ValidationError, IntegrityError)):
        services.create_facility(branch=facility.branch, actor=admin_user, mfl_code="12345")


@pytest.mark.parametrize(
    ("field", "value"),
    [("mfl_code", "12AB"), ("fid", "12345"), ("kra_pin", "123"), ("workstation_lock_minutes", 0)],
)
def test_identifier_formats_and_bounds_are_validated(admin_user, field, value):
    with pytest.raises(ValidationError):
        services.create_facility(branch=BranchFactory.create(), actor=admin_user, **{field: value})


def test_unknown_fields_are_refused(admin_user):
    with pytest.raises(ValidationError):
        services.create_facility(branch=BranchFactory.create(), actor=admin_user, branch_id=5)
    with pytest.raises(ValidationError):
        services.update_facility(FacilityFactory.create(), actor=admin_user, branch_id=5)


def test_update_audits_changed_fields_only(admin_user):
    facility = FacilityFactory.create(sha_contract_number="")
    services.update_facility(
        facility, actor=admin_user, sha_contract_number="SHA-1", name=facility.name
    )
    event = AuditEvent.objects.get(action="facilities.facility.updated")
    assert event.detail == {"fields": ["sha_contract_number"]}
    services.update_facility(facility, actor=admin_user, sha_contract_number="SHA-1")
    assert AuditEvent.objects.filter(action="facilities.facility.updated").count() == 1


def test_layout_is_created_and_audited(admin_user):
    facility = FacilityFactory.create()
    department = services.create_department(
        facility=facility, actor=admin_user, code="OPD", name="Outpatient"
    )
    point = services.create_service_point(
        facility=facility,
        actor=admin_user,
        code="TRI1",
        name="Triage 1",
        kind=ServicePoint.Kind.TRIAGE,
        department=department,
    )
    ward = services.create_ward(
        facility=facility,
        actor=admin_user,
        code="MW",
        name="Maternity",
        kind=Ward.Kind.MATERNITY,
        sex=Ward.Sex.FEMALE,
    )
    bed = services.create_bed(ward=ward, actor=admin_user, code="01")
    assert (point.kind, bed.status, str(bed)) == ("triage", "available", "MW-01")
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "facilities.department.created",
        "facilities.service_point.created",
        "facilities.ward.created",
        "facilities.bed.created",
    } <= actions
    assert set(AuditEvent.objects.values_list("facility_id", flat=True)) == {facility.pk}


def test_codes_are_unique_per_facility(admin_user):
    department = DepartmentFactory.create(code="OPD")
    with pytest.raises(ValidationError):
        services.create_department(
            facility=department.facility, actor=admin_user, code="OPD", name="Again"
        )
    services.create_department(
        facility=FacilityFactory.create(), actor=admin_user, code="OPD", name="Elsewhere"
    )


def test_layout_cannot_cross_facilities(admin_user):
    department = DepartmentFactory.create()
    other = FacilityFactory.create()
    with pytest.raises(ValidationError):
        services.create_service_point(
            facility=other,
            actor=admin_user,
            code="X",
            name="X",
            kind="triage",
            department=department,
        )
    with pytest.raises(ValidationError):
        services.create_ward(
            facility=other, actor=admin_user, code="X", name="X", department=department
        )


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (Bed.Status.AVAILABLE, Bed.Status.CLEANING),
        (Bed.Status.AVAILABLE, Bed.Status.OUT_OF_SERVICE),
        (Bed.Status.CLEANING, Bed.Status.AVAILABLE),
    ],
)
def test_admin_bed_status_changes(admin_user, start, target):
    bed = services.set_bed_status(BedFactory.create(status=start), actor=admin_user, status=target)
    assert bed.status == target
    event = AuditEvent.objects.get(action="facilities.bed.status_changed")
    assert event.detail == {"from": start, "to": target}


def test_beds_are_occupied_only_by_allocation(admin_user):
    with pytest.raises(ValidationError, match="allocation"):
        services.set_bed_status(BedFactory.create(), actor=admin_user, status=Bed.Status.OCCUPIED)
    occupied = BedFactory.create(status=Bed.Status.OCCUPIED)
    with pytest.raises(ValidationError, match="occupied"):
        services.set_bed_status(occupied, actor=admin_user, status=Bed.Status.CLEANING)
    with pytest.raises(ValidationError, match="occupied"):
        services.set_active(occupied, actor=admin_user, active=False)


def test_inactive_bed_cannot_become_available(admin_user):
    bed = BedFactory.create(status=Bed.Status.OUT_OF_SERVICE, active=False)
    with pytest.raises(ValidationError, match="inactive"):
        services.set_bed_status(bed, actor=admin_user, status=Bed.Status.AVAILABLE)


def test_layout_entries_are_deactivated_not_deleted(admin_user):
    ward = WardFactory.create()
    services.set_active(ward, actor=admin_user, active=False)
    ward.refresh_from_db()
    assert ward.active is False
    services.set_active(ward, actor=admin_user, active=False)  # no-op, no second event
    assert AuditEvent.objects.filter(action="facilities.ward.deactivated").count() == 1
    services.set_active(BedFactory.create(), actor=admin_user, active=False)
    assert AuditEvent.objects.filter(action="facilities.bed.deactivated").exists()
