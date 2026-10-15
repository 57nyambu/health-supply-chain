import pytest

from apps.audit.models import AuditEvent
from apps.facilities.models import Bed
from apps.facilities.tests.factories import (
    BedFactory,
    DepartmentFactory,
    FacilityFactory,
    WardFactory,
)

pytestmark = pytest.mark.django_db
BASE = "/api/v1/facilities"


@pytest.mark.req("KE-DHA-04")
def test_facility_admin_edits_identifiers(api_as, facility):
    admin = api_as("facility_admin", facility=facility)
    rows = admin.get(f"{BASE}/facilities/").json()["results"]
    assert [row["id"] for row in rows] == [facility.pk]
    response = admin.patch(
        f"{BASE}/facilities/{facility.pk}/",
        {"fid": "FID-47-000001-1", "sha_contract_number": "SHA-77", "session_idle_minutes": 20},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["fid"] == "FID-47-000001-1"
    assert AuditEvent.objects.filter(action="facilities.facility.updated").exists()
    bad = admin.patch(
        f"{BASE}/facilities/{facility.pk}/", {"session_idle_minutes": 999}, format="json"
    )
    assert bad.status_code == 400


def test_other_facilities_are_invisible(api_as, facility):
    other = FacilityFactory.create()
    admin = api_as("facility_admin", facility=facility)
    assert admin.get(f"{BASE}/facilities/{other.pk}/").status_code == 404


def test_receptionist_reads_layout_but_cannot_change_it(api_as, facility):
    DepartmentFactory.create(facility=facility)
    clerk = api_as("receptionist", facility=facility)
    assert clerk.get(f"{BASE}/departments/").status_code == 200
    assert (
        clerk.post(f"{BASE}/departments/", {"code": "X", "name": "X"}, format="json").status_code
        == 403
    )
    assert clerk.get(f"{BASE}/facilities/").status_code == 403


def test_layout_setup_through_the_api(api_as, facility):
    admin = api_as("facility_admin", facility=facility)
    department = admin.post(
        f"{BASE}/departments/", {"code": "OPD", "name": "Outpatient"}, format="json"
    )
    assert department.status_code == 201
    point = admin.post(
        f"{BASE}/service-points/",
        {
            "code": "TRI1",
            "name": "Triage 1",
            "kind": "triage",
            "department": department.json()["id"],
        },
        format="json",
    )
    assert point.status_code == 201
    assert len(admin.get(f"{BASE}/service-points/?kind=triage").json()["results"]) == 1
    ward = admin.post(
        f"{BASE}/wards/", {"code": "FW", "name": "Female ward", "sex": "female"}, format="json"
    )
    assert ward.status_code == 201
    bed = admin.post(f"{BASE}/beds/", {"ward": ward.json()["id"], "code": "01"}, format="json")
    assert bed.status_code == 201
    listed = admin.get(f"{BASE}/wards/").json()["results"][0]
    assert (listed["beds_total"], listed["beds_available"]) == (1, 1)
    renamed = admin.patch(
        f"{BASE}/wards/{ward.json()['id']}/", {"name": "Female surgical"}, format="json"
    )
    assert renamed.json()["name"] == "Female surgical"
    off = admin.patch(
        f"{BASE}/departments/{department.json()['id']}/", {"active": False}, format="json"
    )
    assert off.json()["active"] is False
    assert admin.delete(f"{BASE}/departments/{department.json()['id']}/").status_code in (403, 405)


def test_cross_facility_references_are_refused(api_as, facility):
    admin = api_as("facility_admin", facility=facility)
    foreign_ward = WardFactory.create()
    assert (
        admin.post(
            f"{BASE}/beds/", {"ward": foreign_ward.pk, "code": "9"}, format="json"
        ).status_code
        == 400
    )
    foreign_department = DepartmentFactory.create()
    response = admin.post(
        f"{BASE}/wards/",
        {"code": "W", "name": "W", "department": foreign_department.pk},
        format="json",
    )
    assert response.status_code == 400
    ward = WardFactory.create(facility=facility)
    moved = admin.patch(
        f"{BASE}/wards/{ward.pk}/", {"department": foreign_department.pk}, format="json"
    )
    assert moved.status_code == 400


def test_bed_status_by_nurse_in_charge(api_as, facility):
    bed = BedFactory.create(ward=WardFactory.create(facility=facility))
    nurse = api_as("nurse", "nurse_in_charge", facility=facility)
    response = nurse.post(f"{BASE}/beds/{bed.pk}/status/", {"status": "cleaning"}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "cleaning"
    occupied = nurse.post(f"{BASE}/beds/{bed.pk}/status/", {"status": "occupied"}, format="json")
    assert occupied.status_code == 400
    assert (
        nurse.get(f"{BASE}/beds/?ward={bed.ward_id}").json()["results"][0]["status"]
        == Bed.Status.CLEANING
    )
    receptionist = api_as("receptionist", facility=facility)
    assert (
        receptionist.post(
            f"{BASE}/beds/{bed.pk}/status/", {"status": "available"}, format="json"
        ).status_code
        == 403
    )


def test_beds_of_other_facilities_are_not_found(api_as, facility):
    bed = BedFactory.create()
    nurse = api_as("nurse_in_charge", facility=facility)
    assert (
        nurse.post(
            f"{BASE}/beds/{bed.pk}/status/", {"status": "cleaning"}, format="json"
        ).status_code
        == 404
    )
