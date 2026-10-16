"""State changes for facilities and their layout. Every change is audited."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.facilities.models import Bed, Department, Facility, ServicePoint, Ward

FACILITY_FIELDS = {
    "name",
    "mfl_code",
    "fid",
    "keph_level",
    "sha_contract_number",
    "kra_pin",
    "odpc_controller_registration",
    "odpc_processor_registration",
    "slade_provider_code",
    "mrn_format",
    "require_mfa_for_all",
    "workstation_lock_minutes",
    "session_idle_minutes",
    "session_absolute_hours",
    "care_team_expiry_hours",
    "break_glass_minutes",
    "active",
}

# Admin may set these; "occupied" is set only by bed allocation (inpatient, Phase 2).
ADMIN_BED_STATUSES = {Bed.Status.AVAILABLE, Bed.Status.CLEANING, Bed.Status.OUT_OF_SERVICE}


def _changed(instance: Any, changes: dict[str, Any], allowed: set[str]) -> list[str]:
    unknown = set(changes) - allowed
    if unknown:
        raise ValidationError({field: "This field cannot be changed here." for field in unknown})
    changed = [field for field, value in changes.items() if getattr(instance, field) != value]
    for field in changed:
        setattr(instance, field, changes[field])
    instance.full_clean()
    return changed


@transaction.atomic
def create_facility(*, branch: Any, actor: Any, **fields: Any) -> Facility:
    values = {"name": branch.name, "kra_pin": branch.kra_pin, **fields}
    unknown = set(values) - FACILITY_FIELDS
    if unknown:
        raise ValidationError({field: "Unknown facility field." for field in unknown})
    facility = Facility(branch=branch, **values)
    facility.full_clean()
    facility.save()
    record("facilities.facility.created", actor, facility, facility=facility)
    return facility


@transaction.atomic
def update_facility(facility: Facility, *, actor: Any, **changes: Any) -> Facility:
    facility = Facility.objects.select_for_update().get(pk=facility.pk)
    changed = _changed(facility, changes, FACILITY_FIELDS)
    if changed:
        facility.save()
        record(
            "facilities.facility.updated",
            actor,
            facility,
            facility=facility,
            detail={"fields": changed},
        )
    return facility


@transaction.atomic
def create_department(*, facility: Facility, actor: Any, code: str, name: str) -> Department:
    department = Department(facility=facility, code=code, name=name)
    department.full_clean()
    department.save()
    record("facilities.department.created", actor, department, facility=facility)
    return department


@transaction.atomic
def create_service_point(
    *,
    facility: Facility,
    actor: Any,
    code: str,
    name: str,
    kind: str,
    department: Department | None = None,
) -> ServicePoint:
    if department is not None and department.facility_id != facility.pk:
        raise ValidationError({"department": "The department belongs to another facility."})
    point = ServicePoint(facility=facility, department=department, code=code, name=name, kind=kind)
    point.full_clean()
    point.save()
    record(
        "facilities.service_point.created", actor, point, facility=facility, detail={"kind": kind}
    )
    return point


@transaction.atomic
def create_ward(
    *,
    facility: Facility,
    actor: Any,
    code: str,
    name: str,
    kind: str = Ward.Kind.GENERAL,
    sex: str = Ward.Sex.MIXED,
    department: Department | None = None,
) -> Ward:
    if department is not None and department.facility_id != facility.pk:
        raise ValidationError({"department": "The department belongs to another facility."})
    ward = Ward(facility=facility, department=department, code=code, name=name, kind=kind, sex=sex)
    ward.full_clean()
    ward.save()
    record("facilities.ward.created", actor, ward, facility=facility)
    return ward


@transaction.atomic
def create_bed(*, ward: Ward, actor: Any, code: str) -> Bed:
    bed = Bed(ward=ward, code=code, status_changed_at=timezone.now())
    bed.full_clean()
    bed.save()
    record("facilities.bed.created", actor, bed, facility=ward.facility_id)
    return bed


@transaction.atomic
def set_bed_status(bed: Bed, *, actor: Any, status: str) -> Bed:
    """Admin status changes; an occupied bed is released only by discharge/transfer."""
    if status not in ADMIN_BED_STATUSES:
        raise ValidationError({"status": "Beds become occupied only through bed allocation."})
    bed = Bed.objects.select_for_update().select_related("ward").get(pk=bed.pk)
    if bed.status == Bed.Status.OCCUPIED:
        raise ValidationError(
            {"status": "The bed is occupied; discharge or transfer the patient first."}
        )
    if not bed.active and status == Bed.Status.AVAILABLE:
        raise ValidationError({"status": "An inactive bed cannot be made available."})
    previous = bed.status
    if previous != status:
        bed.status = status
        bed.status_changed_at = timezone.now()
        bed.save(update_fields=["status", "status_changed_at"])
        record(
            "facilities.bed.status_changed",
            actor,
            bed,
            facility=bed.ward.facility_id,
            detail={"from": previous, "to": status},
        )
    return bed


LAYOUT_FIELDS: dict[type, set[str]] = {
    Department: {"name"},
    ServicePoint: {"name", "kind", "department"},
    Ward: {"name", "kind", "sex", "department"},
    Bed: {"code"},
}


@transaction.atomic
def update_layout(instance: Any, *, actor: Any, **changes: Any) -> Any:
    """Rename or re-type a layout entry; codes of departments, points and wards stay fixed."""
    model = type(instance)
    instance = model.objects.select_for_update().get(pk=instance.pk)
    department = changes.get("department")
    facility_id = instance.ward.facility_id if isinstance(instance, Bed) else instance.facility_id
    if department is not None and department.facility_id != facility_id:
        raise ValidationError({"department": "The department belongs to another facility."})
    changed = _changed(instance, changes, LAYOUT_FIELDS[model])
    if changed:
        instance.save()
        record(
            f"facilities.{model._meta.model_name}.updated",
            actor,
            instance,
            facility=facility_id,
            detail={"fields": changed},
        )
    return instance


@transaction.atomic
def set_active(
    instance: Department | ServicePoint | Ward | Bed, *, actor: Any, active: bool
) -> Any:
    """Deactivate (never delete) layout entries; occupied beds cannot be deactivated."""
    model = type(instance)
    instance = model.objects.select_for_update().get(pk=instance.pk)
    if isinstance(instance, Bed) and not active and instance.status == Bed.Status.OCCUPIED:
        raise ValidationError({"active": "The bed is occupied."})
    if instance.active != active:
        instance.active = active
        instance.save(update_fields=["active"])
        facility_id = (
            instance.ward.facility_id if isinstance(instance, Bed) else instance.facility_id
        )
        record(
            f"facilities.{model._meta.model_name}.{'activated' if active else 'deactivated'}",
            actor,
            instance,
            facility=facility_id,
        )
    return instance
