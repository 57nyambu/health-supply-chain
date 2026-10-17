"""HIE Client Registry port (docs/integrations/INSURANCE.md §3.2; KE-DHA-04).

Reception looks a person up by identification type and number and gets the Client Registry
ID (CR ID) plus demographics to pre-fill registration, or nothing. The HIE call is
``GET /patients`` with ``identification_number`` and ``identification_type``.
``CLIENT_REGISTRY_MODE=fake`` (default) uses the deterministic fake; ``sandbox``/``live`` use
the HIE adapter (``hie.py``, P3-SHA-01) with the HIE credentials and refuse to start without
them. Every call is recorded in ``integrations.ExchangeLog`` with encrypted bodies.
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
    if mode in ("sandbox", "live"):
        from apps.interop.hie.client import HieClient, config_from_settings
        from apps.interop.hie.errors import HieConfigurationError

        from .hie import HieClientRegistry

        try:
            config = config_from_settings(
                mode, setting="CLIENT_REGISTRY_MODE", gap="P3-SHA-01, GAP-CR-001"
            )
        except HieConfigurationError as exc:
            raise ImproperlyConfigured(str(exc)) from exc
        return HieClientRegistry(HieClient(config))
    raise ImproperlyConfigured(f"CLIENT_REGISTRY_MODE={mode!r} is not one of fake, sandbox, live.")
