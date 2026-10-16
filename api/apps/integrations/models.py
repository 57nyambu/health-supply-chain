from django.conf import settings
from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.ids import uuid7
from apps.products.models import Product

User = settings.AUTH_USER_MODEL


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("email", "Email"),
        ("sms", "SMS"),
        ("push", "Push Notification"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} notification for {self.user}"


class InventoryAlert(models.Model):
    ALERT_TYPES = (
        ("low_stock", "Low Stock"),
        ("expired", "Expired Product"),
        ("restock", "Restock Needed"),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_alert_type_display()} alert for {self.product.name}"


class ExchangeLog(models.Model):
    """One call to an external system (api/CLAUDE.md "External adapters", DESIGN §8.2).

    Request and response bodies are encrypted (they carry identifiers and demographics);
    headers are stored redacted. Rows are append-only; retention is 2 years or with the
    claim/payment they support (DESIGN §8.4).
    """

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        NOT_FOUND = "not_found", "Not found"
        ERROR = "error", "Error"
        TIMEOUT = "timeout", "Timeout"
        UNAVAILABLE = "unavailable", "Unavailable"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey(
        "facilities.Facility", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    integration = models.CharField(max_length=50)
    operation = models.CharField(max_length=50)
    mode = models.CharField(max_length=10)
    correlation_id = models.CharField(max_length=64)
    started_at = models.DateTimeField()
    duration_ms = models.PositiveIntegerField()
    outcome = models.CharField(max_length=12, choices=Outcome.choices)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    provider_trace_id = models.CharField(max_length=100, blank=True)
    request_headers = models.JSONField(default=dict, blank=True)
    request_body = EncryptedTextField(blank=True, default="")
    response_body = EncryptedTextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["integration", "started_at"])]

    def __str__(self) -> str:
        return f"{self.integration}.{self.operation} {self.outcome}"
