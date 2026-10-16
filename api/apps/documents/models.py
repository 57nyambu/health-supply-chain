"""Documents: metadata rows for encrypted objects (docs/integrations/STORAGE.md §4).

Bytes live in the backend named on the row (``local`` or ``s3``); the row carries the
wrapped data key and checksums. Documents are never hard-deleted: they are superseded,
and purged only by the retention job (DESIGN §8.4).
"""

from django.conf import settings
from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.ids import uuid7
from apps.core.sensitivity import SensitiveRecord


class Document(SensitiveRecord):
    class Category(models.TextChoices):
        LAB_REPORT = "lab_report", "Lab report"
        IMAGING_REPORT = "imaging_report", "Imaging report"
        CONSENT_FORM = "consent_form", "Consent form"
        CLAIM_ATTACHMENT = "claim_attachment", "Claim attachment"
        INVOICE_PDF = "invoice_pdf", "Invoice"
        RECEIPT_PDF = "receipt_pdf", "Receipt"
        CLAIM_FORM = "claim_form", "Claim form"
        DISCHARGE_SUMMARY = "discharge_summary", "Discharge summary"
        REFERRAL_LETTER = "referral_letter", "Referral letter"
        ID_SCAN = "id_scan", "Identity document scan"
        DSAR_EXPORT = "dsar_export", "Data subject request export"
        AUDIT_ANCHOR = "audit_anchor", "Audit anchor"
        OTHER = "other", "Other"

    class Backend(models.TextChoices):
        LOCAL = "local", "Local (data/)"
        S3 = "s3", "S3-compatible bucket"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey("facilities.Facility", on_delete=models.PROTECT, related_name="+")
    patient = models.ForeignKey(
        "patients.Patient",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    category = models.CharField(max_length=30, choices=Category.choices)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    sha256_plain = models.CharField(max_length=64)
    sha256_cipher = models.CharField(max_length=64)
    storage_backend = models.CharField(max_length=10, choices=Backend.choices)
    storage_key = models.CharField(max_length=255, unique=True)
    enc_kid = models.CharField(max_length=50, blank=True)
    enc_wrapped_key = models.CharField(max_length=200, blank=True)
    enc_nonce_prefix = models.CharField(max_length=24, blank=True)
    original_filename = EncryptedTextField(blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    retention_until = models.DateField(null=True, blank=True)
    legal_hold = models.BooleanField(default=False)
    superseded_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="supersedes"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "category"]),
            models.Index(fields=["storage_backend", "id"]),
        ]

    def __str__(self) -> str:
        return f"Document {self.pk}"

    @property
    def encrypted(self) -> bool:
        return bool(self.enc_kid)
