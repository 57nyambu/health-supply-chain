"""The only way files reach a disk or a bucket (docs/integrations/STORAGE.md §1, §6).

``STORAGES["local"]`` writes under ``DATA_DIR/objects``; ``STORAGES["s3"]`` writes to an
S3-compatible bucket. ``STORAGE_BACKEND`` picks the backend for new objects; reads always
use the backend recorded on the document row, so both can be live during a migration.
"""

import hashlib
import tempfile
from collections.abc import Iterable, Iterator
from datetime import datetime
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage, storages

from apps.core import residency
from apps.core.problems import ApiProblem

BACKENDS = ("local", "s3")
DEFAULT_S3_HOST = "s3.amazonaws.com"
READ_BYTES = 1024 * 1024
BACKEND_ERRORS: tuple[type[BaseException], ...] = (BotoCoreError, ClientError, OSError)


class StorageUnavailable(ApiProblem):
    status_code = 503
    default_detail = "File storage is unavailable. Try again later; nothing was saved."
    default_code = "storage_unavailable"


def check_residency() -> bool:
    """False (warn) or ImproperlyConfigured (strict) when the bucket is outside the allowlist."""
    if settings.STORAGE_BACKEND != "s3" and not settings.S3_ENDPOINT_URL:
        return True
    return residency.check_endpoint(settings.S3_ENDPOINT_URL or DEFAULT_S3_HOST, "Object storage")


def default_backend_name() -> str:
    name = str(settings.STORAGE_BACKEND)
    if name not in BACKENDS:
        raise StorageUnavailable("STORAGE_BACKEND is not configured correctly.")
    return name


def get_backend(name: str) -> Storage:
    if name not in BACKENDS:
        raise ValueError(f"Unknown storage backend {name!r}")
    if name == "s3" and not check_residency():
        raise StorageUnavailable("The object storage endpoint is blocked by the residency guard.")
    return storages[name]


def object_key(*, document_id: Any, facility_id: int, category: str, created: datetime) -> str:
    """``{env}/f{facility}/{category}/{yyyy}/{mm}/{document}`` — no names or identifiers."""
    return (
        f"{settings.DJANGO_ENV}/f{facility_id}/{category}/{created:%Y}/{created:%m}/{document_id}"
    )


def _spool_bytes() -> int:
    return int(settings.DOCUMENT_MAX_BYTES) * 2 + 1024 * 1024


def write(name: str, key: str, chunks: Iterable[bytes]) -> str:
    """Store the bytes under ``key`` and return the SHA-256 of what was stored."""
    digest = hashlib.sha256()
    # Large enough that an upload never spills to the system temp directory.
    with tempfile.SpooledTemporaryFile(max_size=_spool_bytes()) as spool:
        for chunk in chunks:
            spool.write(chunk)
            digest.update(chunk)
        spool.seek(0)
        backend = get_backend(name)
        try:
            saved = backend.save(key, File(spool, name=key))
        except BACKEND_ERRORS as exc:
            raise StorageUnavailable() from exc
    if saved != key:  # never overwrite or rename an object
        backend.delete(saved)
        raise StorageUnavailable("An object with this key already exists.")
    return digest.hexdigest()


def read(name: str, key: str) -> Iterator[bytes]:
    backend = get_backend(name)
    try:
        handle = backend.open(key, "rb")
    except BACKEND_ERRORS as exc:
        raise StorageUnavailable() from exc
    with handle:
        while block := handle.read(READ_BYTES):
            yield block


def stored_sha256(name: str, key: str) -> str:
    digest = hashlib.sha256()
    for block in read(name, key):
        digest.update(block)
    return digest.hexdigest()


def exists(name: str, key: str) -> bool:
    try:
        return bool(get_backend(name).exists(key))
    except BACKEND_ERRORS as exc:
        raise StorageUnavailable() from exc


def delete(name: str, key: str) -> None:
    try:
        get_backend(name).delete(key)
    except BACKEND_ERRORS as exc:
        raise StorageUnavailable() from exc
