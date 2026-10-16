"""Model fields that keep personal data and secrets encrypted at rest (DESIGN §8.2)."""

from typing import Any

from django.core.exceptions import FieldError
from django.db import models

from apps.core import crypto


class EncryptedTextField(models.TextField):
    """Stores ``crypto.encrypt`` tokens; Python code always sees plaintext.

    Ciphertext cannot be searched: pair the field with a blind index for exact
    matches. ``rotate_field_keys`` re-encrypts values written under older keys.
    """

    description = "Text encrypted with AES-256-GCM"

    def from_db_value(self, value: str | None, expression: Any, connection: Any) -> str | None:
        if value is None or value == "":
            return value
        return crypto.decrypt_text(value)

    def to_python(self, value: Any) -> Any:
        return value

    def get_prep_value(self, value: Any) -> Any:
        if value is None or value == "":
            return value
        return crypto.encrypt(str(value))

    def get_lookup(self, lookup_name: str) -> Any:
        if lookup_name not in ("isnull",):
            raise FieldError(
                f"Encrypted fields cannot be filtered with '{lookup_name}'; use a blind index."
            )
        return super().get_lookup(lookup_name)


class EncryptedBinaryField(models.TextField):
    """Binary payloads (raw integration bodies, stored responses) encrypted at rest."""

    description = "Bytes encrypted with AES-256-GCM"

    def from_db_value(self, value: str | None, expression: Any, connection: Any) -> bytes | None:
        if value is None:
            return None
        if value == "":
            return b""
        return crypto.decrypt(value)

    def to_python(self, value: Any) -> Any:
        return value

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return None
        if value in (b"", ""):
            return ""
        return crypto.encrypt(bytes(value))

    def get_lookup(self, lookup_name: str) -> Any:
        if lookup_name not in ("isnull",):
            raise FieldError(f"Encrypted fields cannot be filtered with '{lookup_name}'.")
        return super().get_lookup(lookup_name)
