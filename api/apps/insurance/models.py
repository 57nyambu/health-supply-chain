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
from apps.core.sensitivity import SensitiveRecord


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
    # Phase 3: the payer's own reference for the member (SHA: the Client Registry ID it
    # returned on eligibility), used by consent and claims. Encrypted; never shown in full.
    payer_member_ref = EncryptedTextField(blank=True, default="")

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


# --- Phase 3: eligibility, consent, pre-authorisation, claims, remittances ------------------
# (INSURANCE.md §1; ADR-070). Visits and charges belong to Phase 2: they are referenced by
# UUID (``visit_id``, ``charge_id``) and read only through the seam selectors
# (``apps.insurance.seams``), never by foreign key, so this app does not depend on them.


class EligibilityCheck(PhiModel):
    """A snapshot of one eligibility check: who asked, when, what the payer said."""

    class Status(models.TextChoices):
        ELIGIBLE = "eligible", "Eligible"
        NOT_ELIGIBLE = "not_eligible", "Not eligible"
        INACTIVE = "inactive", "Cover inactive"
        NOT_FOUND = "not_found", "Member not found"
        PENDING = "pending_verification", "Payer not answering — verify later"

    coverage = models.ForeignKey(
        Coverage, on_delete=models.PROTECT, related_name="eligibility_checks"
    )
    gateway = models.CharField(max_length=20)
    mode = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=Status.choices)
    checked_on = models.DateField()
    # HMAC of the identifier the payer was asked about (never the value itself).
    request_hash = models.CharField(max_length=64)
    member_ref = EncryptedTextField(blank=True, default="")
    # IDs, codes, dates and flags only (scheme names and statuses as the payer sent them).
    summary = models.JSONField(default=dict, blank=True)
    message = models.CharField(max_length=255, blank=True)
    raw_payload = EncryptedTextField(blank=True, default="")
    trace_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["coverage", "-created_at"], name="insurance_elig_cov_idx")]


class PayerConsent(PhiModel):
    """A payer's authorisation of a visit (SHA consent token via OTP or biometrics, a SMART
    code…). Not a privacy consent (DESIGN §8.5). The token is a secret: encrypted, never
    logged, never sent to the browser."""

    class Method(models.TextChoices):
        OTP = "otp", "One-time password"
        BIOMETRIC = "biometric", "Fingerprint"
        CARD_OR_CODE = "card_or_code", "Member card or code"

    class Status(models.TextChoices):
        OTP_SENT = "otp_sent", "OTP sent to the member"
        AWAITING_BIOMETRIC = "awaiting_biometric", "Waiting for the fingerprint"
        AWAITING_CODE = "awaiting_code", "Waiting for the member code"
        AUTHORIZED = "authorized", "Authorised"
        AUTHORIZED_PENDING_VISIT = (
            "authorized_pending_visit",
            "Authorised; the visit opens after pre-authorisation",
        )
        VISIT_OPEN = "visit_open", "Visit open with the payer"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    OPEN_STATUSES = (
        Status.OTP_SENT,
        Status.AWAITING_BIOMETRIC,
        Status.AWAITING_CODE,
        Status.AUTHORIZED,
        Status.AUTHORIZED_PENDING_VISIT,
    )

    coverage = models.ForeignKey(Coverage, on_delete=models.PROTECT, related_name="consents")
    visit_id = models.UUIDField(null=True, blank=True, db_index=True)
    gateway = models.CharField(max_length=20)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=30, choices=Status.choices)
    service_type = models.CharField(max_length=20)
    service_codes = models.JSONField(default=list, blank=True)
    challenge_reference = models.CharField(max_length=100, blank=True)
    contact_id = models.CharField(max_length=40, blank=True)
    token_encrypted = EncryptedTextField(blank=True, default="")
    payer_visit_reference = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Payer consent {self.pk}"

    @property
    def has_token(self) -> bool:
        return bool(self.token_encrypted)


class PreAuthorization(PhiModel):
    class Kind(models.TextChoices):
        NORMAL = "normal", "Normal"
        ELECTIVE = "elective", "Elective"
        SURGICAL = "surgical", "Specialised — surgical"
        ONCOLOGY = "oncology", "Specialised — oncology"
        RENAL = "renal", "Specialised — renal"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending with the payer"
        APPROVED = "approved", "Approved"
        PARTIALLY_APPROVED = "partially_approved", "Partially approved"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        OUTCOME_UNKNOWN = "outcome_unknown", "Sent; outcome unknown — check status"

    coverage = models.ForeignKey(
        Coverage, on_delete=models.PROTECT, related_name="preauthorizations"
    )
    visit_id = models.UUIDField(null=True, blank=True, db_index=True)
    consent = models.ForeignKey(
        PayerConsent, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    intervention_code = models.CharField(max_length=40)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    raw_state = models.CharField(max_length=60, blank=True)
    service_from = models.DateField()
    service_to = models.DateField()
    estimated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    approved_amount = models.DecimalField(null=True, blank=True, max_digits=14, decimal_places=2)
    diagnosis_codes = models.JSONField(default=list, blank=True)
    payer_reference = models.CharField(max_length=100, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Pre-authorisation {self.pk}"


class Claim(PhiModel):
    """One claim per visit and payer coverage — the source of truth (INSURANCE.md §1)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready to submit"
        AWAITING_DOCUMENTS = "awaiting_documents", "Awaiting documents"
        AWAITING_PREAUTH = "awaiting_preauth", "Awaiting pre-authorisation"
        SUBMITTING = "submitting", "Submitting"
        OUTCOME_UNKNOWN = "outcome_unknown", "Sent; outcome unknown — check status"
        SUBMITTED = "submitted", "Submitted"
        IN_REVIEW = "in_review", "In review"
        QUERIED = "queried", "Queried by the payer"
        APPROVED = "approved", "Approved"
        PARTIALLY_APPROVED = "partially_approved", "Partially approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"
        SHORT_PAID = "short_paid", "Short-paid"
        PAYMENT_DECLINED = "payment_declined", "Payment declined"
        CANCELLED = "cancelled", "Cancelled"

    number = models.CharField(max_length=30)
    visit_id = models.UUIDField(db_index=True)
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="claims")
    coverage = models.ForeignKey(Coverage, on_delete=models.PROTECT, related_name="claims")
    payer = models.ForeignKey(Payer, on_delete=models.PROTECT, related_name="claims")
    scheme = models.ForeignKey(Scheme, on_delete=models.PROTECT, related_name="claims")
    consent = models.ForeignKey(
        PayerConsent, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    scenario = models.CharField(max_length=20, blank=True)  # SHA scenario 1-8 or "private"
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    raw_payer_state = models.CharField(max_length=60, blank=True)
    unknown_payer_state = models.BooleanField(default=False)
    billable_from = models.DateField()
    billable_to = models.DateField()
    total = models.DecimalField(default=0, max_digits=14, decimal_places=2)
    approved_amount = models.DecimalField(null=True, blank=True, max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(default=0, max_digits=14, decimal_places=2)
    payer_reference = models.CharField(max_length=100, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "number"], name="insurance_claim_number_per_facility"
            ),
            models.UniqueConstraint(
                fields=["visit_id", "coverage"],
                condition=~models.Q(status="cancelled"),
                name="insurance_one_open_claim_per_visit_cover",
            ),
        ]

    def __str__(self) -> str:
        return self.number


class ClaimLine(models.Model):
    """A billed service on a claim. Never deleted: removal is a flag with a reason."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="lines")
    charge_id = models.UUIDField(null=True, blank=True, db_index=True)
    service_code = models.CharField(max_length=40)
    payer_code = models.CharField(max_length=40, blank=True)
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    net = models.DecimalField(max_digits=14, decimal_places=2)
    serviced_from = models.DateField()
    serviced_to = models.DateField()
    diagnosis_codes = models.JSONField(default=list, blank=True)
    preauthorization = models.ForeignKey(
        PreAuthorization, null=True, blank=True, on_delete=models.PROTECT, related_name="lines"
    )
    active = models.BooleanField(default=True)
    removed_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["serviced_from", "created_at"]

    def __str__(self) -> str:
        return f"Claim line {self.pk}"


class ClaimDiagnosis(SensitiveRecord):
    """A diagnosis on a claim; sensitive categories (HIV, mental health…) stay flagged so
    claim screens redact them for staff without sensitive access (DESIGN §7.7)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="diagnoses")
    code = models.CharField(max_length=40)
    system = models.CharField(max_length=10, default="icd11")
    title = models.CharField(max_length=255)
    primary = models.BooleanField(default=False)
    intervention_code = models.CharField(max_length=40, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Claim diagnosis {self.pk}"


class ClaimAttachment(models.Model):
    class Kind(models.TextChoices):
        CLAIM_FORM = "claim_form", "Claim form"
        INVOICE = "invoice", "Itemised invoice"
        DISCHARGE_SUMMARY = "discharge_summary", "Discharge or case summary"
        LAB_RESULT = "lab_result", "Laboratory result"
        IMAGING_REPORT = "imaging_report", "Imaging report"
        PREAUTH_FORM = "preauth_form", "Pre-authorisation form or letter"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="attachments")
    document = models.ForeignKey("documents.Document", on_delete=models.PROTECT, related_name="+")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    added_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.PROTECT, related_name="+"
    )
    payer_reference = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Claim attachment {self.pk}"


class ClaimSubmission(models.Model):
    """Every call that changes a claim at the payer: attempts, keys, outcomes (append-only)."""

    class Operation(models.TextChoices):
        SYNC = "sync", "Sync claim session"
        SUBMIT = "submit", "Submit"
        DISCHARGE = "discharge", "Discharge (submits the claim)"
        CLOSE = "close", "Close / cancel"
        STATUS = "status", "Status query"
        RESUBMIT = "resubmit", "Resubmit after correction"

    class Outcome(models.TextChoices):
        PENDING = "pending", "Sending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        UNKNOWN = "unknown", "Outcome unknown"
        FAILED = "failed", "Failed before sending"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="submissions")
    operation = models.CharField(max_length=20, choices=Operation.choices)
    attempt = models.PositiveSmallIntegerField(default=1)
    idempotency_key = models.CharField(max_length=100)
    payload_hash = models.CharField(max_length=64)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.PENDING)
    payer_reference = models.CharField(max_length=100, blank=True)
    raw_state = models.CharField(max_length=60, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=60, blank=True)
    trace_id = models.CharField(max_length=100, blank=True)
    actor = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.PROTECT, related_name="+"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "operation", "idempotency_key"],
                name="insurance_submission_once_per_key",
            )
        ]

    def __str__(self) -> str:
        return f"Claim submission {self.pk}"


class ClaimStatusChange(models.Model):
    """Status history of a claim (append-only)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="history")
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    raw_payer_state = models.CharField(max_length=60, blank=True)
    reason_code = models.CharField(max_length=60, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.PROTECT, related_name="+"
    )
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["at"]

    def __str__(self) -> str:
        return f"{self.from_status} → {self.to_status}"


class Remittance(models.Model):
    """A payer's payment advice. Manual entries need a second person (maker-checker)."""

    class Source(models.TextChoices):
        API = "api", "Payer API"
        FILE = "file", "Remittance file"
        MANUAL = "manual", "Entered by staff"

    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Waiting for approval"
        POSTED = "posted", "Posted"
        REJECTED = "rejected", "Rejected by the checker"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    facility = models.ForeignKey("facilities.Facility", on_delete=models.PROTECT, related_name="+")
    payer = models.ForeignKey(Payer, on_delete=models.PROTECT, related_name="remittances")
    reference = models.CharField(max_length=100)
    paid_on = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    source = models.CharField(max_length=10, choices=Source.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL
    )
    raw_payload = EncryptedTextField(blank=True, default="")
    entered_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.PROTECT, related_name="+"
    )
    approved_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "payer", "reference"],
                name="insurance_remittance_reference_once",
            )
        ]

    def __str__(self) -> str:
        return self.reference


class RemittanceLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    remittance = models.ForeignKey(Remittance, on_delete=models.PROTECT, related_name="lines")
    claim = models.ForeignKey(
        Claim, null=True, blank=True, on_delete=models.PROTECT, related_name="remittance_lines"
    )
    claim_reference = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Remittance line {self.pk}"


class ShaTariffVersion(models.Model):
    """One imported edition of SHA's benefits and tariffs (immutable; one active)."""

    class Source(models.TextChoices):
        OFFICIAL = "official", "SHA Benefits and Tariffs spreadsheet"
        SYNTHETIC = "synthetic", "Synthetic (development and demos only)"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    label = models.CharField(max_length=60, unique=True)
    checksum = models.CharField(max_length=64, unique=True)
    source = models.CharField(max_length=10, choices=Source.choices)
    rows = models.PositiveIntegerField()
    active = models.BooleanField(default=False)
    imported_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    imported_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-imported_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["active"],
                condition=models.Q(active=True),
                name="insurance_one_active_tariff",
            )
        ]

    def __str__(self) -> str:
        return self.label


class ShaIntervention(models.Model):
    """An SHA intervention with its flags and tariff by KEPH level (None = not published)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    version = models.ForeignKey(
        ShaTariffVersion, on_delete=models.PROTECT, related_name="interventions"
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=255)
    sub_benefit_code = models.CharField(max_length=40, blank=True)
    fund = models.CharField(max_length=20)
    access_point = models.CharField(max_length=10)
    payment_mechanism = models.CharField(max_length=40)
    needs_preauth = models.BooleanField(default=False)
    needs_manual_preauth_approval = models.BooleanField(default=False)
    needs_doctor_authorization = models.BooleanField(default=False)
    level_2 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    level_3 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    level_4 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    level_5 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    level_6 = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    overall = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "code"], name="insurance_intervention_once_per_version"
            )
        ]

    def __str__(self) -> str:
        return self.code
