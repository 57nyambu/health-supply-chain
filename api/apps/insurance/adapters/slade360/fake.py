"""Deterministic Slade360 fake (synthetic data; outcomes in ``adapters/scripted.py``).

Capabilities follow INSURANCE.md §6's outline to be confirmed against the spec:
eligibility and benefits, pre-authorisation, claims with invoice lines, workflow states
(submitted, approved, rejected, paid) and remittances. No member-side consent step.
"""

from apps.insurance.adapters.scripted import ScriptedPayer
from apps.insurance.gateway import DiagnosisSystem, PayerCapabilities


class FakeSlade360Gateway(ScriptedPayer):
    code = "slade360"
    mode = "fake"
    prefix = "SYN-SLADE"

    def capabilities(self) -> PayerCapabilities:
        return PayerCapabilities(
            preauth=True,
            remittance_api=True,
            member_search=True,
            diagnosis_system=DiagnosisSystem.PER_SCHEME,
        )
