"""Granting and revoking roles (DESIGN §7.6). Every change is audited.

Privileged roles (facility admin, medical superintendent, finance manager…) are
created ``pending_approval`` with a maker-checker request; they grant nothing until
a *different* facility administrator approves.
"""

from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.access import approvals, policies
from apps.access.models import ApprovalRequest, Role, RoleAssignment
from apps.audit.services import record

GRANT_ACTION = "access.assignment.grant"


def _ensure_may(actor: Any, code: str, facility_id: int) -> None:
    if not policies.has_permission(actor, code, facility=facility_id):
        raise PermissionDenied("You do not have permission to manage role assignments here.")


@transaction.atomic
def grant_role(
    *,
    granted_by: Any,
    user: Any,
    role: Role,
    facility: Any,
    reason: str,
    department: Any = None,
    ward: Any = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> RoleAssignment:
    """Grant ``role``. Privileged roles stay pending until a second facility admin approves."""
    facility_id = int(getattr(facility, "pk", facility))
    if not role.active:
        raise ValidationError({"role": "This role is not active."})
    if role.service_account:
        raise ValidationError({"role": "Service-account roles are not assigned to staff."})
    if department is not None and department.facility_id != facility_id:
        raise ValidationError({"department": "The department belongs to another facility."})
    if ward is not None and ward.facility_id != facility_id:
        raise ValidationError({"ward": "The ward belongs to another facility."})
    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    _ensure_may(granted_by, "access.assignment.manage", facility_id)
    if role.privileged:
        _ensure_may(granted_by, "access.assignment.grant_privileged", facility_id)

    status = (
        RoleAssignment.Status.PENDING_APPROVAL if role.privileged else RoleAssignment.Status.ACTIVE
    )
    assignment = RoleAssignment(
        user=user,
        role=role,
        facility_id=facility_id,
        department=department,
        ward=ward,
        valid_from=valid_from or timezone.now(),
        valid_to=valid_to,
        reason=reason.strip(),
        granted_by=granted_by,
        status=status,
    )
    assignment.full_clean(exclude=["approval", "approved_by", "revoked_by"])
    assignment.save()
    record(
        "access.assignment.requested" if role.privileged else "access.assignment.granted",
        granted_by,
        assignment,
        facility=facility_id,
        detail={"user_id": user.pk, "role": role.code, "privileged": role.privileged},
        severity="notice",
    )
    if role.privileged:
        request = approvals.request_approval(
            action=GRANT_ACTION,
            facility=facility_id,
            requested_by=granted_by,
            payload={"assignment_id": assignment.pk, "user_id": user.pk, "role": role.code},
            required_permissions=["access.assignment.grant_privileged"],
            reason=reason,
            resource=("access.roleassignment", str(assignment.pk)),
        )
        assignment.approval = request
        assignment.save(update_fields=["approval"])
    return assignment


def activate_privileged_grant(request: ApprovalRequest, approver: Any) -> None:
    """Approval executor: runs inside the approving transaction."""
    assignment = (
        RoleAssignment.objects.select_for_update()
        .select_related("role")
        .get(pk=request.payload["assignment_id"])
    )
    if assignment.status != RoleAssignment.Status.PENDING_APPROVAL:
        raise ValidationError({"status": "The assignment is no longer waiting for approval."})
    if approver.pk == assignment.user_id:
        raise PermissionDenied("You cannot approve a role for yourself.")
    assignment.status = RoleAssignment.Status.ACTIVE
    assignment.approved_by = approver
    assignment.save(update_fields=["status", "approved_by"])
    record(
        "access.assignment.granted",
        approver,
        assignment,
        facility=assignment.facility_id,
        detail={"user_id": assignment.user_id, "role": assignment.role.code, "privileged": True},
        severity="notice",
    )


@transaction.atomic
def revoke_assignment(
    assignment: RoleAssignment, *, revoked_by: Any, reason: str
) -> RoleAssignment:
    assignment = (
        RoleAssignment.objects.select_for_update().select_related("role").get(pk=assignment.pk)
    )
    _ensure_may(revoked_by, "access.assignment.manage", assignment.facility_id)
    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    if assignment.status == RoleAssignment.Status.REVOKED:
        return assignment
    assignment.status = RoleAssignment.Status.REVOKED
    assignment.revoked_at = timezone.now()
    assignment.revoked_by = revoked_by
    assignment.save(update_fields=["status", "revoked_at", "revoked_by"])
    record(
        "access.assignment.revoked",
        revoked_by,
        assignment,
        facility=assignment.facility_id,
        detail={"user_id": assignment.user_id, "role": assignment.role.code},
        severity="notice",
    )
    return assignment
