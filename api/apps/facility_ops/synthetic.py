"""Seed step: a week of synthetic operations data at the synthetic facility (MFL 99999), so
the reports and inventory workspaces (P1-WEB-06) show what the legacy dashboards showed.
Runs after ``apps.facilities.seed``; idempotent. Numbers only — no people, no PHI."""

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.analytics.models import RTInventoryAlert
from apps.facilities import seed as facility_seed
from apps.facility_ops.models import FacilityAlert, FacilityDailyStats
from apps.products.models import Product
from apps.warehouses.models import Warehouse

STORE_CODE = "SYN-MAIN"
DAYS = 7
# Footfall, beds occupied (of 26), doctors present (of 6) — a plausible week, oldest first.
WEEK = [
    (118, 19, 6),
    (131, 21, 5),
    (126, 22, 6),
    (142, 24, 5),
    (109, 23, 4),
    (64, 20, 3),
    (57, 18, 3),
]


@transaction.atomic
def run(command: Any) -> None:
    site = facility_seed.facility()
    store, _ = Warehouse.objects.get_or_create(
        code=STORE_CODE,
        defaults={
            "branch": site.branch,
            "name": "Synthetic Hospital main store",
            "physical_address": "Synthetic Road, Nairobi",
            "contact_phone": "+254700000000",
        },
    )
    today = timezone.localdate()
    added = 0
    for offset, (footfall, occupied, present) in enumerate(WEEK):
        _, created = FacilityDailyStats.objects.get_or_create(
            warehouse=store,
            date=today - timedelta(days=DAYS - 1 - offset),
            defaults={
                "patient_footfall": footfall,
                "beds_total": 26,
                "beds_occupied": occupied,
                "doctors_scheduled": 6,
                "doctors_present": present,
            },
        )
        added += created
    if not FacilityAlert.objects.filter(warehouse=store).exists():
        FacilityAlert.objects.create(
            warehouse=store,
            alert_type="understaffed",
            severity="medium",
            message="Three of six doctors present on the weekend shift.",
        )
    product = Product.objects.order_by("pk").first()
    if product and not RTInventoryAlert.objects.filter(warehouse=store).exists():
        RTInventoryAlert.objects.create(product=product, warehouse=store, current_stock=4)
    command.stdout.write(f"  operations: {added} new days of synthetic statistics at {site.name}")
