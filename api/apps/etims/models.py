"""KRA eTIMS transmissions (P3-TAX-01; DESIGN §10; KE-KRA-01; ADR-076).

One row per invoice or credit note sent to eTIMS through the facility's VSCU. Rows are
never deleted; a failed transmission waits in the offline queue and is retried (an invoice
number is sent at most once per document, so a retry cannot create a second sale).
"""

from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.ids import uuid7


class EtimsTransmission(models.Model):
    class Kind(models.TextChoices):
        SALE = "sale", "Sale (invoice)"
        CREDIT_NOTE = "credit_note", "Credit note"

    class Status(models.TextChoices):
        QUEUED = "queued", "Waiting to be sent"
        ACCEPTED = "accepted", "Accepted by eTIMS"
        REJECTED = "rejected", "Rejected by eTIMS (needs correction)"
        DUPLICATE = "duplicate", "eTIMS already has this invoice number (check its receipt)"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey("facilities.Facility", on_delete=models.PROTECT, related_name="+")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    source_id = models.UUIDField(db_index=True)  # billing invoice / credit note (Phase 2)
    trader_invoice_no = models.CharField(max_length=50)  # our invoice number (trdInvcNo)
    etims_invoice_no = models.PositiveBigIntegerField()  # invcNo, sequential per branch
    original_invoice_no = models.PositiveBigIntegerField(default=0)  # orgInvcNo (credit notes)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    # The exact JSON sent to the VSCU (amounts as written, never via float); encrypted at
    # rest like every raw integration payload; no customer names.
    payload_json = EncryptedTextField()
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    result_code = models.CharField(max_length=3, blank=True)
    result_message = models.CharField(max_length=200, blank=True)
    receipt_no = models.PositiveBigIntegerField(null=True, blank=True)  # rcptNo
    total_receipt_no = models.PositiveBigIntegerField(null=True, blank=True)  # totRcptNo
    internal_data = models.CharField(max_length=100, blank=True)  # intrlData
    receipt_signature = models.CharField(max_length=100, blank=True)  # rcptSign
    sdc_id = models.CharField(max_length=40, blank=True)
    mrc_no = models.CharField(max_length=40, blank=True)
    signed_at = models.CharField(max_length=14, blank=True)  # VSCURcptPbctDate, yyyyMMddhhmmss
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "kind", "source_id"], name="etims_one_transmission_per_document"
            ),
            models.UniqueConstraint(
                fields=["facility", "etims_invoice_no"], name="etims_invoice_no_once"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.trader_invoice_no}"
