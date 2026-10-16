from django.db import models

from apps.core.fields import EncryptedBinaryField
from apps.core.ids import uuid7


class BaseModel(models.Model):
    """Abstract model with common fields for all models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Configuration(models.Model):
    """System-wide settings (e.g., company name, tax rate)."""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.key}: {self.value}"


class AuditLog(BaseModel):
    """Track critical actions (e.g., stock changes, user logins)."""

    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("LOGIN", "Login"),
    ]
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model = models.CharField(max_length=50)  # e.g., "Product", "Order"
    object_id = models.PositiveIntegerField()
    details = models.JSONField(default=dict)  # Store changed fields/old values

    def __str__(self):
        return f"{self.user} {self.action}d {self.model} #{self.object_id}"


class IdempotencyRecord(models.Model):
    """A stored response for an Idempotency-Key, replayed for 24 hours (DESIGN §17)."""

    class State(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    principal = models.CharField(max_length=80)
    key = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    request_hash = models.CharField(max_length=64)
    state = models.CharField(max_length=20, choices=State.choices, default=State.IN_PROGRESS)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    # Responses may contain personal data: encrypted at rest (DESIGN §8.2).
    response_body = EncryptedBinaryField(blank=True, default=b"")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["principal", "key"], name="core_idempotency_principal_key"
            ),
        ]

    def __str__(self):
        return f"{self.method} {self.path} ({self.state})"


class Sequence(models.Model):
    """Counter behind core.sequences.next_value (one row per facility, series and year)."""

    facility_id = models.BigIntegerField()
    name = models.CharField(max_length=40)
    year = models.PositiveSmallIntegerField()
    last_value = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facility_id", "name", "year"], name="core_sequence_series"
            ),
        ]

    def __str__(self):
        return f"{self.name} {self.year} @ facility {self.facility_id}: {self.last_value}"


class PhiModel(models.Model):
    """Base for patient data (api/CLAUDE.md): UUIDv7 key, facility scope, authorship, version.

    ``version`` supports optimistic concurrency: updates send the version they read and
    get 409 when someone else changed the row first.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey("facilities.Facility", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, related_name="+"
    )
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, related_name="+"
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True
