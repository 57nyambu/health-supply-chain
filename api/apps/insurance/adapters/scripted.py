"""Scripted, deterministic payer behaviour shared by the private-switch fakes (SMART,
Slade360) — synthetic data only, so the owner can demo every path before specs arrive.

Members — by the last two digits of the member number:
    97 not found · 96 not eligible · 98 cover inactive (lapsed) · 95 payer outage
    anything else: eligible
Member codes (SMART smart code / card read): ``1234`` accepted · ``0000`` wrong · ``1111`` expired
Pre-authorisation — by the cents of the estimated amount:
    .00 approved · .11 partially approved (90 %) · .22 declined (SYN-P01) · .44 pending
    .99 sent, answer lost, payer has it · .98 sent, answer lost, payer never got it
Claims — by the cents of the claim total (same outcome words):
    .00 approved · .11 partially approved (90 %) · .22 rejected (SYN-R01) · .33 queried (SYN-Q01)
    .44 in review · .99 outcome unknown, payer has it · .98 outcome unknown, payer never got it
Remittances: every approved claim is paid its approved amount on the next download.

State (submitted claims, pre-authorisations) lives in the process, keyed by idempotency key,
so a repeated submission with the same key returns the first answer (exactly once).
"""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from apps.insurance.adapters.base import BaseGateway
from apps.insurance.gateway import (
    AuthChallenge,
    AuthFailed,
    AuthMethod,
    AuthProof,
    BiometricContext,
    CancelReason,
    ChallengeStatus,
    ClaimDraft,
    ClaimRef,
    ClaimState,
    CoverageRef,
    EligibilityResult,
    EligibilityStatus,
    MemberMatch,
    MemberQuery,
    NotFound,
    PayerClaimStatus,
    PayerServiceCode,
    PayerVisitHandle,
    PreauthDraft,
    PreauthRef,
    PreauthState,
    PreauthStatus,
    RemittanceAdvice,
    RemittanceLineAdvice,
    SchemeStatus,
    Secret,
    SubmissionOutcomeUnknown,
    SubmitResult,
    TransientError,
    ValidationRejected,
    VisitRef,
)

MEMBER_OUTCOMES = {"97": "not_found", "96": "not_eligible", "98": "inactive", "95": "outage"}
GOOD_CODE, WRONG_CODE, EXPIRED_CODE = "1234", "0000", "1111"
PARTIAL = Decimal("0.90")
CENT = Decimal("0.01")

REJECTION = ("SYN-R01", "Diagnosis does not support the billed service (synthetic).")
QUERY = ("SYN-Q01", "Attach the discharge summary (synthetic).")
DECLINE = ("SYN-P01", "Service not covered under this benefit (synthetic).")

BENEFITS = [
    PayerServiceCode("SYN-PVT-CONS", "Synthetic consultation benefit", tariff=Decimal("2500.00")),
    PayerServiceCode("SYN-PVT-LAB", "Synthetic laboratory benefit", tariff=Decimal("4000.00")),
    PayerServiceCode(
        "SYN-PVT-SURG",
        "Synthetic surgical benefit",
        needs_preauth=True,
        tariff=Decimal("150000.00"),
    ),
    PayerServiceCode("SYN-PVT-IPDAY", "Synthetic inpatient day", tariff=None),
]


def member_outcome(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    return MEMBER_OUTCOMES.get(digits[-2:], "eligible") if len(digits) >= 2 else "eligible"


def cents(amount: Decimal) -> str:
    return f"{abs(amount).quantize(CENT):.2f}"[-2:]


def _partial(amount: Decimal) -> Decimal:
    return (amount * PARTIAL).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class _Claim:
    reference: str
    total: Decimal
    outcome: str
    approved: Decimal | None
    cancelled: bool = False
    paid: bool = False


class ScriptedPayer(BaseGateway):
    """Base for the private-switch fakes. Subclasses set ``code``, ``prefix`` and
    ``capabilities()``."""

    prefix = "SYN"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._claims: dict[str, _Claim] = {}  # by reference
        self._by_key: dict[str, str] = {}  # idempotency key → reference
        self._preauths: dict[str, PreauthStatus] = {}

    def _ref(self, kind: str, seed: str) -> str:
        return f"{self.prefix}-{kind}-{hashlib.sha256(seed.encode()).hexdigest()[:10].upper()}"

    # --- members ---

    def find_member(self, query: MemberQuery) -> list[MemberMatch]:
        number = query.number.reveal()
        if member_outcome(number) in ("not_found",):
            return []
        if member_outcome(number) == "outage":
            raise TransientError("The payer is not answering.")
        return [MemberMatch(member_ref=self._ref("M", number))]

    def check_eligibility(self, coverage: CoverageRef, on: date) -> EligibilityResult:
        number = coverage.member_number.reveal()
        outcome = member_outcome(number)
        if outcome == "outage":
            raise TransientError("The payer is not answering.")
        if outcome == "not_found":
            return EligibilityResult(
                EligibilityStatus.NOT_FOUND, message="The payer has no such member."
            )
        year = on.year
        active = outcome == "eligible"
        scheme = SchemeStatus(
            scheme_name=coverage.scheme_code,
            status="active" if active else ("lapsed" if outcome == "inactive" else "none"),
            active=active,
            valid_from=date(year, 1, 1),
            valid_to=date(year, 12, 31),
            reason="" if active else "Premium unpaid (synthetic)." if outcome == "inactive" else "",
        )
        status = {
            "eligible": EligibilityStatus.ELIGIBLE,
            "inactive": EligibilityStatus.INACTIVE,
            "not_eligible": EligibilityStatus.NOT_ELIGIBLE,
        }[outcome]
        message = {
            "eligible": "Eligible.",
            "inactive": "Cover lapsed: premium unpaid (synthetic).",
            "not_eligible": "The member has no benefit under this scheme.",
        }[outcome]
        return EligibilityResult(
            status,
            member_ref=self._ref("M", number),
            schemes=(scheme,),
            message=message,
            summary={"scheme": coverage.scheme_code, "status": scheme.status},
        )

    def list_billable(self, coverage: CoverageRef) -> list[PayerServiceCode]:
        return list(BENEFITS)

    # --- member code authorisation (SMART-style) ---

    def start_authorisation(
        self,
        coverage: CoverageRef,
        visit: VisitRef,
        codes: list[str],
        method: AuthMethod,
        *,
        contact_id: str = "",
        biometric: BiometricContext | None = None,
    ) -> AuthChallenge:
        if not self.capabilities().card_or_code_auth or method != AuthMethod.CARD_OR_CODE:
            raise self._unsupported(f"{method} authorisation")
        return AuthChallenge(
            AuthMethod.CARD_OR_CODE,
            ChallengeStatus.AWAITING_CODE,
            reference=self._ref("A", f"{coverage.coverage_id}:{visit.visit_id}"),
            service_codes=tuple(codes),
            service_type=visit.service_type,
        )

    def complete_authorisation(
        self, challenge: AuthChallenge, proof: AuthProof, coverage: CoverageRef, visit: VisitRef
    ) -> PayerVisitHandle:
        if challenge.method != AuthMethod.CARD_OR_CODE:
            raise self._unsupported(f"{challenge.method} authorisation")
        code = proof.member_code.reveal().strip() if proof.member_code else ""
        if not code:
            raise ValidationRejected(["Enter the member's code or read the card."])
        if code == EXPIRED_CODE:
            raise AuthFailed("The member code has expired. Ask the member for a new one.")
        if code != GOOD_CODE:
            raise AuthFailed("The member code is not correct.")
        return PayerVisitHandle(
            consent_token=Secret(self._ref("T", challenge.reference)),
            visit_reference=self._ref("V", challenge.reference),
        )

    # --- pre-authorisation ---

    def request_preauth(self, handle: PayerVisitHandle | None, preauth: PreauthDraft) -> PreauthRef:
        if not self.capabilities().preauth:
            raise self._unsupported("pre-authorisation")
        reference = self._ref("PA", preauth.preauth_id)
        outcome = cents(preauth.estimated_amount)
        state = {
            "00": PreauthStatus(
                reference, PreauthState.APPROVED, "approved", preauth.estimated_amount
            ),
            "11": PreauthStatus(
                reference,
                PreauthState.PARTIALLY_APPROVED,
                "partially_approved",
                _partial(preauth.estimated_amount),
            ),
            "22": PreauthStatus(
                reference, PreauthState.DECLINED, "declined", None, reason=DECLINE[1]
            ),
        }.get(outcome, PreauthStatus(reference, PreauthState.PENDING, "pending"))
        with self._lock:
            if outcome != "98":
                self._preauths.setdefault(reference, state)
        if outcome in ("98", "99"):
            raise SubmissionOutcomeUnknown("The payer did not confirm the request.")
        return PreauthRef(reference)

    def preauth_status(self, ref: PreauthRef) -> PreauthStatus:
        with self._lock:
            status = self._preauths.get(ref.reference)
        if status is None:
            raise NotFound("The payer has no such pre-authorisation.")
        return status

    def cancel_preauth(self, ref: PreauthRef, reason: str) -> PreauthStatus:
        current = self.preauth_status(ref)
        cancelled = PreauthStatus(
            ref.reference, PreauthState.CANCELLED, "cancelled", None, reason=reason[:100]
        )
        with self._lock:
            self._preauths[ref.reference] = cancelled
        return cancelled if current.state != PreauthState.CANCELLED else current

    # --- claims ---

    def _validate(self, claim: ClaimDraft) -> None:
        problems = []
        if not claim.lines:
            problems.append("The claim has no lines.")
        if sum((line.net for line in claim.lines), Decimal("0")) != claim.total:
            problems.append("The claim total does not equal the sum of its lines.")
        if not claim.diagnoses:
            problems.append("The claim has no diagnosis.")
        if problems:
            raise ValidationRejected(problems)

    def submit_claim(
        self, handle: PayerVisitHandle, claim: ClaimDraft, idem_key: str
    ) -> SubmitResult:
        if not idem_key:
            raise ValidationRejected(["An idempotency key is required."])
        with self._lock:
            known = self._by_key.get(idem_key)
            if known is not None:  # the same request again: answer as the first time
                stored = self._claims[known]
                return SubmitResult(stored.reference, ClaimState.SUBMITTED, "received")
        self._validate(claim)
        outcome = cents(claim.total)
        reference = self._ref("C", idem_key)
        approved = {"00": claim.total, "99": claim.total, "11": _partial(claim.total)}.get(outcome)
        with self._lock:
            if outcome != "98":  # .98: the request never reached the payer
                self._claims[reference] = _Claim(reference, claim.total, outcome, approved)
                self._by_key[idem_key] = reference
        if outcome in ("98", "99"):
            raise SubmissionOutcomeUnknown("The payer did not confirm the claim; check its status.")
        return SubmitResult(reference, ClaimState.SUBMITTED, "received")

    def claim_status(self, ref: ClaimRef) -> PayerClaimStatus:
        with self._lock:
            stored = self._claims.get(ref.reference)
        if stored is None:
            return PayerClaimStatus(ref.reference, ClaimState.UNKNOWN, "", found=False)
        if stored.cancelled:
            return PayerClaimStatus(stored.reference, ClaimState.CANCELLED, "cancelled")
        if stored.paid:
            return PayerClaimStatus(stored.reference, ClaimState.PAID, "paid", stored.approved)
        table = {
            "00": PayerClaimStatus(
                stored.reference, ClaimState.APPROVED, "approved", stored.approved
            ),
            "99": PayerClaimStatus(
                stored.reference, ClaimState.APPROVED, "approved", stored.approved
            ),
            "11": PayerClaimStatus(
                stored.reference,
                ClaimState.PARTIALLY_APPROVED,
                "partially_approved",
                stored.approved,
            ),
            "22": PayerClaimStatus(
                stored.reference, ClaimState.REJECTED, "rejected", reasons=(REJECTION,)
            ),
            "33": PayerClaimStatus(
                stored.reference, ClaimState.QUERIED, "queried", reasons=(QUERY,)
            ),
        }
        return table.get(
            stored.outcome, PayerClaimStatus(stored.reference, ClaimState.IN_REVIEW, "in_review")
        )

    def find_claim(self, claim: ClaimDraft, idem_key: str) -> PayerClaimStatus:
        """Look a claim up by the key it was sent with (used after an unknown outcome)."""
        with self._lock:
            reference = self._by_key.get(idem_key)
        if reference is None:
            return PayerClaimStatus("", ClaimState.UNKNOWN, "", found=False)
        return self.claim_status(ClaimRef(reference))

    def cancel_claim(self, handle: PayerVisitHandle, reason: CancelReason, text: str) -> None:
        with self._lock:
            for stored in self._claims.values():
                if stored.reference == handle.payer_claim_ref:
                    stored.cancelled = True
                    return
        raise NotFound("The payer has no such claim.")

    def fetch_remittances(self, since: datetime) -> list[RemittanceAdvice]:
        if not self.capabilities().remittance_api:
            raise self._unsupported("remittance download")
        today = timezone.localdate()
        advices = []
        with self._lock:
            for stored in self._claims.values():
                if stored.paid or stored.cancelled or stored.approved is None:
                    continue
                if stored.outcome not in ("00", "11", "99"):
                    continue
                stored.paid = True
                advices.append(
                    RemittanceAdvice(
                        reference=self._ref("R", stored.reference),
                        paid_on=today,
                        amount=stored.approved,
                        lines=(RemittanceLineAdvice(stored.reference, stored.approved),),
                    )
                )
        return advices
