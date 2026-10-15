import pytest

from apps.audit.models import AuditEvent
from apps.facilities.tests.factories import FacilityFactory
from apps.warehouses.models import StockTransfer
from apps.warehouses.tests.factories import ProductFactory, WarehouseFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def store(facility):
    return WarehouseFactory.create(branch=facility.branch)


@pytest.fixture
def other_store():
    return WarehouseFactory.create(branch=FacilityFactory.create().branch)


def test_store_keeper_sees_only_their_facility(api_as, facility, store, other_store):
    client = api_as("store_keeper", facility=facility)
    codes = [w["code"] for w in client.get("/api/v1/warehouses/warehouses/").json()["results"]]
    assert codes == [store.code]
    assert client.get(f"/api/v1/warehouses/warehouses/{other_store.pk}/").status_code == 404
    branches = client.get("/api/v1/warehouses/branches/").json()["results"]
    assert [b["id"] for b in branches] == [facility.branch_id]


def test_roles_without_the_permission_are_denied(api_as, facility, store):
    client = api_as("receptionist", facility=facility)
    response = client.get("/api/v1/warehouses/warehouses/")
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_user_without_a_facility_is_denied(api_as, facility, make_user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_login(make_user())
    assert client.get("/api/v1/warehouses/warehouses/").status_code == 403


def test_store_create_requires_own_branch_and_is_audited(api_as, facility, other_store):
    client = api_as("store_keeper", facility=facility)
    payload = {
        "name": "Pharmacy store",
        "code": "WH-PH1",
        "physical_address": "Block B",
        "contact_phone": "+254700000009",
    }
    refused = client.post(
        "/api/v1/warehouses/warehouses/",
        {**payload, "branch": other_store.branch_id},
        format="json",
    )
    assert refused.status_code == 400
    created = client.post(
        "/api/v1/warehouses/warehouses/", {**payload, "branch": facility.branch_id}, format="json"
    )
    assert created.status_code == 201
    updated = client.patch(
        f"/api/v1/warehouses/warehouses/{created.json()['id']}/",
        {"name": "Main pharmacy"},
        format="json",
    )
    assert updated.status_code == 200
    assert {"inventory.store.created", "inventory.store.updated"} <= set(
        AuditEvent.objects.values_list("action", flat=True)
    )


def test_stores_cannot_be_deleted(api_as, facility, store):
    client = api_as("store_keeper", facility=facility)
    assert client.delete(f"/api/v1/warehouses/warehouses/{store.pk}/").status_code in (403, 405)
    assert client.get(f"/api/v1/warehouses/warehouses/{store.pk}/").status_code == 200


def test_branch_edit_needs_branch_management(api_as, facility):
    client = api_as("store_keeper", facility=facility)
    assert (
        client.patch(
            f"/api/v1/warehouses/branches/{facility.branch_id}/", {"name": "x"}, format="json"
        ).status_code
        == 403
    )


def test_bins_are_scoped_to_facility_stores(api_as, facility, store, other_store):
    client = api_as("store_keeper", facility=facility)
    ok = client.post(
        "/api/v1/warehouses/bins/",
        {"warehouse": store.pk, "name": "Shelf A", "barcode": "BIN-A"},
        format="json",
    )
    assert ok.status_code == 201
    other = client.post(
        "/api/v1/warehouses/bins/",
        {"warehouse": other_store.pk, "name": "Shelf A", "barcode": "BIN-B"},
        format="json",
    )
    assert other.status_code == 400
    listed = client.get(f"/api/v1/warehouses/bins/?warehouse={store.pk}").json()["results"]
    assert [b["name"] for b in listed] == ["Shelf A"]
    assert (
        client.patch(
            f"/api/v1/warehouses/bins/{ok.json()['id']}/", {"notes": "cold"}, format="json"
        ).status_code
        == 200
    )


def _transfer(client, store, target, product):
    return client.post(
        "/api/v1/warehouses/transfers/",
        {
            "product": product.pk,
            "from_warehouse": store.pk,
            "to_warehouse": target.pk,
            "quantity": 5,
        },
        format="json",
    )


def test_transfer_workflow_with_separation_of_duties(api_as, facility, store, make_user, grant):
    second_store = WarehouseFactory.create(branch=facility.branch)
    product = ProductFactory.create()
    maker = api_as("store_keeper", facility=facility)
    response = _transfer(maker, store, second_store, product)
    assert response.status_code == 201
    transfer = StockTransfer.objects.get()
    assert transfer.reference_no.startswith("TRF-")
    own = maker.post(f"/api/v1/warehouses/transfers/{transfer.pk}/approve/")
    assert own.status_code == 403
    assert "requested" in own.json()["detail"]
    checker = api_as("store_keeper", facility=facility)
    early = checker.post(f"/api/v1/warehouses/transfers/{transfer.pk}/complete/")
    assert early.status_code == 409
    assert (
        checker.post(f"/api/v1/warehouses/transfers/{transfer.pk}/approve/").json()["status"]
        == "APPROVED"
    )
    assert checker.post(f"/api/v1/warehouses/transfers/{transfer.pk}/approve/").status_code == 409
    assert (
        maker.post(f"/api/v1/warehouses/transfers/{transfer.pk}/complete/").json()["status"]
        == "RECEIVED"
    )
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "inventory.transfer.created",
        "inventory.transfer.approved",
        "inventory.transfer.received",
    } <= actions
    assert len(maker.get("/api/v1/warehouses/transfers/").json()["results"]) == 1


def test_only_the_receiving_facility_receives(api_as, facility, store, other_store):
    product = ProductFactory.create()
    maker = api_as("store_keeper", facility=facility)
    _transfer(maker, store, other_store, product)
    transfer = StockTransfer.objects.get()
    api_as("store_keeper", facility=facility).post(
        f"/api/v1/warehouses/transfers/{transfer.pk}/approve/"
    )
    response = maker.post(f"/api/v1/warehouses/transfers/{transfer.pk}/complete/")
    assert response.status_code == 403


def test_transfers_must_leave_from_own_store(api_as, facility, store, other_store):
    client = api_as("store_keeper", facility=facility)
    response = _transfer(client, other_store, store, ProductFactory.create())
    assert response.status_code == 400
