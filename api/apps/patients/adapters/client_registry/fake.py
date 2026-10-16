"""Deterministic fake Client Registry for dev, CI and demos — synthetic people only.

Known records are listed in ``RECORDS``. National ID ``99999999`` simulates an outage
(RegistryUnavailable); anything else is not in the registry. Every lookup is written to
``ExchangeLog`` (mode ``fake``) exactly as the real adapter will be.
"""

from datetime import date

from apps.integrations.exchange import exchange
from apps.integrations.models import ExchangeLog

from . import SEARCHABLE_TYPES, RegistryPerson, RegistryUnavailable

OUTAGE = ("national_id", "99999999")
RECORDS: dict[tuple[str, str], RegistryPerson] = {}


def _add(person: RegistryPerson) -> None:
    for key in person.identifiers:
        if key[0] in SEARCHABLE_TYPES:
            RECORDS[key] = person


_add(
    RegistryPerson(
        "CR-SYN-000001",
        "Achieng",
        "",
        "Syntheticus",
        "female",
        date(1988, 3, 14),
        (("national_id", "10000001"), ("sha_number", "SHA-SYN-0001")),
        "+254700100001",
    )
)
_add(
    RegistryPerson(
        "CR-SYN-000002",
        "Kiprono",
        "Test",
        "Fixture",
        "male",
        date(1975, 11, 2),
        (("national_id", "10000002"), ("maisha_namba", "500000000002")),
    )
)
_add(
    RegistryPerson(
        "CR-SYN-000003",
        "Halima",
        "",
        "Sample",
        "female",
        date(1996, 6, 30),
        (("alien_id", "2000003"),),
        "+254700100003",
    )
)
_add(
    RegistryPerson(
        "CR-SYN-000004", "Deng", "", "Placeholder", "male", None, (("refugee_id", "RF-300004"),)
    )
)


class FakeClientRegistry:
    mode = "fake"

    def find(
        self, identifier_type: str, number: str, *, facility_id: int | None = None
    ) -> RegistryPerson | None:
        key = (identifier_type, number.strip().upper())
        request = {"identification_type": identifier_type, "identification_number": key[1]}
        with exchange(
            "hie.client_registry", "find", mode=self.mode, facility_id=facility_id, request=request
        ) as call:
            if key == OUTAGE:
                call.outcome = ExchangeLog.Outcome.UNAVAILABLE
                raise RegistryUnavailable("The Client Registry did not answer.")
            person = RECORDS.get(key) if identifier_type in SEARCHABLE_TYPES else None
            call.outcome = ExchangeLog.Outcome.SUCCESS if person else ExchangeLog.Outcome.NOT_FOUND
            call.http_status = 200 if person else 404
            call.provider_trace_id = f"fake-{call.correlation_id[:12]}"
            call.response = person.__dict__ if person else None
            return person
