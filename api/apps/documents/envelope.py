"""Envelope encryption of stored objects (docs/integrations/STORAGE.md §3).

Each object gets a random 256-bit data key. Content is encrypted with AES-256-GCM in
1 MiB chunks so it can be streamed; chunk ``i`` uses nonce ``prefix(8) || i(4)`` and
binds the document ID, the index and a final-chunk flag as associated data, so chunks
cannot be reordered, swapped between objects or truncated. The data key is wrapped with
the current ``STORAGE_MASTER_KEYS`` key; rotation re-wraps data keys only.
"""

import base64
import os
from collections.abc import Iterable, Iterator
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apps.core import crypto

CHUNK = 1024 * 1024
TAG = 16
PREFIX_BYTES = 8
WRAP_AAD = b"afyasync:document-data-key"
MASTER_SETTING = "STORAGE_MASTER_KEYS"


class Readable(Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


class EnvelopeError(Exception):
    """The object or its key could not be decrypted (tampered, truncated or wrong key)."""


def new_data_key() -> bytes:
    return os.urandom(crypto.KEY_BYTES)


def new_nonce_prefix() -> bytes:
    return os.urandom(PREFIX_BYTES)


def wrap(data_key: bytes) -> tuple[str, str]:
    """(kid, base64(nonce || wrapped key)) under the newest master key."""
    ring = crypto.keyring(MASTER_SETTING)
    nonce = os.urandom(crypto.NONCE_BYTES)
    sealed = AESGCM(ring.keys[ring.current]).encrypt(nonce, data_key, WRAP_AAD)
    return ring.current, base64.b64encode(nonce + sealed).decode("ascii")


def unwrap(kid: str, wrapped: str) -> bytes:
    ring = crypto.keyring(MASTER_SETTING)
    if kid not in ring.keys:
        raise EnvelopeError("The master key for this object is not configured.")
    raw = base64.b64decode(wrapped)
    try:
        return AESGCM(ring.keys[kid]).decrypt(
            raw[: crypto.NONCE_BYTES], raw[crypto.NONCE_BYTES :], WRAP_AAD
        )
    except InvalidTag as exc:
        raise EnvelopeError("The data key could not be unwrapped.") from exc


def _nonce(prefix: bytes, index: int) -> bytes:
    return prefix + index.to_bytes(4, "big")


def _aad(object_id: str, index: int, final: bool) -> bytes:
    return f"{object_id}:{index}:{int(final)}".encode()


def _chunks(source: Readable, size: int) -> Iterator[bytes]:
    while block := source.read(size):
        yield block


def _with_final_flag(blocks: Iterable[bytes]) -> Iterator[tuple[bytes, bool]]:
    iterator = iter(blocks)
    current = next(iterator, b"")
    for following in iterator:
        yield current, False
        current = following
    yield current, True  # always one final chunk, possibly empty


def encrypt(
    plaintext: Readable, *, data_key: bytes, prefix: bytes, object_id: str
) -> Iterator[bytes]:
    cipher = AESGCM(data_key)
    for index, (block, final) in enumerate(_with_final_flag(_chunks(plaintext, CHUNK))):
        yield cipher.encrypt(_nonce(prefix, index), block, _aad(object_id, index, final))


def decrypt(stored: Readable, *, data_key: bytes, prefix: bytes, object_id: str) -> Iterator[bytes]:
    cipher = AESGCM(data_key)
    for index, (block, final) in enumerate(_with_final_flag(_chunks(stored, CHUNK + TAG))):
        try:
            yield cipher.decrypt(_nonce(prefix, index), block, _aad(object_id, index, final))
        except InvalidTag as exc:
            raise EnvelopeError("The stored object failed its integrity check.") from exc
