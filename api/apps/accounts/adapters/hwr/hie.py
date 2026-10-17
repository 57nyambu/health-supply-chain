"""HIE Health Worker Registry adapter (P3-SHA-01; DESIGN §7.10; KE-PRF-01, KE-DHA-04).

``GET /professionals?identification_type=registration_number&identification_number=&regulator=``
returns ``{message: {identifiers, licenses[], membership, …}}``. The spec names no PUID
field (GAP-HIE-005): we take ``identifiers.client_registry_id`` until UAT shows the PUID's
home. A practitioner is active when ``membership.is_active`` is 1; the licence is valid to
the latest ``licenses[].license_end``. An outage is reported as a validation message so
licence verification tells the admin to try again and changes nothing.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

from apps.interop.hie import mapping
from apps.interop.hie.client import HieClient
from apps.interop.hie.errors import HieError, HieNotFound

from . import PractitionerRecord


def record_from_message(
    regulator: str, registration_number: str, body: dict[str, Any]
) -> PractitionerRecord | None:
    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, dict):
        return None
    identifiers = message.get("identifiers") or {}
    membership = message.get("membership") or {}
    puid = mapping.text(identifiers.get("client_registry_id"))
    if not puid:
        return None
    ends = [mapping.parse_date(row.get("license_end")) for row in message.get("licenses") or []]
    valid = [d for d in ends if d is not None]
    return PractitionerRecord(
        puid=puid,
        regulator=regulator,
        registration_number=mapping.text(membership.get("registration_id")) or registration_number,
        licence_valid_to=max(valid) if valid else None,
        active=mapping.truthy(membership.get("is_active")),
    )


class HieHealthWorkerRegistry:
    source = "hwr-hie"

    def __init__(self, client: HieClient) -> None:
        self.client = client

    def lookup(self, regulator: str, registration_number: str) -> PractitionerRecord | None:
        if regulator not in mapping.REGULATORS:
            return None
        number = registration_number.strip().upper()
        try:
            body = self.client.get(
                "/professionals",
                params={
                    "identification_type": "registration_number",
                    "identification_number": number,
                    "regulator": regulator,
                },
                operation="lookup",
                integration="hie.health_worker_registry",
            )
        except HieNotFound:
            return None
        except HieError as exc:
            # Licence verification shows this to the admin; nothing is changed (P1 caller).
            raise ValidationError(
                {
                    "registration_number": "The Health Worker Registry is not answering. Try again later."
                }
            ) from exc
        return record_from_message(regulator, number, body)
