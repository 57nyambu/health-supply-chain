"""Which adapter serves a payer (``Payer.gateway``) in the configured mode (ADR-070).

    SHA_MODE        fake | sandbox | live   sha_hie (the HIE eClaims REST path)
    SHA_TRANSPORT   hie | fhir              fhir (AfyaLink bundles) arrives with P3-SHA-07
    SMART_MODE      fake | sandbox | live   sandbox/live refuse: no spec yet (GAP-SMART-001)
    SLADE360_MODE   fake | sandbox | live   sandbox/live refuse: no spec yet (GAP-SLADE-001)
    manual          always available        claim packs and manual entry

Fakes are process-wide singletons so their scripted state (claims sent, pre-authorisations)
survives between requests; ``use()`` swaps a gateway in tests.
"""

from __future__ import annotations

import threading

from django.conf import settings

from apps.insurance.gateway import ConfigurationError, PayerGateway

GATEWAY_CODES = ("sha_hie", "sha_fhir", "smart", "slade360", "mtiba", "manual")
_instances: dict[str, PayerGateway] = {}
_overrides: dict[str, PayerGateway] = {}
_lock = threading.Lock()


def _mode(name: str) -> str:
    mode = getattr(settings, name, "fake")
    if mode not in ("fake", "sandbox", "live"):
        raise ConfigurationError(f"{name}={mode!r} is not one of fake, sandbox, live.")
    return str(mode)


def _build(code: str) -> PayerGateway:
    if code in ("sha_hie", "sha_fhir"):
        if code == "sha_fhir" or getattr(settings, "SHA_TRANSPORT", "hie") == "fhir":
            raise ConfigurationError(
                "SHA through AfyaLink FHIR bundles arrives with P3-SHA-07; use SHA_TRANSPORT=hie."
            )
        from apps.interop.hie.client import HieClient, config_from_settings
        from apps.interop.hie.errors import HieConfigurationError

        from .sha_hie import ShaHieGateway

        try:
            config = config_from_settings(_mode("SHA_MODE"))
        except HieConfigurationError as exc:
            raise ConfigurationError(str(exc)) from exc
        return ShaHieGateway(HieClient(config))
    if code == "smart":
        if _mode("SMART_MODE") != "fake":
            raise ConfigurationError(
                "SMART_MODE=sandbox/live needs SMART's API specification and test credentials "
                "(provider integration agreement — owner action, GAP-SMART-001)."
            )
        from .smart.fake import FakeSmartGateway

        return FakeSmartGateway()
    if code == "slade360":
        if _mode("SLADE360_MODE") != "fake":
            raise ConfigurationError(
                "SLADE360_MODE=sandbox/live needs Slade360's API specification and test "
                "credentials (partner agreement — owner action, GAP-SLADE-001)."
            )
        from .slade360.fake import FakeSlade360Gateway

        return FakeSlade360Gateway()
    if code == "manual":
        from .manual import ManualGateway

        return ManualGateway()
    if code == "mtiba":
        raise ConfigurationError("M-TIBA is optional and not built (INSURANCE.md §7).")
    raise ConfigurationError(f"No payer gateway {code!r}.")


def gateway_for(code: str) -> PayerGateway:
    """The gateway for a ``Payer.gateway`` code. Raises ``ConfigurationError`` (naming the
    gap) when the mode needs a specification or credentials we do not have."""
    with _lock:
        if code in _overrides:
            return _overrides[code]
        if code not in _instances:
            _instances[code] = _build(code)
        return _instances[code]


def use(code: str, gateway: PayerGateway | None) -> None:
    """Replace (or with ``None`` restore) the gateway for ``code`` — tests and demos."""
    with _lock:
        if gateway is None:
            _overrides.pop(code, None)
        else:
            _overrides[code] = gateway


def reset() -> None:
    """Forget built gateways (after a settings change)."""
    with _lock:
        _instances.clear()
