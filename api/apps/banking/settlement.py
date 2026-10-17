"""Card-terminal (PDQ) settlement files (PAYMENTS.md §6.2; P3-CRD-01).

Counter card payments stay on the bank's standalone terminals; the cashier records the
terminal ID, approval code, RRN and amount (stage B, Phase 2's payment screen). The
acquirer's daily settlement file confirms them. Acquirers' file layouts are not published
to us (GAP-PDQ-001), so the importer reads our documented CSV layout (``COLUMNS``) — an
acquirer's export is mapped to it once we see one. No card number is accepted or stored.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.banking.models import SettlementLine

COLUMNS = ("terminal_id", "rrn", "approval_code", "amount", "settled_on")
CARD_LIKE = ("pan", "card_number", "card", "masked_pan")


@dataclass(frozen=True)
class SettlementImport:
    created: int
    duplicates: int
    checksum: str


@dataclass(frozen=True)
class _Line:
    terminal_id: str
    rrn: str
    approval_code: str
    amount: Decimal
    settled_on: date


def _row(raw: dict[str, str], line: int) -> _Line:
    values = {k: (raw.get(k) or "").strip() for k in COLUMNS}
    for column in COLUMNS:
        if not values[column]:
            raise ValidationError(f"Line {line}: {column} is empty.")
    try:
        amount = Decimal(values["amount"].replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValidationError(f"Line {line}: amount is not an amount.") from exc
    if amount <= 0:
        raise ValidationError(f"Line {line}: amount must be positive.")
    try:
        settled_on = date.fromisoformat(values["settled_on"])
    except ValueError as exc:
        raise ValidationError(f"Line {line}: settled_on must be YYYY-MM-DD.") from exc
    return _Line(
        values["terminal_id"][:20],
        values["rrn"][:20],
        values["approval_code"][:12],
        amount,
        settled_on,
    )


@transaction.atomic
def import_file(content: bytes) -> SettlementImport:
    """Validate the whole file, then store new lines; lines already imported are skipped."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("The settlement file must be UTF-8 CSV.") from exc
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip().lower() for h in reader.fieldnames or []]
    if any(h in CARD_LIKE for h in headers):
        raise ValidationError(
            "The file contains card numbers; remove that column before importing."
        )
    missing = [c for c in COLUMNS if c not in headers]
    if missing:
        raise ValidationError(f"The settlement file lacks columns: {', '.join(missing)}.")
    rows = [_row(raw, line) for line, raw in enumerate(reader, start=2)]
    if not rows:
        raise ValidationError("The settlement file has no rows.")
    checksum = hashlib.sha256(content).hexdigest()
    created = duplicates = 0
    for row in rows:
        _obj, new = SettlementLine.objects.get_or_create(
            terminal_id=row.terminal_id,
            rrn=row.rrn,
            approval_code=row.approval_code,
            defaults={
                "amount": row.amount,
                "settled_on": row.settled_on,
                "file_checksum": checksum,
            },
        )
        created += int(new)
        duplicates += int(not new)
    return SettlementImport(created, duplicates, checksum)
