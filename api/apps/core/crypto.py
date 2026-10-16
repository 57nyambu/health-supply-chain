"""Field-level encryption and blind indexes (DESIGN §8.2, P1-DATA-01).

- ``encrypt``/``decrypt``: AES-256-GCM. Tokens are ``v1.<kid>.<base64(nonce|ciphertext)>``;
  the key id travels with the value so keys rotate without downtime.
- ``FIELD_ENCRYPTION_KEYS`` is JSON ``{"<kid>": "<base64 32-byte key>"}``, newest first.
  New values use the first key; any listed key decrypts.
- ``blind_index``: HMAC-SHA256 with a separate key over a normalised value, for
  exact-match search without storing the plaintext.

Development and tests without configured keys use keys derived from SECRET_KEY
(kid ``dev``); production refuses to start without real keys (config/settings/guards.py).
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from functools import cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

TOKEN_VERSION = "v1"  # noqa: S105 - format version, not a secret
NONCE_BYTES = 12
KEY_BYTES = 32
DEV_KID = "dev"


class DecryptionError(Exception):
    """A value could not be decrypted (unknown key id, tampering or corruption)."""


@dataclass(frozen=True)
class Keyring:
    keys: dict[str, bytes]
    current: str


def _decode_key(kid: str, encoded: str) -> bytes:
    try:
        key = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ImproperlyConfigured(f"Encryption key {kid!r} is not valid base64.") from exc
    if len(key) != KEY_BYTES:
        raise ImproperlyConfigured(f"Encryption key {kid!r} must be {KEY_BYTES} bytes.")
    return key


def _derived(purpose: str) -> bytes:
    return hashlib.sha256(f"afyasync-dev:{purpose}:{settings.SECRET_KEY}".encode()).digest()


@cache
def keyring(setting: str = "FIELD_ENCRYPTION_KEYS") -> Keyring:
    raw = getattr(settings, setting, "") or ""
    if not raw:
        if settings.DJANGO_ENV == "prod":
            raise ImproperlyConfigured(f"{setting} must be set in production.")
        return Keyring({DEV_KID: _derived(setting)}, DEV_KID)
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{setting} must be a JSON object.") from exc
    if not isinstance(parsed, dict) or not parsed:
        raise ImproperlyConfigured(f"{setting} must be a non-empty JSON object.")
    keys = {str(kid): _decode_key(str(kid), str(value)) for kid, value in parsed.items()}
    return Keyring(keys, next(iter(keys)))


@cache
def _blind_index_key() -> bytes:
    raw = settings.FIELD_BLIND_INDEX_KEY
    if not raw:
        if settings.DJANGO_ENV == "prod":
            raise ImproperlyConfigured("FIELD_BLIND_INDEX_KEY must be set in production.")
        return _derived("FIELD_BLIND_INDEX_KEY")
    return raw.encode() if not isinstance(raw, bytes) else raw


def reset_key_cache() -> None:
    """Forget cached keys (tests and key rotation)."""
    keyring.cache_clear()
    _blind_index_key.cache_clear()


def encrypt(plaintext: str | bytes, *, aad: bytes = b"") -> str:
    ring = keyring()
    data = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext
    nonce = os.urandom(NONCE_BYTES)
    sealed = AESGCM(ring.keys[ring.current]).encrypt(nonce, data, aad)
    body = base64.urlsafe_b64encode(nonce + sealed).decode("ascii")
    return f"{TOKEN_VERSION}.{ring.current}.{body}"


def token_kid(token: str) -> str:
    parts = token.split(".", 2)
    if len(parts) != 3 or parts[0] != TOKEN_VERSION:
        raise DecryptionError("Not an encrypted value.")
    return parts[1]


def decrypt(token: str, *, aad: bytes = b"") -> bytes:
    kid = token_kid(token)
    key = keyring().keys.get(kid)
    if key is None:
        raise DecryptionError(f"No key with id {kid!r} is configured.")
    try:
        raw = base64.urlsafe_b64decode(token.split(".", 2)[2])
        return AESGCM(key).decrypt(raw[:NONCE_BYTES], raw[NONCE_BYTES:], aad)
    except Exception as exc:  # InvalidTag, binascii.Error, ValueError
        raise DecryptionError("The value could not be decrypted.") from exc


def decrypt_text(token: str, *, aad: bytes = b"") -> str:
    return decrypt(token, aad=aad).decode("utf-8")


def normalise(value: str) -> str:
    """Case- and space-insensitive form used for blind indexes."""
    return "".join(value.split()).upper()


def blind_index(value: str, *, purpose: str) -> str:
    """HMAC-SHA256 of ``purpose`` + normalised value (hex). Different purposes never collide."""
    message = f"{purpose}\x00{normalise(value)}".encode()
    return hmac.new(_blind_index_key(), message, hashlib.sha256).hexdigest()


def needs_rotation(token: str) -> bool:
    return token_kid(token) != keyring().current
