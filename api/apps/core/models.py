from django.db import models


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
    response_body = models.BinaryField(blank=True, default=b"")
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
