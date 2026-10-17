"""Remove PHI from free text and structured data before it leaves the process.

Used by the logging filter and the error tracker. Pattern scrubbing catches
identifiers, phone numbers and e-mail addresses in any text; names cannot be
recognised reliably in free text, so structured values are redacted by key
(``first_name``, ``patient_name``, ``phone``, ``id_number``…). Code must still
never log PHI on purpose — this is the safety net, not the policy.
"""

import re
from collections.abc import Mapping
from typing import Any

from django.http import HttpRequest

REDACTED = "[redacted]"

# Phone-like digit runs (E.164 and Kenyan local formats +2547…, 2547…, 07…, 01…),
# replaced only when they hold at least 9 digits so ISO dates survive.
_PHONE_LIKE = re.compile(r"(?<![\w+])\+?\d[\d\s-]{7,16}\d(?!\w)")
MIN_PHONE_DIGITS = 9

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email]"),
    # Registry and local identifiers: CR…, SHA…, FID-…, PUID-…, MRN 99999-26-000123, visit OP-…
    (re.compile(r"\b(?:CR|SHA|FID-|PUID-)[A-Z0-9-]{4,}\b", re.IGNORECASE), "[identifier]"),
    (re.compile(r"\b\d{4,6}-\d{2}-\d{4,8}\b"), "[identifier]"),
    (re.compile(r"\b(?:OP|EM|IP)-\d{4,6}-\d{6}-\d+\b"), "[identifier]"),
    # Passports, alien and refugee IDs: letter(s) followed by 6+ digits
    (re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"), "[identifier]"),
    # Any other run of 6+ digits (national IDs, birth certificate numbers)
    (re.compile(r"(?<![\w.])\d{6,}(?![\w.])"), "[number]"),
]

SENSITIVE_KEY_PARTS = (
    "name",
    "phone",
    "mobile",
    "msisdn",
    "email",
    "identifier",
    "id_number",
    "national_id",
    "passport",
    "birth",
    "dob",
    "address",
    "next_of_kin",
    "nok",
    "password",
    "pin",
    "secret",
    "token",
    "otp",
    "diagnosis",
    "note",
    "query",
    "search",
    "cookie",
    "authorization",
)
SAFE_KEYS = {"logger", "logger_name", "levelname", "module", "funcName", "app_name", "event_name"}


def _phone(match: re.Match[str]) -> str:
    digits = sum(ch.isdigit() for ch in match.group(0))
    return "[number]" if digits >= MIN_PHONE_DIGITS else match.group(0)


# UUIDs are opaque record IDs, not personal data. Their hex groups can be all digits
# (e.g. ``…-785334721303``), which the digit-run patterns would otherwise mangle.
_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


def _scrub_segment(text: str) -> str:
    text = _PATTERNS[0][0].sub(_PATTERNS[0][1], text)  # e-mail first: it contains digits too
    text = _PHONE_LIKE.sub(_phone, text)
    for pattern, replacement in _PATTERNS[1:]:
        text = pattern.sub(replacement, text)
    return text


def scrub_text(text: str) -> str:
    """Scrub everything except UUIDs, which pass through unchanged."""
    out: list[str] = []
    last = 0
    for match in _UUID.finditer(text):
        out.append(_scrub_segment(text[last : match.start()]))
        out.append(match.group(0))
        last = match.end()
    out.append(_scrub_segment(text[last:]))
    return "".join(out)


def is_sensitive_key(key: str) -> bool:
    if key in SAFE_KEYS:
        return False
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def scrub_value(value: Any, key: str | None = None) -> Any:
    """Recursively redact sensitive keys and scrub identifiers from strings."""
    if key is not None and is_sensitive_key(key) and value not in (None, "", [], {}):
        return REDACTED
    if isinstance(value, HttpRequest):
        # Django passes the request to django.request records; its repr carries the query
        # string (search terms, filters). Keep the method and path only.
        return scrub_text(f"{value.method} {value.path}")
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, Mapping):
        return {k: scrub_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [scrub_value(item) for item in value]
    return value
