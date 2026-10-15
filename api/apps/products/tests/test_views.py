from decimal import Decimal

import pytest

from apps.audit.models import AuditEvent
from apps.facilities.tests.factories import FacilityFactory
from apps.products.models import Product
from apps.warehouses.tests.factories import (
    CategoryFactory,
    InventoryFactory,
    ProductFactory,
    WarehouseFactory,
)

pytestmark = pytest.mark.django_db


def test_catalogue_read_and_manage(api_as, facility):
    client = api_as("store_keeper", facility=facility)
    category = client.post("/api/v1/products/categories/", {"name": "Analgesics"}, format="json")
    assert category.status_code == 201
    created = client.post(
        "/api/v1/products/products/",
        {
            "name": "Ibuprofen 400mg",
            "category": category.json()["id"],
            "barcode": "IBU400",
            "buying_price": "4.00",
            "selling_price": "6.50",
            "reorder_level": 30,
        },
        format="json",
    )
    assert created.status_code == 201
    product = Product.objects.get(barcode="IBU400")
    assert product.sku.startswith("SKU-")
    detail = client.get(f"/api/v1/products/products/{product.pk}/").json()
    assert detail["vat_amount"] == "1.04"
    assert (
        client.patch(
            f"/api/v1/products/products/{product.pk}/", {"reorder_level": 40}, format="json"
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/products/categories/{category.json()['id']}/",
            {"description": "Pain"},
            format="json",
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/products/products/{product.pk}/").status_code == 204
    product.refresh_from_db()
    assert product.is_active is False  # retired, not deleted
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "inventory.category.created",
        "inventory.product.created",
        "inventory.product.updated",
        "inventory.product.retired",
    } <= actions


def test_vat_is_a_decimal_rounded_half_up():
    product = ProductFactory.build(selling_price=Decimal("15.03"), category=CategoryFactory.build())
    assert product.vat_amount == Decimal("2.40")
    product.category.vat_category = "EXEMPT"
    assert product.vat_amount == Decimal("0.00")


def test_report_viewer_cannot_read_the_catalogue(api_as, facility):
    client = api_as("report_viewer", facility=facility)
    assert client.get("/api/v1/products/products/").status_code == 403


def test_pharmacist_reads_but_cannot_edit_catalogue(api_as, facility):
    client = api_as("pharmacist", facility=facility)
    assert client.get("/api/v1/products/products/").status_code == 403  # product.read is store's
    assert client.get("/api/v1/products/inventory/").status_code == 200  # stock.read


def test_product_images(api_as, facility):
    product = ProductFactory.create()
    client = api_as("store_keeper", facility=facility)
    assert client.get(f"/api/v1/products/products/{product.pk}/images/").json()["results"] == []
    missing = client.post("/api/v1/products/products/999999/images/", {}, format="multipart")
    assert missing.status_code in (400, 404)


def test_stock_is_scoped_and_adjustments_audited(api_as, facility):
    mine = InventoryFactory.create(warehouse=WarehouseFactory.create(branch=facility.branch))
    theirs = InventoryFactory.create(
        warehouse=WarehouseFactory.create(branch=FacilityFactory.create().branch)
    )
    client = api_as("store_keeper", facility=facility)
    rows = client.get("/api/v1/products/inventory/").json()["results"]
    assert [row["id"] for row in rows] == [mine.pk]
    assert (
        client.get(f"/api/v1/products/inventory/?warehouse={mine.warehouse_id}").json()["results"][
            0
        ]["id"]
        == mine.pk
    )
    assert client.get(f"/api/v1/products/inventory/{theirs.pk}/").status_code == 404
    assert (
        client.patch(
            f"/api/v1/products/inventory/{mine.pk}/", {"quantity": 7}, format="json"
        ).status_code
        == 200
    )
    moved = client.patch(
        f"/api/v1/products/inventory/{mine.pk}/", {"warehouse": theirs.warehouse_id}, format="json"
    )
    assert moved.status_code == 400
    new_row = client.post(
        "/api/v1/products/inventory/",
        {"product": ProductFactory.create().pk, "warehouse": mine.warehouse_id, "quantity": 3},
        format="json",
    )
    assert new_row.status_code == 201
    assert AuditEvent.objects.filter(action="inventory.stock.adjusted").count() == 2
