"""Billing state changes (DESIGN §10). Every change is audited; price changes and new
services go through maker-checker (DESIGN §7.9: finance manager approves)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.access import approvals, policies
from apps.access.models import ApprovalRequest
from apps.audit.services import record
from apps.billing.models import PriceList, PriceListItem, Service
from apps.core.money import as_str, money

PRICE_CHANGE = "billing.price.set"
NEW_SERVICE = "billing.service.create"
APPROVER = ["billing.pricelist.approve"]
EDITABLE_SERVICE_FIELDS = {
    "name",
    "department",
    "revenue_code",
    "sha_interventions",
    "etims_item_code",
}


def _ensure(actor: Any, code: str, facility: Any) -> None:
    if actor is not None and not policies.has_permission(actor, code, facility=facility):
        raise PermissionDenied("You do not have permission to do this here.")


# --- Services ------------------------------------------------------------------------------------


def _validate_service_fields(facility_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    clean = dict(fields)
    if "kind" in clean and clean["kind"] not in Service.Kind.values:
        raise ValidationError({"kind": "Choose a service kind."})
    codes = clean.get("sha_interventions")
    if codes is not None:
        if not isinstance(codes, list) or not all(isinstance(c, str) and c.strip() for c in codes):
            raise ValidationError({"sha_interventions": "List intervention codes as text."})
        clean["sha_interventions"] = sorted({c.strip().upper() for c in codes})
    department = clean.get("department")
    if department is not None and getattr(department, "facility_id", facility_id) != facility_id:
        raise ValidationError({"department": "Choose a department of this facility."})
    return clean


def _create_service(*, facility: Any, actor: Any, approval: Any = None, **fields: Any) -> Service:
    facility_id = getattr(facility, "pk", facility)
    fields = _validate_service_fields(facility_id, fields)
    code = str(fields.pop("code", "")).strip().upper()
    if not code:
        raise ValidationError({"code": "Enter a service code."})
    if Service.objects.filter(facility_id=facility_id, code=code).exists():
        raise ValidationError({"code": "A service with this code already exists."})
    service = Service(facility_id=facility_id, code=code, status=Service.Status.ACTIVE, **fields)
    service.full_clean()
    service.save()
    record(
        "billing.service.created",
        actor,
        service,
        facility=facility_id,
        detail={
            "code": code,
            "kind": service.kind,
            "approval_id": str(approval.pk) if approval else None,
        },
    )
    return service


@transaction.atomic
def request_new_service(
    *,
    facility: Any,
    actor: Any,
    reason: str,
    cash_price: Decimal | str | None = None,
    **fields: Any,
) -> ApprovalRequest:
    """Maker side: ask the finance manager to add a service (and optionally its cash price)."""
    facility_id = getattr(facility, "pk", facility)
    _ensure(actor, "billing.pricelist.manage", facility_id)
    fields = _validate_service_fields(facility_id, fields)
    code = str(fields.get("code", "")).strip().upper()
    if not code or not fields.get("name") or not fields.get("kind"):
        raise ValidationError({"code": "Enter a code, name and kind."})
    if Service.objects.filter(facility_id=facility_id, code=code).exists():
        raise ValidationError({"code": "A service with this code already exists."})
    department = fields.get("department")
    payload = {
        "code": code,
        "name": str(fields["name"]).strip(),
        "kind": fields["kind"],
        "revenue_code": str(fields.get("revenue_code", "")),
        "sha_interventions": fields.get("sha_interventions", []),
        "etims_item_code": str(fields.get("etims_item_code", "")),
        "department_id": getattr(department, "pk", department),
        "cash_price": as_str(cash_price) if cash_price is not None else None,
    }
    return approvals.request_approval(
        action=NEW_SERVICE,
        facility=facility_id,
        requested_by=actor,
        payload=payload,
        required_permissions=APPROVER,
        reason=reason,
        resource=("billing.service", code),
        amount=money(cash_price) if cash_price is not None else None,
    )


def _execute_new_service(request: ApprovalRequest, approver: Any) -> None:
    data = dict(request.payload)
    cash_price = data.pop("cash_price")
    service = _create_service(
        facility=request.facility_id,
        actor=approver,
        approval=request,
        code=data["code"],
        name=data["name"],
        kind=data["kind"],
        revenue_code=data["revenue_code"],
        sha_interventions=data["sha_interventions"],
        etims_item_code=data["etims_item_code"],
        department_id=data["department_id"],
    )
    if cash_price is not None:
        cash = cash_list(request.facility_id)
        _set_price(
            price_list=cash,
            service=service,
            price=money(cash_price),
            effective_from=timezone.localdate(),
            actor=approver,
            approval=request,
        )


@transaction.atomic
def update_service(service: Service, *, actor: Any, changes: dict[str, Any]) -> Service:
    """Name, department and mapping fields change directly (audited); prices never do."""
    _ensure(actor, "billing.pricelist.manage", service.facility_id)
    unknown = set(changes) - EDITABLE_SERVICE_FIELDS
    if unknown:
        raise ValidationError({field: "This field cannot be changed here." for field in unknown})
    changes = _validate_service_fields(service.facility_id, changes)
    current = Service.objects.select_for_update().get(pk=service.pk)
    changed = [f for f, v in changes.items() if getattr(current, f) != v]
    for field in changed:
        setattr(current, field, changes[field])
    if changed:
        current.full_clean()
        current.save()
        record(
            "billing.service.updated",
            actor,
            current,
            facility=current.facility_id,
            detail={"fields": sorted(changed)},
        )
    return current


@transaction.atomic
def set_service_status(service: Service, *, actor: Any, active: bool, reason: str) -> Service:
    _ensure(actor, "billing.pricelist.manage", service.facility_id)
    if not reason.strip():
        raise ValidationError({"reason": "Say why."})
    current = Service.objects.select_for_update().get(pk=service.pk)
    target = Service.Status.ACTIVE if active else Service.Status.INACTIVE
    if current.status != target:
        current.status = target
        current.save(update_fields=["status", "updated_at"])
        record(
            "billing.service.status_changed",
            actor,
            current,
            facility=current.facility_id,
            detail={"status": target},
        )
    return current


# --- Price lists ----------------------------------------------------------------------------------


def cash_list(facility: Any) -> PriceList:
    facility_id = getattr(facility, "pk", facility)
    found = PriceList.objects.filter(
        facility_id=facility_id, payer__isnull=True, scheme__isnull=True, active=True
    ).first()
    if found is None:
        raise ValidationError({"price_list": "This facility has no active cash price list."})
    return found


@transaction.atomic
def create_price_list(
    *, facility: Any, actor: Any, code: str, name: str, payer: Any = None, scheme: Any = None
) -> PriceList:
    facility_id = getattr(facility, "pk", facility)
    _ensure(actor, "billing.pricelist.manage", facility_id)
    if payer is not None and scheme is not None:
        raise ValidationError(
            {"scheme": "A list is for a payer or for one of its schemes, not both."}
        )
    price_list = PriceList(
        facility_id=facility_id, code=code, name=name, payer=payer, scheme=scheme
    )
    price_list.full_clean()
    price_list.save()
    record(
        "billing.pricelist.created",
        actor,
        price_list,
        facility=facility_id,
        detail={"basis": price_list.basis, "code": code},
    )
    return price_list


def _set_price(
    *,
    price_list: PriceList,
    service: Service,
    price: Decimal,
    effective_from: date,
    actor: Any,
    approval: Any = None,
) -> PriceListItem:
    """Close the open price (the day before) and open the new one; history stays."""
    if service.facility_id != price_list.facility_id:
        raise ValidationError(
            {"service": "The service and price list belong to different facilities."}
        )
    if price < 0:
        raise ValidationError({"price": "A price cannot be negative."})
    current = (
        PriceListItem.objects.select_for_update()
        .filter(price_list=price_list, service=service, effective_to__isnull=True)
        .first()
    )
    if current is not None:
        if effective_from <= current.effective_from:
            raise ValidationError(
                {"effective_from": "The new price must start after the current one started."}
            )
        current.effective_to = effective_from - timedelta(days=1)
        current.save(update_fields=["effective_to"])
    item = PriceListItem.objects.create(
        price_list=price_list,
        service=service,
        price=price,
        effective_from=effective_from,
        approval=approval,
    )
    record(
        "billing.price.set",
        actor,
        item,
        facility=price_list.facility_id,
        detail={
            "price_list": price_list.code,
            "service": service.code,
            "price": as_str(price),
            "previous": as_str(current.price) if current is not None else None,
            "effective_from": effective_from.isoformat(),
            "approval_id": str(approval.pk) if approval else None,
        },
    )
    return item


@transaction.atomic
def request_price_change(
    *,
    price_list: PriceList,
    service: Service,
    price: Decimal | str,
    effective_from: date | None,
    actor: Any,
    reason: str,
) -> ApprovalRequest:
    """Maker side of a price change (DESIGN §7.9: price list change → finance manager)."""
    _ensure(actor, "billing.pricelist.manage", price_list.facility_id)
    amount = money(price)
    if amount < 0:
        raise ValidationError({"price": "A price cannot be negative."})
    start = effective_from or timezone.localdate()
    if start < timezone.localdate():
        raise ValidationError({"effective_from": "Prices cannot be changed for past dates."})
    if service.facility_id != price_list.facility_id or not price_list.active:
        raise ValidationError({"price_list": "Choose an active price list of this facility."})
    return approvals.request_approval(
        action=PRICE_CHANGE,
        facility=price_list.facility_id,
        requested_by=actor,
        payload={
            "price_list_id": str(price_list.pk),
            "service_id": str(service.pk),
            "price": as_str(amount),
            "effective_from": start.isoformat(),
        },
        required_permissions=APPROVER,
        reason=reason,
        resource=("billing.pricelist", str(price_list.pk)),
        amount=amount,
    )


def _execute_price_change(request: ApprovalRequest, approver: Any) -> None:
    data = request.payload
    start = date.fromisoformat(data["effective_from"])
    if start < timezone.localdate():
        start = timezone.localdate()  # approved after the requested start: never backdate
    _set_price(
        price_list=PriceList.objects.get(pk=data["price_list_id"]),
        service=Service.objects.get(pk=data["service_id"]),
        price=money(data["price"]),
        effective_from=start,
        actor=approver,
        approval=request,
    )


def register_executors() -> None:
    approvals.register_executor(PRICE_CHANGE, _execute_price_change)
    approvals.register_executor(NEW_SERVICE, _execute_new_service)


# --- Price resolution -----------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceQuote:
    service_id: Any
    amount: Decimal
    basis: str  # scheme | payer | cash
    price_list_id: Any


class NoPrice(ValidationError):
    pass


def _price_on(price_list: PriceList | None, service: Service, on: date) -> PriceListItem | None:
    if price_list is None:
        return None
    return (
        PriceListItem.objects.filter(price_list=price_list, service=service, effective_from__lte=on)
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=on))
        .order_by("-effective_from")
        .first()
    )


def resolve_price(service: Service, *, scheme: Any = None, on: date | None = None) -> PriceQuote:
    """Scheme-specific price → payer default price → facility cash price (DESIGN §10)."""
    day = on or timezone.localdate()
    lists = PriceList.objects.filter(facility_id=service.facility_id, active=True)
    candidates: list[tuple[str, PriceList | None]] = []
    if scheme is not None:
        candidates.append((PriceList.Basis.SCHEME, lists.filter(scheme=scheme).first()))
        candidates.append((PriceList.Basis.PAYER, lists.filter(payer_id=scheme.payer_id).first()))
    candidates.append(
        (PriceList.Basis.CASH, lists.filter(payer__isnull=True, scheme__isnull=True).first())
    )
    for basis, price_list in candidates:
        item = _price_on(price_list, service, day)
        if item is not None and price_list is not None:
            return PriceQuote(service.pk, money(item.price), basis, price_list.pk)
    raise NoPrice({"service": "This service has no price on that date; ask billing to add one."})
