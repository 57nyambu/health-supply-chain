"""HIE Client Registry port (docs/integrations/INSURANCE.md §3.2; KE-DHA-04).

Reception looks a person up by identification type and number and gets the Client Registry
ID (CR ID) plus demographics to pre-fill registration, or nothing. The HIE call is
``GET /patients`` with ``identification_number`` and ``identification_type``; its response
schema and the exact identification-type values are not yet documented to us (GAP-CR-001),
so only the fake exists until the HIE adapter lands with P3-SHA-01. Every call is recorded
in ``integrations.ExchangeLog`` with encrypted bodies.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Identification types the HIE registry is searched by (INSURANCE.md §3.2), in our names.
SEARCHABLE_TYPES = ("national_id", "maisha_namba", "alien_id", "refugee_id")


@dataclass(frozen=True)
class RegistryPerson:
    cr_id: str
    given_name: str
    middle_name: str
    family_name: str
    sex: str  # female | male | intersex
    date_of_birth: date | None
    identifiers: tuple[tuple[str, str], ...]  # (our identifier type, value)
    phone: str = ""


class RegistryUnavailable(Exception):
    """The registry did not answer (timeout, outage); reception carries on locally."""


class ClientRegistry(Protocol):
    mode: str

    def find(
        self, identifier_type: str, number: str, *, facility_id: int | None = None
    ) -> RegistryPerson | None:
        """The registry record for one identifier, None when there is none.

        Raises RegistryUnavailable when the registry cannot answer; never retries writes
        (this is a read, retried by the real adapter only on 429/5xx).
        """
        ...


def get_registry() -> ClientRegistry:
    mode = settings.CLIENT_REGISTRY_MODE
    if mode == "fake":
        from .fake import FakeClientRegistry

        return FakeClientRegistry()
    raise ImproperlyConfigured(
        f"CLIENT_REGISTRY_MODE={mode!r} is not available yet: the HIE adapter is P3-SHA-01 (GAP-CR-001)."
    )
