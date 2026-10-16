"""Health Worker Registry (HWR) port (DESIGN §7.10, §15; KE-PRF-01, KE-DHA-04).

The HIE exposes a practitioner search (`/v1/practitioner-search`, see
docs/integrations/INSURANCE.md) whose request/response fields are not yet
documented to us (spec gap GAP-HWR-001). Until the real adapter lands in
P3-SHA-01 only the fake exists; any other HWR_MODE refuses to verify.
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
    raise ImproperlyConfigured(
        f"HWR_MODE={mode!r} is not available yet: the HIE practitioner-search adapter is P3-SHA-01."
    )
