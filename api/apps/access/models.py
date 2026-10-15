"""Access-control data: catalogue, roles, scoped assignments, approvals (DESIGN §7)."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.access.catalogue import Sensitivity
from apps.access.roles import ChartAccess


class Permission(models.Model):
    """Database mirror of a code-defined PermissionDef (synced by ``sync_access``)."""

    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)
    sensitivity = models.CharField(max_length=20, choices=[(s.value, s.value) for s in Sensitivity])
    requires_licence = models.BooleanField(default=False)
    privileged = models.BooleanField(default=False)
    active = models.BooleanField(
        default=True, help_text="False once the code is removed from the catalogue"
    )

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Role(models.Model):
    CHART_CHOICES = [(level.value, level.value) for level in ChartAccess]

    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    chart_baseline = models.CharField(
        max_length=20, choices=CHART_CHOICES, default=ChartAccess.NONE
    )
    chart_care_team = models.CharField(
        max_length=20, choices=CHART_CHOICES, default=ChartAccess.NONE
    )
    privileged = models.BooleanField(
        default=False, help_text="Granting it needs a second facility admin"
    )
    mfa_required = models.BooleanField(default=False)
    addon = models.BooleanField(
        default=False, help_text="Supervisor add-on assigned on top of a base role"
    )
    requires_cosign = models.BooleanField(default=False)
    service_account = models.BooleanField(default=False)
    is_system = models.BooleanField(default=True, help_text="Seeded from apps/access/roles.py")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RoleAssignment(models.Model):
    """A role held in a facility, optionally narrowed to a department or ward, for a period.

    Privileged roles start ``pending_approval`` and become ``active`` only when a second
    facility administrator approves the linked ApprovalRequest (DESIGN §7.6).
    """

    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Pending approval"
        ACTIVE = "active", "Active"
        REJECTED = "rejected", "Rejected"
        REVOKED = "revoked", "Revoked"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.PROTECT, related_name="role_assignments"
    )
    department = models.ForeignKey(
        "facilities.Department", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    ward = models.ForeignKey(
        "facilities.Ward", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    reason = models.CharField(max_length=255, blank=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    approval = models.ForeignKey(
        "access.ApprovalRequest", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_to__gt=models.F("valid_from")),
                name="access_assignment_valid_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role.code} @ facility {self.facility_id}"


class ApprovalRequest(models.Model):
    """Generic maker-checker request (DESIGN §7.9).

    ``payload`` holds the parameters the approved action will use; ``payload_hash``
    is fixed at request time, so any later change to the payload invalidates the
    request. ``required_permissions`` lists the permission each approval must come
    from (one approver per entry, never the requester, never the same person twice).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        INVALIDATED = "invalidated", "Invalidated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.PROTECT, related_name="approval_requests"
    )
    action = models.CharField(
        max_length=100, help_text="Executor key, e.g. access.assignment.grant"
    )
    required_permissions = models.JSONField(
        help_text="Permission codes, one approval needed per entry"
    )
    payload = models.JSONField()
    payload_hash = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    threshold_band = models.CharField(max_length=20, blank=True)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=64, blank=True)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approval_requests"
    )
    requested_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [models.Index(fields=["facility", "status"])]

    def __str__(self) -> str:
        return f"{self.action} ({self.status})"


class ApprovalDecision(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"

    request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, related_name="decisions")
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    permission = models.CharField(
        max_length=100, help_text="The required permission this decision fills"
    )
    decision = models.CharField(max_length=10, choices=Decision.choices)
    comment = models.CharField(max_length=255, blank=True)
    decided_at = models.DateTimeField()

    class Meta:
        ordering = ["decided_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "approver"], name="access_one_decision_per_approver"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.decision} by {self.approver_id}"
