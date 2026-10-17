"""SHA benefits and tariffs, imported as versions (P3-SHA-01 acceptance 4; DESIGN §9).

The official "Benefits and Tariffs" spreadsheet is an owner action (GAP-SHA-TARIFF-001):
its column layout is not published to us, so the importer reads our documented CSV layout
(``COLUMNS``) — the owner's spreadsheet is exported to it with a column map once we see it.
Until then the synthetic file ``fixtures/sha_tariffs_synthetic.csv`` (codes ``SYN-…``,
clearly not SHA's) is loaded by the seed. Versions are immutable: a new spreadsheet is a
new version; one version is active at a time. A missing tariff stays unknown (None), never
zero (KE-SHA-08).
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.insurance.models import ShaIntervention, ShaTariffVersion

COLUMNS = (
    "code",
    "name",
    "sub_benefit_code",
    "fund",
    "access_point",
    "payment_mechanism",
    "needs_preauth",
    "needs_manual_preauth_approval",
    "needs_doctor_authorization",
    "level_2",
    "level_3",
    "level_4",
    "level_5",
    "level_6",
    "overall",
)
REQUIRED = ("code", "name", "fund", "access_point", "payment_mechanism")
LEVELS = ("level_2", "level_3", "level_4", "level_5", "level_6")
TRUE = {"1", "true", "yes", "y"}
FALSE = {"", "0", "false", "no", "n"}


@dataclass(frozen=True)
class ImportResult:
    version: ShaTariffVersion
    created: bool
    rows: int


def _money(value: str, line: int, column: str) -> Decimal | None:
    text = value.strip().replace(",", "")
    if not text:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"Line {line}: {column} is not an amount.") from exc
    if amount < 0:
        raise ValidationError(f"Line {line}: {column} is negative.")
    return amount.quantize(Decimal("0.01"))


def _flag(value: str, line: int, column: str) -> bool:
    text = value.strip().lower()
    if text in TRUE:
        return True
    if text in FALSE:
        return False
    raise ValidationError(f"Line {line}: {column} must be yes or no.")


def parse(content: bytes) -> list[dict[str, Any]]:
    """Validate the whole file before anything is written; errors name the line."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("The tariff file must be UTF-8 CSV.") from exc
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ValidationError(f"The tariff file lacks columns: {', '.join(missing)}.")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line, raw in enumerate(reader, start=2):
        row = {k: (raw.get(k) or "").strip() for k in COLUMNS}
        for column in REQUIRED:
            if not row[column]:
                raise ValidationError(f"Line {line}: {column} is empty.")
        code = row["code"].upper()
        if code in seen:
            raise ValidationError(f"Line {line}: intervention {code} appears twice.")
        seen.add(code)
        rows.append(
            {
                "code": code,
                "name": row["name"][:255],
                "sub_benefit_code": row["sub_benefit_code"][:40],
                "fund": row["fund"][:20],
                "access_point": row["access_point"][:10],
                "payment_mechanism": row["payment_mechanism"][:40],
                "needs_preauth": _flag(row["needs_preauth"], line, "needs_preauth"),
                "needs_manual_preauth_approval": _flag(
                    row["needs_manual_preauth_approval"], line, "needs_manual_preauth_approval"
                ),
                "needs_doctor_authorization": _flag(
                    row["needs_doctor_authorization"], line, "needs_doctor_authorization"
                ),
                **{level: _money(row[level], line, level) for level in LEVELS},
                "overall": _money(row["overall"], line, "overall"),
            }
        )
    if not rows:
        raise ValidationError("The tariff file has no rows.")
    return rows


@transaction.atomic
def import_file(
    content: bytes, *, label: str, synthetic: bool, actor: Any = None, activate: bool = True
) -> ImportResult:
    checksum = hashlib.sha256(content).hexdigest()
    existing = ShaTariffVersion.objects.filter(checksum=checksum).first()
    if existing is not None:
        return ImportResult(existing, False, existing.rows)
    if ShaTariffVersion.objects.filter(label=label).exists():
        raise ValidationError(f"Version {label!r} already exists with different content.")
    rows = parse(content)
    version = ShaTariffVersion.objects.create(
        label=label,
        checksum=checksum,
        source=ShaTariffVersion.Source.SYNTHETIC if synthetic else ShaTariffVersion.Source.OFFICIAL,
        rows=len(rows),
        imported_by=actor,
    )
    ShaIntervention.objects.bulk_create(ShaIntervention(version=version, **row) for row in rows)
    if activate:
        activate_version(version, actor=actor)
    record(
        "insurance.tariffs.imported",
        actor,
        version,
        detail={"label": label, "rows": len(rows), "synthetic": synthetic, "active": activate},
    )
    return ImportResult(version, True, len(rows))


@transaction.atomic
def activate_version(version: ShaTariffVersion, *, actor: Any = None) -> ShaTariffVersion:
    ShaTariffVersion.objects.select_for_update().filter(active=True).exclude(pk=version.pk).update(
        active=False
    )
    if not version.active:
        version.active = True
        version.activated_at = timezone.now()
        version.save(update_fields=["active", "activated_at"])
    return version


def active_version() -> ShaTariffVersion | None:
    return ShaTariffVersion.objects.filter(active=True).first()


def intervention(code: str) -> ShaIntervention | None:
    version = active_version()
    if version is None:
        return None
    return ShaIntervention.objects.filter(version=version, code=code.upper()).first()


def tariff(code: str, keph_level: int | None) -> Decimal | None:
    """The tariff for a facility level (falls back to the overall rate), None if unpublished."""
    row = intervention(code)
    if row is None:
        return None
    if keph_level is not None and 2 <= keph_level <= 6:
        value = getattr(row, f"level_{keph_level}")
        if value is not None:
            return value  # type: ignore[no-any-return]
    return row.overall


def unknown_codes(codes: list[str]) -> list[str]:
    """Codes that are not in the active version (claims scrubber, billing mapping checks)."""
    version = active_version()
    wanted = {c.upper() for c in codes}
    if version is None:
        return sorted(wanted)
    known = set(
        ShaIntervention.objects.filter(version=version, code__in=wanted).values_list(
            "code", flat=True
        )
    )
    return sorted(wanted - known)
