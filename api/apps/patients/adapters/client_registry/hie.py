"""HIE Client Registry adapter (P3-SHA-01; INSURANCE.md §3.2; KE-DHA-04).

``GET /patients?identification_number=&identification_type=`` returns a ``Member``; its
``id`` is the Client Registry ID (GAP-HIE-003 until UAT confirms). A 404 is "not in the
registry"; outages and timeouts raise ``RegistryUnavailable`` so reception carries on
locally. The HIE has no Maisha Namba type yet (GAP-HIE-004): such lookups report the
registry as unavailable rather than claiming the person is unknown.
"""

from __future__ import annotations

from typing import Any

from apps.interop.hie import mapping
from apps.interop.hie.client import HieClient
from apps.interop.hie.errors import HieError, HieNotFound

from . import RegistryPerson, RegistryUnavailable


def person_from_member(member: dict[str, Any]) -> RegistryPerson | None:
    cr_id = mapping.text(member.get("id"))
    if not cr_id:
        return None
    identifiers: list[tuple[str, str]] = []
    rows = [member, *(member.get("other_identifications") or [])]
    for row in rows:
        ours = mapping.FROM_HIE_ID_TYPES.get(mapping.text(row.get("identification_type")))
        number = mapping.text(row.get("identification_number"))
        if ours and ours != "cr_id" and number and (ours, number) not in identifiers:
            identifiers.append((ours, number))
    return RegistryPerson(
        cr_id=cr_id,
        given_name=mapping.text(member.get("first_name")),
        middle_name=mapping.text(member.get("middle_name")),
        family_name=mapping.text(member.get("last_name")),
        sex=mapping.sex(member.get("gender")),
        date_of_birth=mapping.parse_date(member.get("date_of_birth")),
        identifiers=tuple(identifiers),
        phone=mapping.text(member.get("phone")),
    )


class HieClientRegistry:
    def __init__(self, client: HieClient) -> None:
        self.client = client
        self.mode = client.mode

    def find(
        self, identifier_type: str, number: str, *, facility_id: int | None = None
    ) -> RegistryPerson | None:
        hie_type = mapping.hie_id_type(identifier_type)
        if hie_type is None:
            raise RegistryUnavailable(
                "The national Client Registry cannot be searched by this identifier yet."
            )
        try:
            member = self.client.get(
                "/patients",
                params={"identification_number": number.strip(), "identification_type": hie_type},
                operation="find",
                integration="hie.client_registry",
                facility_id=facility_id,
            )
        except HieNotFound:
            return None
        except HieError as exc:
            raise RegistryUnavailable("The Client Registry did not answer.") from exc
        return person_from_member(member) if isinstance(member, dict) else None
