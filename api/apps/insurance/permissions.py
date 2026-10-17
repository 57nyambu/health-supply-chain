from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("insurance.payer.read", "View payers and schemes", S.LOW),
    P("insurance.payer.manage", "Set up payers and schemes", S.FINANCIAL, privileged=True),
    P("insurance.coverage.read", "View a patient's insurance cover", S.PHI),
    P("insurance.coverage.manage", "Record or end a patient's insurance cover", S.PHI),
    P("insurance.eligibility.check", "Check SHA and insurer eligibility", S.PHI),
    P("insurance.consent.request", "Request payer consent (OTP or biometrics)", S.PHI),
    P("insurance.preauth.request", "Request pre-authorisation", S.PHI),
    P(
        "insurance.preauth.clinical_signoff",
        "Clinically sign off pre-authorisation requests",
        S.PHI,
        requires_licence=True,
    ),
    P("insurance.claim.prepare", "Prepare and scrub claims", S.PHI),
    P("insurance.claim.submit", "Submit claims to payers", S.PHI),
    P("insurance.claim.cancel_submitted", "Cancel a submitted claim", S.PHI, privileged=True),
    P("insurance.remittance.post", "Post insurer remittances", S.FINANCIAL),
]
