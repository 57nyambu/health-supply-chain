"""Defaults for payer adapters: every operation a payer does not offer raises ``Unsupported``
(the services check ``capabilities()`` first, so this is a guard, not a code path)."""

from __future__ import annotations

from datetime import date, datetime

from apps.insurance.gateway import (
    AuthChallenge,
    AuthMethod,
    AuthProof,
    BiometricContext,
    CancelReason,
    ClaimDraft,
    ClaimRef,
    CoverageRef,
    EligibilityResult,
    MemberMatch,
    MemberQuery,
    PayerCapabilities,
    PayerClaimStatus,
    PayerEvent,
    PayerEventKind,
    PayerServiceCode,
    PayerVisitHandle,
    PreauthDraft,
    PreauthRef,
    PreauthStatus,
    RemittanceAdvice,
    SubmitResult,
    SyncReport,
    Unsupported,
    VisitRef,
)


class BaseGateway:
    code = "base"
    mode = "fake"

    def _unsupported(self, operation: str) -> Unsupported:
        return Unsupported(f"{self.code} does not support {operation}.")

    def capabilities(self) -> PayerCapabilities:
        return PayerCapabilities()

    def find_member(self, query: MemberQuery) -> list[MemberMatch]:
        raise self._unsupported("member search")

    def check_eligibility(self, coverage: CoverageRef, on: date) -> EligibilityResult:
        raise self._unsupported("eligibility checks")

    def list_billable(self, coverage: CoverageRef) -> list[PayerServiceCode]:
        raise self._unsupported("benefit lists")

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
        raise self._unsupported(f"{method} authorisation")

    def pending_authorisations(self, coverage: CoverageRef) -> list[AuthChallenge]:
        return []

    def authorisation_status(self, challenge: AuthChallenge) -> AuthChallenge:
        return challenge

    def reject_authorisation(self, challenge: AuthChallenge) -> None:
        raise self._unsupported("rejecting authorisations")

    def complete_authorisation(
        self, challenge: AuthChallenge, proof: AuthProof, coverage: CoverageRef, visit: VisitRef
    ) -> PayerVisitHandle:
        raise self._unsupported("visit authorisation")

    def request_preauth(self, handle: PayerVisitHandle | None, preauth: PreauthDraft) -> PreauthRef:
        raise self._unsupported("pre-authorisation")

    def preauth_status(self, ref: PreauthRef) -> PreauthStatus:
        raise self._unsupported("pre-authorisation")

    def cancel_preauth(self, ref: PreauthRef, reason: str) -> PreauthStatus:
        raise self._unsupported("pre-authorisation")

    def sync_claim(self, handle: PayerVisitHandle, claim: ClaimDraft) -> SyncReport:
        return SyncReport()  # batch payers validate at submission

    def submit_claim(
        self, handle: PayerVisitHandle, claim: ClaimDraft, idem_key: str
    ) -> SubmitResult:
        raise self._unsupported("claim submission")

    def claim_status(self, ref: ClaimRef) -> PayerClaimStatus:
        raise self._unsupported("claim status")

    def find_claim(self, claim: ClaimDraft, idem_key: str) -> PayerClaimStatus:
        raise self._unsupported("claim lookup")

    def cancel_claim(self, handle: PayerVisitHandle, reason: CancelReason, text: str) -> None:
        raise self._unsupported("claim cancellation")

    def fetch_remittances(self, since: datetime) -> list[RemittanceAdvice]:
        raise self._unsupported("remittance download")

    def parse_callback(self, raw_body: str, headers: dict[str, str]) -> PayerEvent:
        return PayerEvent(PayerEventKind.UNKNOWN, "")
