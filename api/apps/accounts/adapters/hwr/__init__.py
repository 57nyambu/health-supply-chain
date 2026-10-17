"""Health Worker Registry (HWR) port (DESIGN §7.10, §15; KE-PRF-01, KE-DHA-04).

``HWR_MODE=fake`` (default) uses the deterministic fake; ``sandbox``/``live`` use the HIE
``GET /professionals`` adapter (``hie.py``, P3-SHA-01) with the HIE credentials, and refuse
to start without them.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class PractitionerRecord:
    puid: str
    regulator: str
    registration_number: str
    licence_valid_to: date | None
    active: bool


class HealthWorkerRegistry(Protocol):
    source: str

    def lookup(self, regulator: str, registration_number: str) -> PractitionerRecord | None:
        """The registry record for a regulator + registration number, or None."""
        ...


def get_registry() -> HealthWorkerRegistry:
    mode = settings.HWR_MODE
    if mode == "fake":
        from .fake import FakeHealthWorkerRegistry

        return FakeHealthWorkerRegistry()
    if mode in ("sandbox", "live"):
        from apps.interop.hie.client import HieClient, config_from_settings
        from apps.interop.hie.errors import HieConfigurationError

        from .hie import HieHealthWorkerRegistry

        try:
            config = config_from_settings(mode, setting="HWR_MODE", gap="P3-SHA-01, GAP-HWR-001")
        except HieConfigurationError as exc:
            raise ImproperlyConfigured(str(exc)) from exc
        return HieHealthWorkerRegistry(HieClient(config))
    raise ImproperlyConfigured(f"HWR_MODE={mode!r} is not one of fake, sandbox, live.")
