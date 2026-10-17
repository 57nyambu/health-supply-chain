"""SHA through the national HIE (eClaims REST) — INSURANCE.md §3; ADR-009, ADR-072.

Stage A (this module): eligibility, billable interventions, consent by OTP and fingerprint,
starting the payer visit. Claim session, dispatch, pre-authorisation and callbacks follow
with P3-SHA-03…06 (stage B, after Phase 2's visits and billing are on ``main``).
"""

from .gateway import ShaHieGateway

__all__ = ["ShaHieGateway"]
