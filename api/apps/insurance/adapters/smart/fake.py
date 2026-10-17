"""Deterministic SMART fake (synthetic data; outcomes in ``adapters/scripted.py``).

Capabilities follow INSURANCE.md §5's outline to be confirmed against the spec: member
identification by card or member-generated code, benefits, visit authorisation,
pre-authorisation for some services, itemised claims, status and settlement.
"""

from apps.insurance.adapters.scripted import ScriptedPayer
from apps.insurance.gateway import DiagnosisSystem, PayerCapabilities


class FakeSmartGateway(ScriptedPayer):
    code = "smart"
    mode = "fake"
    prefix = "SYN-SMART"

    def capabilities(self) -> PayerCapabilities:
        return PayerCapabilities(
            card_or_code_auth=True,
            preauth=True,
            remittance_api=True,
            member_search=True,
            diagnosis_system=DiagnosisSystem.PER_SCHEME,
        )
