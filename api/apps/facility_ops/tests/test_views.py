from datetime import date

import pytest

from apps.analytics.models import RTInventoryAlert
from apps.audit.models import AuditEvent
from apps.facilities.tests.factories import FacilityFactory
from apps.facility_ops.models import FacilityAlert, FacilityDailyStats
from apps.warehouses.tests.factories import ProductFactory, WarehouseFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def stores(facility):
    return WarehouseFactory.create(branch=facility.branch), WarehouseFactory.create(
        branch=FacilityFactory.create().branch
    )


def test_stats_are_scoped_and_submissions_audited(api_as, facility, stores):
    mine, theirs = stores
    FacilityDailyStats.objects.create(warehouse=mine, date=date(2026, 10, 14), patient_footfall=40)
    FacilityDailyStats.objects.create(
        warehouse=theirs, date=date(2026, 10, 14), patient_footfall=90
    )
    client = api_as("store_keeper", facility=facility)
    rows = client.get("/api/v1/facility-ops/stats/").json()
    assert [row["patient_footfall"] for row in rows] == [40]  # plain list for the legacy dashboard
    assert (
        client.get(f"/api/v1/facility-ops/stats/?warehouse={mine.pk}").json()[0]["warehouse"]
        == mine.pk
    )
    payload = {"date": "2026-10-15", "patient_footfall": 55, "beds_total": 10, "beds_occupied": 6}
    refused = client.post(
        "/api/v1/facility-ops/stats/", {**payload, "warehouse": theirs.pk}, format="json"
    )
    assert refused.status_code == 400
    created = client.post(
        "/api/v1/facility-ops/stats/", {**payload, "warehouse": mine.pk}, format="json"
    )
    assert created.status_code == 201
    assert created.json()["bed_occupancy_rate"] == 60.0
    assert AuditEvent.objects.get(action="operations.stats.submitted").detail == {
        "date": "2026-10-15"
    }


def test_report_viewer_reads_but_cannot_submit(api_as, facility, stores):
    client = api_as("report_viewer", facility=facility)
    assert client.get("/api/v1/facility-ops/stats/").status_code == 200
    response = client.post(
        "/api/v1/facility-ops/stats/",
        {"warehouse": stores[0].pk, "date": "2026-10-15"},
        format="json",
    )
    assert response.status_code == 403


def test_alerts_are_scoped(api_as, facility, stores):
    mine, theirs = stores
    FacilityAlert.objects.create(warehouse=mine, alert_type="understaffed", message="Short")
    FacilityAlert.objects.create(warehouse=theirs, alert_type="understaffed", message="Elsewhere")
    product = ProductFactory.create()
    RTInventoryAlert.objects.create(product=product, warehouse=mine, current_stock=2)
    RTInventoryAlert.objects.create(product=product, warehouse=theirs, current_stock=1)
    client = api_as("report_viewer", facility=facility)
    assert [a["message"] for a in client.get("/api/v1/facility-ops/alerts/").json()] == ["Short"]
    assert [
        a["current_stock"] for a in client.get("/api/v1/analytics/inventory-alerts/").json()
    ] == [2]


def test_cashier_has_no_operations_access(api_as, facility):
    client = api_as("cashier", facility=facility)
    assert client.get("/api/v1/facility-ops/alerts/").status_code == 403
    assert client.get("/api/v1/analytics/inventory-alerts/").status_code == 403
