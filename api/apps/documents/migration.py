"""Moving and checking stored objects (docs/integrations/STORAGE.md §6).

``migrate`` copies ciphertext from one backend to the other, checks the SHA-256 of what was
written against the row, then flips ``storage_backend`` on the row; rows already flipped are
no longer selected, so an interrupted run resumes where it stopped. ``purge_source`` is a
separate, later run that deletes a source object only when its row points at the destination
and the destination copy verifies. ``verify`` checks existence, ciphertext hash, decryption
and plaintext hash. Reports name document IDs only — never names or file names.
"""

import hashlib
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction
from django.db.models import QuerySet

from apps.audit.services import record
from apps.documents import envelope, storage
from apps.documents.models import Document

logger = logging.getLogger(__name__)


@dataclass
class Report:
    selected: int = 0
    copied: int = 0
    skipped: int = 0
    purged: int = 0
    verified: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def summary(self) -> dict[str, int]:
        return {
            "selected": self.selected,
            "copied": self.copied,
            "skipped": self.skipped,
            "purged": self.purged,
            "verified": self.verified,
            "failed": len(self.failed),
        }


def _rows(backend: str, *, category: str | None, facility: int | None) -> QuerySet[Document]:
    rows = Document.objects.filter(storage_backend=backend)
    if category:
        rows = rows.filter(category=category)
    if facility:
        rows = rows.filter(facility_id=facility)
    return rows.order_by("id")


def _batches(rows: QuerySet[Document], size: int) -> Iterator[list[Document]]:
    """Keyset pagination by UUIDv7 id, so rows flipped meanwhile never shift the cursor."""
    last: Any = None
    while True:
        page = rows.filter(id__gt=last) if last is not None else rows
        batch = list(page[:size])
        if not batch:
            return
        yield batch
        last = batch[-1].pk


def _check_pair(source: str, destination: str) -> None:
    if source not in storage.BACKENDS or destination not in storage.BACKENDS:
        raise ValueError("Backends are 'local' and 's3'.")
    if source == destination:
        raise ValueError("Source and destination must differ.")


def _copy(document: Document, source: str, destination: str, *, read_back: bool) -> str:
    """Copy one object; returns 'copied' or 'skipped' (already there and identical)."""
    key = document.storage_key
    if storage.exists(destination, key):
        if storage.stored_sha256(destination, key) == document.sha256_cipher:
            return "skipped"
        storage.delete(destination, key)  # a partial copy from an interrupted run
    written = storage.write(destination, key, storage.read(source, key))
    if written != document.sha256_cipher:
        storage.delete(destination, key)
        raise ValueError("source object does not match its recorded checksum")
    if read_back and storage.stored_sha256(destination, key) != document.sha256_cipher:
        storage.delete(destination, key)
        raise ValueError("destination copy failed verification")
    return "copied"


def migrate(
    source: str,
    destination: str,
    *,
    category: str | None = None,
    facility: int | None = None,
    batch: int = 500,
    dry_run: bool = False,
    verify: bool = False,
) -> Report:
    _check_pair(source, destination)
    report = Report()
    for rows in _batches(_rows(source, category=category, facility=facility), batch):
        report.selected += len(rows)
        if dry_run:
            continue
        before = report.summary()
        for document in rows:
            try:
                outcome = _copy(document, source, destination, read_back=verify)
            except (ValueError, storage.StorageUnavailable) as exc:
                report.failed.append((str(document.pk), str(exc) or type(exc).__name__))
                logger.error("Storage migration failed", extra={"document_id": str(document.pk)})
                continue
            with transaction.atomic():
                flipped = Document.objects.filter(pk=document.pk, storage_backend=source).update(
                    storage_backend=destination
                )
            if outcome == "copied" and flipped:
                report.copied += 1
            else:
                report.skipped += 1
        after = report.summary()
        record(
            "documents.storage.migrated_batch",
            None,
            severity="notice",
            detail={
                "source": source,
                "destination": destination,
                **{name: after[name] - before[name] for name in ("copied", "skipped", "failed")},
            },
        )
    return report


def purge_source(
    source: str,
    destination: str,
    *,
    category: str | None = None,
    facility: int | None = None,
    batch: int = 500,
    dry_run: bool = False,
) -> Report:
    """Delete source copies of objects already migrated, after re-verifying the destination."""
    _check_pair(source, destination)
    report = Report()
    for rows in _batches(_rows(destination, category=category, facility=facility), batch):
        report.selected += len(rows)
        purged_before = report.purged
        for document in rows:
            key = document.storage_key
            try:
                if not storage.exists(source, key):
                    report.skipped += 1
                    continue
                if storage.stored_sha256(destination, key) != document.sha256_cipher:
                    report.failed.append((str(document.pk), "destination copy failed verification"))
                    continue
                if not dry_run:
                    storage.delete(source, key)
                report.purged += 1
            except storage.StorageUnavailable as exc:
                report.failed.append((str(document.pk), str(exc)))
        if not dry_run:
            record(
                "documents.storage.purged_batch",
                None,
                severity="notice",
                detail={"source": source, "purged": report.purged - purged_before},
            )
    return report


def verify_document(document: Document) -> str | None:
    """None when the object is intact, else the reason (no PHI)."""
    backend, key = document.storage_backend, document.storage_key
    try:
        if not storage.exists(backend, key):
            return "missing"
        if storage.stored_sha256(backend, key) != document.sha256_cipher:
            return "ciphertext checksum mismatch"
        from apps.documents.services import plaintext

        digest = hashlib.sha256()
        for block in plaintext(document):
            digest.update(block)
    except envelope.EnvelopeError:
        return "decryption failed"
    except storage.StorageUnavailable:
        return "storage unavailable"
    if digest.hexdigest() != document.sha256_plain:
        return "plaintext checksum mismatch"
    return None


def verify(
    *, backend: str | None = None, sample: int | None = None, facility: int | None = None
) -> Report:
    rows = Document.objects.all()
    if backend:
        rows = rows.filter(storage_backend=backend)
    if facility:
        rows = rows.filter(facility_id=facility)
    rows = rows.order_by("?") if sample else rows.order_by("id")
    selected = list(rows[:sample]) if sample else rows.iterator()
    report = Report()
    for document in selected:
        report.selected += 1
        problem = verify_document(document)
        if problem is None:
            report.verified += 1
        else:
            report.failed.append((str(document.pk), problem))
            logger.error(
                "Stored object failed verification", extra={"document_id": str(document.pk)}
            )
    record("documents.storage.verified", None, severity="notice", detail=report.summary())
    return report
