"""Identifier rules: normalisation, type-specific validation and blind-index purposes.

Formats follow what Kenyan documents look like in practice; anything stricter (check
digits, the HIE Client Registry ID scheme) belongs in the registry adapter once the
specs are confirmed (GAP-CR-001).
"""

import re

import phonenumbers
from django.core.exceptions import ValidationError

from apps.core import crypto
from apps.patients.models import PatientIdentifier

T = PatientIdentifier.Type

PATTERNS: dict[str, re.Pattern[str]] = {
    T.NATIONAL_ID: re.compile(r"^\d{6,9}$"),
    T.MAISHA: re.compile(r"^\d{9,12}$"),
    T.ALIEN_ID: re.compile(r"^\d{6,10}$"),
    T.REFUGEE_ID: re.compile(r"^[A-Z0-9-]{6,20}$"),
    T.PASSPORT: re.compile(r"^[A-Z0-9]{6,12}$"),
    T.BIRTH_CERTIFICATE: re.compile(r"^\d{6,12}$"),
    T.BIRTH_NOTIFICATION: re.compile(r"^[A-Z0-9-]{4,20}$"),
    T.SHA: re.compile(r"^[A-Z0-9-]{6,20}$"),
    T.CLIENT_REGISTRY: re.compile(r"^CR[A-Z0-9-]{4,30}$"),
    T.TEMPORARY: re.compile(r"^ER-\d{4}-\d{4,}$"),
}
# Types staff may type in; temporary IDs are issued by the system only.
ENTERABLE = [t for t in PATTERNS if t != T.TEMPORARY]


def normalise(value: str) -> str:
    return crypto.normalise(value)


def validate(type_: str, value: str) -> str:
    """Return the normalised value or raise ValidationError (message never echoes the value)."""
    pattern = PATTERNS.get(type_)
    if pattern is None:
        raise ValidationError({"type": "Unknown identifier type."})
    normalised = normalise(value)
    if not pattern.match(normalised):
        raise ValidationError({"value": f"This is not a valid {T(type_).label.lower()} number."})
    return normalised


def index(type_: str, normalised: str) -> str:
    return crypto.blind_index(normalised, purpose=f"patients.identifier.{type_}")


def candidate_types(query: str) -> list[str]:
    """Identifier types a free-text search term could be (for exact-match lookup)."""
    normalised = normalise(query)
    return [t for t, pattern in PATTERNS.items() if pattern.match(normalised)]


def normalise_phone(value: str) -> str:
    """E.164, Kenya as the default region (api/CLAUDE.md)."""
    try:
        number = phonenumbers.parse(value, "KE")
    except phonenumbers.NumberParseException as exc:
        raise ValidationError({"value": "This is not a valid phone number."}) from exc
    if not phonenumbers.is_valid_number(number):
        raise ValidationError({"value": "This is not a valid phone number."})
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def phone_index(e164: str) -> str:
    return crypto.blind_index(e164, purpose="patients.contact.phone")


def email_index(email: str) -> str:
    return crypto.blind_index(email.strip().lower(), purpose="patients.contact.email")


def mask(value: str) -> str:
    """Show only the last 3 characters, for confirming identity at reception."""
    return "•" * max(0, len(value) - 3) + value[-3:]
