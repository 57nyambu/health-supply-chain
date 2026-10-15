"""Maker-checker approvals (DESIGN §7.9), reusable by billing, payments, pharmacy and access.

A caller registers an executor for its action and opens a request with the exact
payload the executor will receive. Approvers need the listed permission in the
request's facility; the requester can never approve, and nobody approves twice.
The executor runs inside the approving transaction, only after every required
approval, and only if the payload still matches the hash taken at request time.
"""

import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.access import policies
from apps.access.catalogue import is_known
from apps.access.models import ApprovalDecision, ApprovalRequest
from apps.audit.services import record

DEFAULT_TTL = timedelta(hours=72)

Executor = Callable[[ApprovalRequest, Any], None]
_executors: dict[str, Executor] = {}


def register_executor(action: str, executor: Executor) -> None:
    """Register the function that performs ``action`` once approved (called once per process)."""
    _executors[action] = executor


def payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _audit(event: str, request: ApprovalRequest, actor: Any, **detail: Any) -> None:
    record(
        f"access.approval.{event}",
        actor,
        request,
        facility=request.facility_id,
        detail={"action": request.action, **detail},
        severity="notice",
    )


@transaction.atomic
def request_approval(
    *,
    action: str,
    facility: Any,
    requested_by: Any,
    payload: dict[str, Any],
    required_permissions: list[str],
    reason: str,
    resource: tuple[str, str] | None = None,
    amount: Decimal | None = None,
    threshold_band: str = "",
    ttl: timedelta = DEFAULT_TTL,
) -> ApprovalRequest:
    if action not in _executors:
        raise ValidationError({"action": f"No executor is registered for {action!r}."})
    unknown = [code for code in required_permissions if not is_known(code)]
    if not required_permissions or unknown:
        raise ValidationError({"required_permissions": "List one or more known permission codes."})
    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    now = timezone.now()
    request = ApprovalRequest.objects.create(
        facility_id=getattr(facility, "pk", facility),
        action=action,
        required_permissions=list(required_permissions),
        payload=payload,
        payload_hash=payload_hash(payload),
        amount=amount,
        threshold_band=threshold_band,
        resource_type=resource[0] if resource else "",
        resource_id=str(resource[1]) if resource else "",
        reason=reason.strip(),
        requested_by=requested_by,
        requested_at=now,
        expires_at=now + ttl,
    )
    _audit(
        "requested", request, requested_by, required=list(required_permissions), band=threshold_band
    )
    return request


def _locked(request: ApprovalRequest) -> ApprovalRequest:
    return ApprovalRequest.objects.select_for_update().get(pk=request.pk)


def _close_if_stale(request: ApprovalRequest, actor: Any) -> dict[str, str] | None:
    """Close an expired or tampered request (persisted) and return the error to raise."""
    if request.status != ApprovalRequest.Status.PENDING:
        return {"status": f"The request is {request.status}."}
    now = timezone.now()
    if request.expires_at <= now:
        request.status = ApprovalRequest.Status.EXPIRED
        request.decided_at = now
        request.save(update_fields=["status", "decided_at"])
        _audit("expired", request, None)
        return {"status": "The request has expired."}
    if payload_hash(request.payload) != request.payload_hash:
        request.status = ApprovalRequest.Status.INVALIDATED
        request.decided_at = now
        request.save(update_fields=["status", "decided_at"])
        _audit("invalidated", request, actor, cause="payload_changed")
        return {"payload": "The request was changed after it was made; ask again."}
    return None


def _open_slot(request: ApprovalRequest, approver: Any) -> str:
    """The first still-unfilled required permission this approver holds."""
    if approver.pk == request.requested_by_id:
        raise PermissionDenied("You cannot approve your own request.")
    decisions = list(request.decisions.all())
    if any(d.approver_id == approver.pk for d in decisions):
        raise PermissionDenied("You have already decided on this request.")
    remaining: list[str] = [str(code) for code in request.required_permissions]
    for decision in decisions:
        if (
            decision.decision == ApprovalDecision.Decision.APPROVE
            and decision.permission in remaining
        ):
            remaining.remove(decision.permission)
    for code in remaining:
        if policies.has_permission(approver, code, facility=request.facility_id):
            return code
    raise PermissionDenied("You do not hold an approver permission this request still needs.")


def approve(request: ApprovalRequest, *, approver: Any, comment: str = "") -> ApprovalRequest:
    with transaction.atomic():
        request = _locked(request)
        error = _close_if_stale(request, approver)
        if error is None:
            slot = _open_slot(request, approver)
            now = timezone.now()
            ApprovalDecision.objects.create(
                request=request,
                approver=approver,
                permission=slot,
                decision=ApprovalDecision.Decision.APPROVE,
                comment=comment,
                decided_at=now,
            )
            approvals = request.decisions.filter(decision=ApprovalDecision.Decision.APPROVE).count()
            _audit(
                "approved",
                request,
                approver,
                permission=slot,
                step=approvals,
                of=len(request.required_permissions),
            )
            if approvals == len(request.required_permissions):
                request.status = ApprovalRequest.Status.APPROVED
                request.decided_at = now
                request.save(update_fields=["status", "decided_at"])
                _executors[request.action](request, approver)
                _audit("executed", request, approver)
    if error is not None:
        raise ValidationError(error)
    return request


def reject(request: ApprovalRequest, *, approver: Any, comment: str) -> ApprovalRequest:
    if not comment.strip():
        raise ValidationError({"comment": "Say why the request is rejected."})
    with transaction.atomic():
        request = _locked(request)
        error = _close_if_stale(request, approver)
        if error is None:
            slot = _open_slot(request, approver)
            now = timezone.now()
            ApprovalDecision.objects.create(
                request=request,
                approver=approver,
                permission=slot,
                decision=ApprovalDecision.Decision.REJECT,
                comment=comment.strip(),
                decided_at=now,
            )
            request.status = ApprovalRequest.Status.REJECTED
            request.decided_at = now
            request.save(update_fields=["status", "decided_at"])
            _audit("rejected", request, approver, permission=slot)
    if error is not None:
        raise ValidationError(error)
    return request


@transaction.atomic
def cancel(request: ApprovalRequest, *, by: Any) -> ApprovalRequest:
    request = _locked(request)
    if by.pk != request.requested_by_id:
        raise PermissionDenied("Only the requester can cancel a request.")
    if request.status != ApprovalRequest.Status.PENDING:
        raise ValidationError({"status": f"The request is {request.status}."})
    request.status = ApprovalRequest.Status.CANCELLED
    request.decided_at = timezone.now()
    request.save(update_fields=["status", "decided_at"])
    _audit("cancelled", request, by)
    return request


def expire_overdue() -> int:
    """Mark pending requests past their expiry as expired (beat task); each is audited."""
    expired = 0
    for request_id in ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.PENDING, expires_at__lte=timezone.now()
    ).values_list("pk", flat=True):
        with transaction.atomic():
            request = ApprovalRequest.objects.select_for_update().get(pk=request_id)
            if request.status == ApprovalRequest.Status.PENDING:
                request.status = ApprovalRequest.Status.EXPIRED
                request.decided_at = timezone.now()
                request.save(update_fields=["status", "decided_at"])
                _audit("expired", request, None)
                expired += 1
    return expired
