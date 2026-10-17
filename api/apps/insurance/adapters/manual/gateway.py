from datetime import date

from apps.insurance.adapters.base import BaseGateway
from apps.insurance.gateway import (
    ClaimDraft,
    ClaimState,
    CoverageRef,
    DiagnosisSystem,
    EligibilityResult,
    EligibilityStatus,
    PayerCapabilities,
    PayerClaimStatus,
    PayerVisitHandle,
    SubmitResult,
    ValidationRejected,
)


class ManualGateway(BaseGateway):
    code = "manual"
    mode = "manual"

    def capabilities(self) -> PayerCapabilities:
        return PayerCapabilities(diagnosis_system=DiagnosisSystem.PER_SCHEME)

    def check_eligibility(self, coverage: CoverageRef, on: date) -> EligibilityResult:
        return EligibilityResult(
            EligibilityStatus.PENDING,
            message="This payer has no integration: confirm cover with the payer and record it.",
        )

    def submit_claim(
        self, handle: PayerVisitHandle, claim: ClaimDraft, idem_key: str
    ) -> SubmitResult:
        """The claim leaves as a pack the claims officer sends; "submitted" means the pack
        was generated. The same key always gives the same reference."""
        if not idem_key:
            raise ValidationRejected(["An idempotency key is required."])
        if not claim.lines:
            raise ValidationRejected(["The claim has no lines."])
        return SubmitResult(f"MANUAL-{claim.number}", ClaimState.SUBMITTED, "pack_generated")

    def find_claim(self, claim: ClaimDraft, idem_key: str) -> PayerClaimStatus:
        # Generating a pack never has an unknown outcome; staff record what the payer says.
        return PayerClaimStatus(f"MANUAL-{claim.number}", ClaimState.SUBMITTED, "pack_generated")
