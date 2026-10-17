"""PDQ settlement import (P3-CRD-01 acceptance 3, vendor part; PAYMENTS.md §6.2)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.banking import settlement
from apps.banking.models import SettlementLine

pytestmark = pytest.mark.django_db
HEADER = "terminal_id,rrn,approval_code,amount,settled_on"


def csv(*rows: str, header: str = HEADER) -> bytes:
    return ("\n".join([header, *rows]) + "\n").encode()


def test_lines_are_stored_once():
    first = settlement.import_file(
        csv(
            "SYN-T1,000000000001,A1B2C3,1500.00,2026-10-17",
            "SYN-T1,000000000002,D4E5F6,250,2026-10-17",
        )
    )
    assert (first.created, first.duplicates) == (2, 0)
    again = settlement.import_file(csv("SYN-T1,000000000001,A1B2C3,1500.00,2026-10-17"))
    assert (again.created, again.duplicates) == (0, 1)
    assert SettlementLine.objects.get(rrn="000000000002").amount == Decimal("250.00")


@pytest.mark.parametrize(
    "content, message",
    [
        (
            csv(
                "SYN-T1,1,A,10,2026-10-17",
                header="terminal_id,rrn,approval_code,amount,settled_on,card_number",
            ),
            "card numbers",
        ),
        (b"terminal_id,rrn\nX,1\n", "lacks columns"),
        (csv(), "no rows"),
        (csv("SYN-T1,1,A,abc,2026-10-17"), "not an amount"),
        (csv("SYN-T1,1,A,-5,2026-10-17"), "positive"),
        (csv("SYN-T1,1,A,5,17/10/2026"), "YYYY-MM-DD"),
        (csv("SYN-T1,,A,5,2026-10-17"), "rrn is empty"),
    ],
)
def test_bad_files_are_refused_whole(content, message):
    with pytest.raises(ValidationError, match=message):
        settlement.import_file(content)
    assert not SettlementLine.objects.exists()
