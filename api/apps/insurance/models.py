"""Payers, schemes and coverage (DESIGN §11, docs/integrations/INSURANCE.md §1).

Created on `main` as the seam between the parallel lanes (ADR-024): Phase 2 references
``Scheme`` and ``Coverage`` (visit payer, price resolution, payment gates) read-only through
``apps.insurance.selectors``; the Phase 3 lane owns this app and adds eligibility, consent,
pre-authorisation, claims and remittances. Member numbers are personal data: encrypted at
rest, matched by blind index, masked on screen.
"""

from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.ids import uuid7
from apps.core.models import PhiModel


class Payer(models.Model):
    class Kind(models.TextChoices):
        SHA = "sha", "Social Health Authority"
        INSURER = "insurer", "Private insurer"
        EMPLOYER = "employer", "Employer or corporate"
        GOVERNMENT = "government", "Other government"
        OTHER = "other", "Other"

    class Gateway(models.TextChoices):
        SHA_HIE = "sha_hie", "SHA through the HIE (eClaims REST)"
        SHA_FHIR = "sha_fhir", "SHA through AfyaLink (FHIR bundle)"
        SMART = "smart", "SMART"
        SLADE360 = "slade360", "Slade360"
        MTIBA = "mtiba", "M-TIBA"
        MANUAL = "manual", "Manual claim pack"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Scheme(models.Model):
    class Kind(models.TextChoices):
        SHIF = "shif", "SHIF (Social Health Insurance Fund)"
        PHC = "phc", "Primary health care (PHC/UHC)"
        ECCIF = "eccif", "Emergency, chronic and critical illness (ECCIF)"
        POMSF = "pomsf", "Public officers' medical scheme (POMSF)"
        CORPORATE = "corporate", "Corporate scheme"
        INDIVIDUAL = "individual", "Individual or family cover"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    payer = models.ForeignKey(Payer, on_delete=models.PROTECT, related_name="schemes")
    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["payer__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["payer", "code"], name="insurance_scheme_code_per_payer"
            )
        ]

    def __str__(self) -> str:
        return f"{self.payer.name} — {self.name}"


class Coverage(PhiModel):
    """A patient's membership of a scheme. Phase 3 verifies it (eligibility checks)."""

    class Relationship(models.TextChoices):
        PRINCIPAL = "principal", "Principal member"
        DEPENDANT = "dependant", "Dependant"

    class Verification(models.TextChoices):
        UNVERIFIED = "unverified", "Not verified yet"
        VERIFIED = "verified", "Verified with the payer"
        FAILED = "failed", "Not eligible or not found"

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="coverages"
    )
    scheme = models.ForeignKey(Scheme, on_delete=models.PROTECT, related_name="coverages")
    member_number = EncryptedTextField()
    member_number_index = models.CharField(max_length=64, db_index=True)
    relationship = models.CharField(
        max_length=10, choices=Relationship.choices, default=Relationship.PRINCIPAL
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    verification = models.CharField(
        max_length=10, choices=Verification.choices, default=Verification.UNVERIFIED
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "scheme", "member_number_index"],
                condition=models.Q(active=True),
                name="insurance_one_active_coverage_per_member_number",
            )
        ]

    def __str__(self) -> str:
        return f"Coverage {self.pk}"
