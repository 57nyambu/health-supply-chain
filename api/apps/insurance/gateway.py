"""The payer port (docs/integrations/INSURANCE.md §2; ADR-070).

Every payer — SHA through the HIE, SMART, Slade360, the manual claim pack — is reached
through one ``PayerGateway``. The local ``Claim`` is the source of truth: services build
immutable snapshots (``CoverageRef``, ``VisitRef``, ``ClaimDraft``) from our tables and pass
them in; adapters translate them for their payer and return the results below. Adapters
never read or write our tables, never auto-retry a submission and raise only the errors of
the shared taxonomy, so the services and the contract suite
(``apps/insurance/tests/contract/``) treat every payer alike.

Secrets in these values (member numbers, consent tokens, OTPs) are wrapped in ``Secret`` so
that ``repr`` — and therefore logs, tracebacks and test output — never shows them.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

# --- Secrets ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Secret:
    """A value that must never be logged or shown: consent tokens, OTPs, member numbers."""

    value: str = field(repr=False)

    def __repr__(self) -> str:
        return "Secret([redacted])"

    def __str__(self) -> str:
        return "[redacted]"

    def __bool__(self) -> bool:
        return bool(self.value)

    def reveal(self) -> str:
        return self.value


# --- Errors (shared taxonomy) -------------------------------------------------------------


class GatewayError(Exception):
    """Base of every payer error. Messages are safe to show staff: no PHI, no secrets."""

    code = "payer_error"
    retryable = False

    def __init__(self, message: str = "", *, trace_id: str = "") -> None:
        super().__init__(message or self.__doc__ or self.code)
        self.trace_id = trace_id


class ConfigurationError(GatewayError):
    """The payer integration is not configured (mode, credentials or a spec gap)."""

    code = "payer_not_configured"


class Unsupported(GatewayError):
    """This payer does not offer the operation (see its capabilities)."""

    code = "payer_operation_unsupported"


class ValidationRejected(GatewayError):
    """The payer rejected the request as malformed or incomplete."""

    code = "payer_validation_rejected"

    def __init__(self, violations: list[str], *, trace_id: str = "") -> None:
        super().__init__(
            "The payer rejected the request: " + "; ".join(violations), trace_id=trace_id
        )
        self.violations = violations


class BusinessRuleRejected(GatewayError):
    """The payer refused on a business rule (benefit exhausted, not contracted…)."""

    code = "payer_business_rule"

    def __init__(self, rule: str, message: str, *, trace_id: str = "") -> None:
        super().__init__(message, trace_id=trace_id)
        self.rule = rule


class AuthFailed(GatewayError):
    """Our credentials, or the patient's consent proof (OTP, fingerprint), were refused."""

    code = "payer_auth_failed"


class Forbidden(GatewayError):
    """The payer does not allow this facility or credential to do this."""

    code = "payer_forbidden"


class NotFound(GatewayError):
    """The payer has no such member, authorisation, pre-authorisation or claim."""

    code = "payer_not_found"


class RateLimited(GatewayError):
    """The payer asked us to slow down."""

    code = "payer_rate_limited"
    retryable = True

    def __init__(self, retry_after: int | None = None, *, trace_id: str = "") -> None:
        super().__init__("The payer is limiting requests; try again shortly.", trace_id=trace_id)
        self.retry_after = retry_after


class TransientError(GatewayError):
    """The payer did not answer (outage, timeout before sending). Reads may be retried."""

    code = "payer_unavailable"
    retryable = True


class SubmissionOutcomeUnknown(GatewayError):
    """A write was sent but no reliable answer came back. Never retry blindly: query the
    payer for the claim (or authorisation) first and resubmit only if it is not there."""

    code = "payer_outcome_unknown"


# --- Capabilities -------------------------------------------------------------------------


class DiagnosisSystem(enum.StrEnum):
    ICD11 = "icd11"
    ICD10 = "icd10"
    PER_SCHEME = "per_scheme"


@dataclass(frozen=True)
class PayerCapabilities:
    incremental_claim_session: bool = False
    bundle_submission: bool = False
    consent_otp: bool = False
    consent_biometric: bool = False
    card_or_code_auth: bool = False
    preauth: bool = False
    remittance_api: bool = False
    callbacks: bool = False
    member_search: bool = False
    diagnosis_system: DiagnosisSystem = DiagnosisSystem.ICD11


# --- Inputs (snapshots built by services) --------------------------------------------------


@dataclass(frozen=True)
class CoverageRef:
    """What an adapter may know about a patient's cover."""

    coverage_id: str
    payer_code: str
    scheme_code: str
    scheme_kind: str
    member_number: Secret
    relationship: str = "principal"
    # The patient's HIE Client Registry ID (SHA) when we have it; otherwise the payer is
    # searched by ``identification`` (our identifier type, value).
    cr_id: str = ""
    identification: tuple[str, Secret] | None = None
    facility_code: str = ""  # the facility's registry code (FID) for facility scoping


@dataclass(frozen=True)
class MemberQuery:
    identifier_type: str  # our identifier type, e.g. "national_id", "cr_id", "sha_number"
    number: Secret
    facility_code: str = ""


@dataclass(frozen=True)
class Practitioner:
    regulator: str  # KMPDC | COC | NCK | PPB
    registration_number: str
    puid: str = ""


@dataclass(frozen=True)
class VisitRef:
    visit_id: str
    service_type: str  # outpatient | inpatient | capitation | emergency
    opened_at: datetime
    practitioner: Practitioner | None = None


class AuthMethod(enum.StrEnum):
    OTP = "otp"
    BIOMETRIC = "biometric"
    CARD_OR_CODE = "card_or_code"


@dataclass(frozen=True)
class BiometricContext:
    """What the facility's fingerprint workstation and agent supply for a biometric
    authorisation (read from the local hardware service by the browser; never stored)."""

    agent_id: Secret  # the eKYC agent's national ID
    device_os: str  # windows | android
    ekyc_provider_id: str
    work_station_id: str


@dataclass(frozen=True)
class AuthProof:
    otp: Secret | None = None  # passed straight through, never stored
    member_code: Secret | None = None  # SMART smart code / card reader output


@dataclass(frozen=True)
class ClaimDiagnosis:
    code: str
    system: str  # "icd11" | "icd10"
    title: str
    primary: bool = False
    intervention_code: str = ""


@dataclass(frozen=True)
class ClaimLineDraft:
    line_id: str  # our ClaimLine id, used as the payer's service identifier
    payer_code: str  # intervention / benefit code
    description: str
    quantity: Decimal
    unit_price: Decimal
    net: Decimal
    serviced_from: date
    serviced_to: date
    diagnosis_codes: tuple[str, ...] = ()
    preauth_reference: str = ""


@dataclass(frozen=True)
class ClaimAttachmentDraft:
    attachment_id: str
    kind: str  # claim_form | invoice | discharge_summary | lab_result | imaging_report | preauth_form | other
    filename: str
    content_type: str
    size: int


@dataclass(frozen=True)
class ClaimDraft:
    claim_id: str
    number: str
    visit: VisitRef
    coverage: CoverageRef
    billable_from: date
    billable_to: date
    total: Decimal
    lines: tuple[ClaimLineDraft, ...]
    diagnoses: tuple[ClaimDiagnosis, ...]
    attachments: tuple[ClaimAttachmentDraft, ...] = ()
    practitioners: tuple[Practitioner, ...] = ()
    interventions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreauthDraft:
    preauth_id: str
    coverage: CoverageRef
    visit: VisitRef | None
    intervention_code: str
    kind: str  # normal | elective | surgical | oncology | renal
    service_from: date
    service_to: date
    estimated_amount: Decimal
    diagnoses: tuple[ClaimDiagnosis, ...]
    practitioners: tuple[Practitioner, ...]
    attachments: tuple[ClaimAttachmentDraft, ...] = ()


class CancelReason(enum.StrEnum):
    """Reasons the HIE accepts on ``/claims/close`` (INSURANCE.md §3.5)."""

    WRONG_PATIENT = "wrong_patient"
    NO_SERVICE_GIVEN = "no_service_given"
    WRONG_BENEFIT = "wrong_benefit"
    EXPIRED_VISIT = "expired_visit"
    EXHAUSTED_BENEFIT = "exhausted_benefit"
    TIME_BARRED = "time_barred"
    OTHER = "other"


# --- Results -------------------------------------------------------------------------------


class EligibilityStatus(enum.StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    INACTIVE = "inactive"  # known member, cover lapsed or suspended
    NOT_FOUND = "not_found"
    PENDING = "pending_verification"  # the payer could not answer (degraded mode, DESIGN §16)


@dataclass(frozen=True)
class MemberMatch:
    member_ref: str  # payer's member reference (SHA: CR ID); not a secret, still PHI
    scheme_codes: tuple[str, ...] = ()
    relationship: str = ""


@dataclass(frozen=True)
class SchemeStatus:
    scheme_name: str
    status: str  # payer's raw status text, kept for the snapshot
    active: bool
    valid_from: date | None = None
    valid_to: date | None = None
    reason: str = ""
    possible_solution: str = ""


@dataclass(frozen=True)
class EligibilityResult:
    status: EligibilityStatus
    member_ref: str = ""
    schemes: tuple[SchemeStatus, ...] = ()
    message: str = ""  # safe for staff (payer reason or our explanation)
    biometrics_enforced: bool = False
    otp_allowed: bool = True
    trace_id: str = ""
    summary: dict[str, Any] = field(default_factory=dict)  # IDs and codes only


@dataclass(frozen=True)
class PayerServiceCode:
    code: str
    name: str
    fund: str = ""
    sub_benefit_code: str = ""
    access_point: str = ""  # OP | IP
    payment_mechanism: str = ""  # fee for service | capitation | per diem | …
    needs_preauth: bool = False
    needs_manual_preauth_approval: bool = False
    needs_doctor_authorization: bool = False
    tariff: Decimal | None = None  # None means "not published", never zero (KE-SHA-08)
    required_documents: tuple[str, ...] = ()


@dataclass(frozen=True)
class MaskedContact:
    contact_id: str
    masked: str  # e.g. "+254714***898" — as the payer masks it
    confirmed: bool = True


class ChallengeStatus(enum.StrEnum):
    CHOOSE_CONTACT = "choose_contact"  # OTP: confirm with the member which phone to use
    OTP_SENT = "otp_sent"
    AWAITING_BIOMETRIC = "awaiting_biometric"  # iframe shown, fingerprint pending
    AUTHORIZED = "authorized"
    AUTHORIZED_PENDING_VISIT = "authorized_pending_visit"
    REJECTED = "rejected"
    AWAITING_CODE = "awaiting_code"


@dataclass(frozen=True)
class AuthChallenge:
    method: AuthMethod
    status: ChallengeStatus
    reference: str = ""  # consent request id / authorisation guid (not a secret)
    consent_token: Secret | None = None  # biometric authorisations carry one from the start
    capture_url: str = ""  # biometric iframe; shown in our page, never stored
    expires_at: datetime | None = None
    contacts: tuple[MaskedContact, ...] = ()
    reason: str = ""  # e.g. biometrics not found → OTP allowed
    service_codes: tuple[str, ...] = ()
    service_type: str = ""


@dataclass(frozen=True)
class PayerVisitHandle:
    """The payer's side of a visit: the consent token every later call needs."""

    consent_token: Secret
    visit_reference: str = ""  # payer's visit / claim number (not a secret)
    payer_claim_ref: str = ""
    expires_at: datetime | None = None
    workflow_state: str = ""


@dataclass(frozen=True)
class PreauthRef:
    reference: str


class PreauthState(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PreauthStatus:
    reference: str
    state: PreauthState
    raw_state: str
    approved_amount: Decimal | None = None
    expires_on: date | None = None
    reason: str = ""


@dataclass(frozen=True)
class SyncReport:
    applied: tuple[str, ...] = ()  # operation names, e.g. "add_line:<line_id>"
    blockers: tuple[str, ...] = ()  # payer-reported reasons dispatch would fail


class ClaimState(enum.StrEnum):
    """Our mapping of payer claim states (INSURANCE.md §3.8, §9 queues)."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    QUERIED = "queried"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"
    PAID = "paid"
    PAYMENT_DECLINED = "payment_declined"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"  # raw state not recognised: stored raw and flagged


@dataclass(frozen=True)
class ClaimRef:
    reference: str


@dataclass(frozen=True)
class SubmitResult:
    reference: str
    state: ClaimState
    raw_state: str
    trace_id: str = ""


@dataclass(frozen=True)
class PayerClaimStatus:
    reference: str
    state: ClaimState
    raw_state: str
    approved_amount: Decimal | None = None
    reasons: tuple[tuple[str, str], ...] = ()  # (payer reason code, text)
    found: bool = True


@dataclass(frozen=True)
class RemittanceLineAdvice:
    claim_reference: str
    amount: Decimal


@dataclass(frozen=True)
class RemittanceAdvice:
    reference: str
    paid_on: date
    amount: Decimal
    lines: tuple[RemittanceLineAdvice, ...] = ()


class PayerEventKind(enum.StrEnum):
    CLAIM_STATUS = "claim_status"
    PREAUTH_STATUS = "preauth_status"
    AUTHORIZATION_STATUS = "authorization_status"
    REMITTANCE = "remittance"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PayerEvent:
    kind: PayerEventKind
    reference: str
    raw_state: str = ""


# --- The port ------------------------------------------------------------------------------


@runtime_checkable
class PayerGateway(Protocol):
    code: str
    mode: str

    def capabilities(self) -> PayerCapabilities: ...

    def find_member(self, query: MemberQuery) -> list[MemberMatch]: ...

    def check_eligibility(self, coverage: CoverageRef, on: date) -> EligibilityResult: ...

    def list_billable(self, coverage: CoverageRef) -> list[PayerServiceCode]: ...

    def start_authorisation(
        self,
        coverage: CoverageRef,
        visit: VisitRef,
        codes: list[str],
        method: AuthMethod,
        *,
        contact_id: str = "",
        biometric: BiometricContext | None = None,
    ) -> AuthChallenge: ...

    def pending_authorisations(self, coverage: CoverageRef) -> list[AuthChallenge]: ...

    def authorisation_status(self, challenge: AuthChallenge) -> AuthChallenge: ...

    def reject_authorisation(self, challenge: AuthChallenge) -> None: ...

    def complete_authorisation(
        self, challenge: AuthChallenge, proof: AuthProof, coverage: CoverageRef, visit: VisitRef
    ) -> PayerVisitHandle: ...

    def request_preauth(
        self, handle: PayerVisitHandle | None, preauth: PreauthDraft
    ) -> PreauthRef: ...

    def preauth_status(self, ref: PreauthRef) -> PreauthStatus: ...

    def cancel_preauth(self, ref: PreauthRef, reason: str) -> PreauthStatus: ...

    def sync_claim(self, handle: PayerVisitHandle, claim: ClaimDraft) -> SyncReport: ...

    def submit_claim(
        self, handle: PayerVisitHandle, claim: ClaimDraft, idem_key: str
    ) -> SubmitResult: ...

    def claim_status(self, ref: ClaimRef) -> PayerClaimStatus: ...

    def find_claim(self, claim: ClaimDraft, idem_key: str) -> PayerClaimStatus:
        """After ``SubmissionOutcomeUnknown``: does the payer have this claim? (by our key
        or claim number — we never received its reference). ``found=False`` means it is
        safe to submit again with the same key."""
        ...

    def cancel_claim(self, handle: PayerVisitHandle, reason: CancelReason, text: str) -> None: ...

    def fetch_remittances(self, since: datetime) -> list[RemittanceAdvice]: ...

    def parse_callback(self, raw_body: str, headers: dict[str, str]) -> PayerEvent: ...


# --- Shared state mapping ------------------------------------------------------------------

# Raw SHA claim states seen in AfyaLink's checklist (INSURANCE.md §3.8); the HIE workflow
# states are mapped by the adapter. Unknown states map to UNKNOWN (stored raw, flagged).
SHA_CLAIM_STATES: dict[str, ClaimState] = {
    "queued": ClaimState.SUBMITTED,
    "approved": ClaimState.APPROVED,
    "rejected": ClaimState.REJECTED,
    "in-review": ClaimState.IN_REVIEW,
    "clinical-review": ClaimState.IN_REVIEW,
    "sent-for-payment-processing": ClaimState.APPROVED,
    "sent-to-surveillance": ClaimState.IN_REVIEW,
    "payment-completed": ClaimState.PAID,
    "payment-declined": ClaimState.PAYMENT_DECLINED,
}


def map_state(raw: str, table: dict[str, ClaimState]) -> ClaimState:
    return table.get(raw.strip().lower(), ClaimState.UNKNOWN)
