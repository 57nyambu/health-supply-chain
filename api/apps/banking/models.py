"""Bank and card notifications (PAYMENTS.md §1, §4-6; ADR-075).

Phase 2 owns the payments ledger (``payments.ProviderTransaction``, ``Payment``). Until its
provider port is on ``main`` (SEAMS §5), ``apps.banking`` keeps what the banks and Pesapal
tell us here: each verified notification, normalised, with the provider's own status
query result. A notification alone never moves money: ``confirmed`` is set only after the
provider's query API agrees (PAYMENTS.md §1). Rows are never deleted.
"""

from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.ids import uuid7


class BankNotification(models.Model):
    class Provider(models.TextChoices):
        JENGA = "jenga", "Equity Bank (Jenga)"
        BUNI = "buni", "KCB (Buni)"
        PESAPAL = "pesapal", "Pesapal (cards)"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received, not yet confirmed"
        CONFIRMED = "confirmed", "Confirmed by the provider's query"
        FAILED = "failed", "Provider reports the payment failed"
        REVERSED = "reversed", "Provider reports the payment reversed"
        MISMATCH = "mismatch", "Notification and query disagree"
        UNKNOWN = "unknown", "Provider does not know the reference"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    provider = models.CharField(max_length=10, choices=Provider.choices)
    inbox_id = models.UUIDField(unique=True)  # integrations.WebhookInbox row
    reference = models.CharField(max_length=128, db_index=True)  # provider's own reference
    account_reference = models.CharField(max_length=100, blank=True)  # bill/invoice we gave
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="KES")
    channel = models.CharField(max_length=30, blank=True)  # CARD, MPESA, PESALINK…
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RECEIVED)
    confirmed_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    provider_status = models.CharField(max_length=60, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    # Normalised payload (payer names and phone numbers stay only in the encrypted inbox row).
    summary = EncryptedTextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "reference"], name="banking_notification_reference_once"
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.reference}"


class SettlementLine(models.Model):
    """A card-terminal (PDQ) settlement line from the acquirer's daily file (PAYMENTS.md §6.2)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    file_checksum = models.CharField(max_length=64, db_index=True)
    terminal_id = models.CharField(max_length=20)
    rrn = models.CharField(max_length=20)
    approval_code = models.CharField(max_length=12)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    settled_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["settled_on", "rrn"]
        constraints = [
            models.UniqueConstraint(
                fields=["terminal_id", "rrn", "approval_code"], name="banking_settlement_line_once"
            )
        ]

    def __str__(self) -> str:
        return f"{self.terminal_id}:{self.rrn}"
