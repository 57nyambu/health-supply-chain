"""Append-only, hash-chained audit trail (DESIGN §7.11, KE-DPA-06, KE-DHA-05).

Events form one chain per facility per day (facility 0 = system-level events).
Each event's hash covers its content and the previous event's hash; the first
event of a day links to the last event of the facility's previous chain. A
daily AuditAnchor freezes each finished chain in the database and in an
append-only file under DATA_DIR/audit-anchors/. Database triggers reject UPDATE
and DELETE on events and anchors; production also revokes those grants.
"""

import uuid

from django.db import models


class AuditEvent(models.Model):
    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        DENIED = "denied", "Denied"
        FAILURE = "failure", "Failure"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ts = models.DateTimeField()
    facility_id = models.BigIntegerField(default=0, help_text="0 for system-level events")
    chain_date = models.DateField()
    seq = models.PositiveIntegerField()
    actor_id = models.BigIntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=200, blank=True)
    workstation_id = models.CharField(max_length=64, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=64, blank=True)
    patient_id = models.UUIDField(null=True, blank=True)
    purpose = models.CharField(max_length=100, blank=True)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.SUCCESS)
    severity = models.CharField(max_length=10, default="info")
    detail = models.JSONField(default=dict, blank=True)
    prev_hash = models.CharField(max_length=64)
    hash = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["facility_id", "chain_date", "seq"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility_id", "chain_date", "seq"], name="audit_event_chain_position"
            ),
        ]
        indexes = [
            models.Index(fields=["ts"]),
            models.Index(fields=["actor_id", "ts"]),
            models.Index(fields=["patient_id", "ts"]),
            models.Index(fields=["action", "ts"]),
        ]

    def __str__(self) -> str:
        return f"{self.ts:%Y-%m-%d %H:%M:%S} {self.action} ({self.outcome})"


class AuditChainHead(models.Model):
    """Last position of each open chain; its row lock serialises appends per facility-day."""

    facility_id = models.BigIntegerField()
    chain_date = models.DateField()
    last_seq = models.PositiveIntegerField(default=0)
    last_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["facility_id", "chain_date"], name="audit_head_chain"),
        ]

    def __str__(self) -> str:
        return f"chain {self.facility_id}/{self.chain_date} at {self.last_seq}"


class AuditAnchor(models.Model):
    """The final hash and length of a finished day chain (also written to a file)."""

    facility_id = models.BigIntegerField()
    chain_date = models.DateField()
    last_hash = models.CharField(max_length=64)
    event_count = models.PositiveIntegerField()
    anchored_at = models.DateTimeField()

    class Meta:
        ordering = ["chain_date", "facility_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility_id", "chain_date"], name="audit_anchor_chain"
            ),
        ]

    def __str__(self) -> str:
        return f"anchor {self.facility_id}/{self.chain_date} ({self.event_count} events)"
