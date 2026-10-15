"""Facility scoping for stores: a warehouse belongs to the facility of its branch (ADR-018)."""

from django.db.models import QuerySet

from apps.warehouses.models import Branch, Warehouse


def facility_warehouses(facility_id: int | None) -> QuerySet[Warehouse]:
    if facility_id is None:
        return Warehouse.objects.none()
    return Warehouse.objects.filter(branch__facility__id=facility_id)


def facility_branches(facility_id: int | None) -> QuerySet[Branch]:
    if facility_id is None:
        return Branch.objects.none()
    return Branch.objects.filter(facility__id=facility_id)


def branch_facility_id(branch: Branch) -> int | None:
    facility = getattr(branch, "facility", None)
    return facility.pk if facility is not None else None


def warehouse_facility_id(warehouse: Warehouse) -> int | None:
    return branch_facility_id(warehouse.branch)
