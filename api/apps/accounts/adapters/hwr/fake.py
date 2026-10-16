"""Deterministic fake Health Worker Registry for dev, CI and demos (synthetic data only).

Registration numbers starting ``TEST-`` are active with a licence valid to the end of
next year; ``EXPIRED-`` are registered but expired; ``SUSP-`` are inactive; anything
else is unknown. PUIDs are derived from the regulator and number.
"""

import hashlib
from datetime import date

from django.utils import timezone

from . import PractitionerRecord


class FakeHealthWorkerRegistry:
    source = "hwr-fake"

    def lookup(self, regulator: str, registration_number: str) -> PractitionerRecord | None:
        number = registration_number.strip().upper()
        if not number.startswith(("TEST-", "EXPIRED-", "SUSP-")):
            return None
        digest = hashlib.sha256(f"{regulator}:{number}".encode()).hexdigest()[:10].upper()
        today = timezone.localdate()
        valid_to = date(today.year + 1, 12, 31)
        if number.startswith("EXPIRED-"):
            valid_to = date(today.year - 1, 12, 31)
        return PractitionerRecord(
            puid=f"PUID-{digest}",
            regulator=regulator,
            registration_number=number,
            licence_valid_to=valid_to,
            active=not number.startswith("SUSP-"),
        )
