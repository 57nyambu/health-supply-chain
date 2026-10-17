"""Translation between our vocabulary and the HIE's (field names from the published specs —
DECISIONS.md, Phase 3 findings). All HIE field names used by the registry and SHA adapters
are read here, so a spec change touches one module."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

# Our identifier types → the HIE's ``identification_type`` values (registries and
# eligibility share the enum). Maisha Namba has no HIE value yet (GAP-HIE-004).
ID_TYPES: dict[str, str] = {
    "national_id": "National ID",
    "cr_id": "ClientRegistry ID",
    "birth_notification": "Birth Notification",
    "birth_certificate": "Birth Certificate",
    "alien_id": "Alien ID",
    "refugee_id": "Refugee ID",
}
FROM_HIE_ID_TYPES = {value: key for key, value in ID_TYPES.items()}

REGULATORS = ("KMPDC", "COC", "NCK", "PPB")
SERVICE_TYPES = {
    "outpatient": "OUTPATIENT",
    "inpatient": "INPATIENT",
    "capitation": "CAPITATION",
    "emergency": "EMERGENCY",
}
# ``POST /claims/authorize`` accepts only these two (its schema's enum).
AUTHORIZE_SERVICE_TYPES = {"outpatient": "OUTPATIENT", "inpatient": "INPATIENT"}


def hie_id_type(ours: str) -> str | None:
    return ID_TYPES.get(ours)


def parse_date(value: Any) -> date | None:
    """ISO dates (the HIE's examples are placeholders; GAP-HIE-003 asks for the format)."""
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_money(value: Any) -> Decimal | None:
    """HIE tariffs are JSON numbers; convert from their text so no float rounding creeps in.
    ``None`` (absent) stays ``None`` — an unpublished rate is unknown, not zero (KE-SHA-08)."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def sex(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"female", "f"}:
        return "female"
    if text in {"male", "m"}:
        return "male"
    if text == "intersex":
        return "intersex"
    return "unknown"


def text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value == 1
    return str(value).strip().lower() in {"1", "true", "yes"}
