"""Uploading and reading documents (docs/integrations/STORAGE.md §3, §5).

Upload: size and type checks (magic bytes), image metadata stripped, encrypt, write to the
default backend, then create the row — a failed write leaves no row. Read: permission,
chart access (including sensitivity) and an audit event, then a decrypted stream.
"""

import base64
import hashlib
import io
import logging
from collections.abc import Iterator
from typing import Any, BinaryIO

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.access import chart, policies
from apps.access.roles import ChartAccess
from apps.audit.services import record
from apps.core.ids import uuid7
from apps.core.sensitivity import SensitiveCategory
from apps.documents import envelope, storage
from apps.documents.models import Document

logger = logging.getLogger(__name__)

C = Document.Category
# Chart level needed to see a patient's document of each category (DESIGN §7.7).
CATEGORY_LEVEL = {
    C.ID_SCAN: ChartAccess.DEMOGRAPHICS,
    C.CONSENT_FORM: ChartAccess.DEMOGRAPHICS,
    C.INVOICE_PDF: ChartAccess.DEMOGRAPHICS,
    C.RECEIPT_PDF: ChartAccess.DEMOGRAPHICS,
}
DEFAULT_LEVEL = ChartAccess.FULL
# Documents read through another process need that process's permission as well.
CATEGORY_PERMISSION = {C.AUDIT_ANCHOR: "audit.log.read", C.DSAR_EXPORT: "patients.dsar.read"}
SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)
PIL_FORMAT = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


def sniff(head: bytes) -> str | None:
    """Content type from magic bytes; the declared type and extension are ignored."""
    for signature, content_type in SIGNATURES:
        if head.startswith(signature):
            return content_type
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _read_limited(content: BinaryIO) -> bytes:
    limit = int(settings.DOCUMENT_MAX_BYTES)
    data = content.read(limit + 1)
    if len(data) > limit:
        raise ValidationError({"file": f"The file is larger than {limit // (1024 * 1024)} MB."})
    if not data:
        raise ValidationError({"file": "The file is empty."})
    return data


def _strip_image_metadata(data: bytes, content_type: str) -> bytes:
    """Re-encode the image without EXIF/GPS/text metadata, keeping its orientation."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            upright = ImageOps.exif_transpose(image)
            out = io.BytesIO()
            upright.save(out, format=PIL_FORMAT[content_type])
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError({"file": "The image could not be read."}) from exc
    return out.getvalue()


def required_level(document: Document) -> ChartAccess:
    if document.is_sensitive:
        return ChartAccess.SENSITIVE
    return CATEGORY_LEVEL.get(Document.Category(document.category), DEFAULT_LEVEL)


def visible_level(category: str) -> ChartAccess:
    return CATEGORY_LEVEL.get(Document.Category(category), DEFAULT_LEVEL)


@transaction.atomic
def upload(
    *,
    actor: Any,
    facility_id: int,
    content: BinaryIO,
    filename: str,
    category: str,
    patient: Any = None,
    sensitivity: str = SensitiveCategory.NORMAL,
    supersedes: Document | None = None,
) -> Document:
    if not policies.has_permission(actor, "documents.document.upload", facility=facility_id):
        raise PermissionDenied("You may not upload documents here.")
    if category not in Document.Category.values or category in CATEGORY_PERMISSION:
        raise ValidationError({"category": "Choose a document category."})
    if sensitivity not in SensitiveCategory.values:
        raise ValidationError({"sensitivity": "Unknown sensitivity category."})
    if patient is not None:
        if patient.facility_id != facility_id:
            raise ValidationError({"patient": "Choose a patient of this facility."})
        if not chart.decide(actor, patient).allows(ChartAccess.DEMOGRAPHICS):
            raise PermissionDenied("You do not have access to this patient's record.")
    if supersedes is not None and (
        supersedes.facility_id != facility_id
        or supersedes.patient_id != getattr(patient, "pk", None)
        or supersedes.superseded_by_id is not None
    ):
        raise ValidationError(
            {"supersedes": "Choose the current version of this patient's document."}
        )

    data = _read_limited(content)
    content_type = sniff(data[:16])
    if content_type is None or content_type not in settings.DOCUMENT_ALLOWED_TYPES:
        raise ValidationError({"file": "Upload a PDF, JPEG, PNG or WebP file."})
    if content_type in PIL_FORMAT:
        data = _strip_image_metadata(data, content_type)
    return _store(
        actor=actor,
        facility_id=facility_id,
        data=data,
        content_type=content_type,
        filename=filename,
        category=category,
        patient=patient,
        sensitivity=sensitivity,
        supersedes=supersedes,
    )


GENERATED_TYPES = {"application/pdf", "application/json"}


@transaction.atomic
def store_generated(
    *,
    actor: Any,
    facility_id: int,
    data: bytes,
    content_type: str,
    filename: str,
    category: str,
    patient: Any = None,
    sensitivity: str = SensitiveCategory.NORMAL,
) -> Document:
    """Store a file the system produced (exports, generated PDFs) — never a user upload."""
    if content_type not in GENERATED_TYPES:
        raise ValueError(f"Unsupported generated content type {content_type}")
    return _store(
        actor=actor,
        facility_id=facility_id,
        data=data,
        content_type=content_type,
        filename=filename,
        category=category,
        patient=patient,
        sensitivity=sensitivity,
        supersedes=None,
    )


def _store(
    *,
    actor: Any,
    facility_id: int,
    data: bytes,
    content_type: str,
    filename: str,
    category: str,
    patient: Any,
    sensitivity: str,
    supersedes: Document | None,
) -> Document:
    document_id = uuid7()
    now = timezone.now()
    backend = storage.default_backend_name()
    key = storage.object_key(
        document_id=document_id, facility_id=facility_id, category=category, created=now
    )
    kid = wrapped = prefix_text = ""
    if settings.STORAGE_ENCRYPTION:
        data_key, prefix = envelope.new_data_key(), envelope.new_nonce_prefix()
        kid, wrapped = envelope.wrap(data_key)
        prefix_text = base64.b64encode(prefix).decode("ascii")
        chunks: Any = envelope.encrypt(
            io.BytesIO(data), data_key=data_key, prefix=prefix, object_id=str(document_id)
        )
    else:
        chunks = [data]
    cipher_hash = storage.write(
        backend, key, chunks
    )  # raises StorageUnavailable: no row is created

    document = Document.objects.create(
        id=document_id,
        facility_id=facility_id,
        patient=patient,
        category=category,
        sensitivity=sensitivity,
        content_type=content_type,
        size=len(data),
        sha256_plain=hashlib.sha256(data).hexdigest(),
        sha256_cipher=cipher_hash,
        storage_backend=backend,
        storage_key=key,
        enc_kid=kid,
        enc_wrapped_key=wrapped,
        enc_nonce_prefix=prefix_text,
        original_filename=filename[:255],
        uploaded_by=actor,
    )
    if supersedes is not None:
        Document.objects.filter(pk=supersedes.pk).update(superseded_by=document)
    record(
        "documents.document.uploaded",
        actor,
        document,
        patient=patient,
        facility=facility_id,
        detail={
            "category": category,
            "flagged": document.is_sensitive,
            "bytes": document.size,
            "backend": backend,
            "supersedes_id": str(supersedes.pk) if supersedes else None,
        },
    )
    return document


def reassign(document_ids: list[str], patient: Any) -> None:
    """Move documents to another record during a registry merge or its reversal (the merge
    itself is audited by the patients app)."""
    Document.objects.filter(pk__in=document_ids).update(patient=patient)


def plaintext(document: Document) -> Iterator[bytes]:
    """Decrypted content; raises EnvelopeError when the object or key is wrong."""
    stored = storage.read(document.storage_backend, document.storage_key)
    if not document.encrypted:
        yield from stored
        return
    data_key = envelope.unwrap(document.enc_kid, document.enc_wrapped_key)
    prefix = base64.b64decode(document.enc_nonce_prefix)
    yield from envelope.decrypt(
        _Reader(stored), data_key=data_key, prefix=prefix, object_id=str(document.pk)
    )


class _Reader(io.RawIOBase):
    """File-like view over an iterator of byte blocks."""

    def __init__(self, blocks: Iterator[bytes]) -> None:
        self._blocks = blocks
        self._buffer = b""

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        while size < 0 or len(self._buffer) < size:
            block = next(self._blocks, None)
            if block is None:
                break
            self._buffer += block
        if size < 0:
            size = len(self._buffer)
        out, self._buffer = self._buffer[:size], self._buffer[size:]
        return out


def authorise_read(
    document: Document, *, user: Any, purpose: str
) -> chart.ChartAccessDecision | None:
    """Raise unless ``user`` may read the document; return the chart decision for audit."""
    needed_permission = CATEGORY_PERMISSION.get(Document.Category(document.category))
    if needed_permission is not None:
        # Exports and anchors are reached through their own process (e.g. the DPO's DSAR
        # work), gated by that process's permission rather than by chart access.
        if not policies.has_permission(user, needed_permission, facility=document.facility_id):
            raise PermissionDenied("This document is available only through its own process.")
        return None
    if document.patient_id is None:
        return None
    from apps.patients.selectors import ChartAccessDenied

    decision = chart.decide(user, document.patient, purpose=purpose)
    needed = required_level(document)
    if not decision.allows(needed):
        record(
            "documents.document.denied",
            user,
            document,
            patient=document.patient_id,
            purpose=purpose,
            outcome="denied",
            detail={"level": decision.level.value, "needed": needed.value},
        )
        raise ChartAccessDenied(decision, needed)
    return decision


def open_content(document: Document, *, user: Any, purpose: str) -> Iterator[bytes]:
    """Check access, audit the view and return the plaintext stream (first block ready)."""
    purpose = purpose if purpose in chart.PURPOSES else "care"
    decision = authorise_read(document, user=user, purpose=purpose)
    stream = plaintext(document)
    first = next(stream, b"")  # surface key/integrity/storage errors before any byte is sent
    grant = decision.break_glass if decision else None
    record(
        "documents.document.viewed",
        user,
        document,
        patient=document.patient_id,
        purpose=purpose,
        severity="high" if grant is not None else "info",
        detail={
            "category": document.category,
            "level": decision.level.value if decision else None,
            "break_glass_id": str(grant.pk) if grant is not None else None,
        },
    )

    def chained() -> Iterator[bytes]:
        yield first
        yield from stream

    return chained()
