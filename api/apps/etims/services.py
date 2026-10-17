"""eTIMS queue (P3-TAX-01; DESIGN §10, §20 Q6; KE-KRA-01; ADR-076).

``ETIMS_MODE``: ``off`` (default — nothing is queued), ``fake`` (in-process VSCU) or
``vscu`` (the facility's KRA VSCU at ``ETIMS_VSCU_URL``). Invoices and credit notes are
queued with a branch-sequential eTIMS invoice number and sent at once; when the VSCU does
not answer they wait in the offline queue and ``transmit_due`` (beat ``p3-etims-retry``)
retries them with back-off. A document is sent under one invoice number for ever, so a
retry can never create a second sale (``994`` means eTIMS already has it).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record
from apps.core import sequences
from apps.etims.models import EtimsTransmission
from apps.etims.vscu import (
    CREDIT_NOTE,
    DUPLICATE,
    SALE,
    SUCCESS,
    TaxDocument,
    TaxLine,
    VscuClient,
    VscuUnavailable,
    build_save_sales,
    dumps,
)

MAX_BACKOFF = timedelta(hours=1)
SEQUENCE = "etims_invoice"


def mode() -> str:
    value = str(getattr(settings, "ETIMS_MODE", "off") or "off")
    if value not in ("off", "fake", "vscu"):
        raise ImproperlyConfigured(f"ETIMS_MODE={value!r} is not one of off, fake, vscu.")
    return value


def enabled() -> bool:
    return mode() != "off"


def client() -> VscuClient:
    current = mode()
    if current == "fake":
        from apps.etims.fake import shared

        return VscuClient("http://vscu.fake.invalid", mode="fake", transport=shared().transport())
    if current == "vscu":
        url = str(getattr(settings, "ETIMS_VSCU_URL", "") or "")
        if not url or not getattr(settings, "ETIMS_PIN", ""):
            raise ImproperlyConfigured(
                "ETIMS_MODE=vscu needs ETIMS_VSCU_URL and ETIMS_PIN (KRA VSCU approval and "
                "device registration — owner action, DESIGN §20 Q6)."
            )
        return VscuClient(url, mode="vscu")
    raise ImproperlyConfigured("eTIMS is off (ETIMS_MODE=off).")


@transaction.atomic
def queue(
    *,
    facility_id: int,
    kind: str,
    source_id: UUID,
    trader_invoice_no: str,
    lines: list[TaxLine],
    confirmed_at: Any = None,
    payment_type: str = "cash",
    original: EtimsTransmission | None = None,
    credit_note_reason: str = "",
    customer_pin: str = "",
    actor: Any = None,
) -> EtimsTransmission | None:
    """Queue one invoice or credit note (idempotent per source document). None when off."""
    if not enabled():
        return None
    existing = EtimsTransmission.objects.filter(
        facility_id=facility_id, kind=kind, source_id=source_id
    ).first()
    if existing is not None:
        return existing
    if kind == EtimsTransmission.Kind.CREDIT_NOTE and (
        original is None or original.receipt_no is None
    ):
        raise ValueError("A credit note needs its invoice accepted by eTIMS first.")
    number = sequences.next_value(facility_id=facility_id, name=SEQUENCE, year=0)
    doc = TaxDocument(
        trader_invoice_no=trader_invoice_no,
        invoice_no=number,
        original_invoice_no=original.etims_invoice_no if original else 0,
        receipt_type=CREDIT_NOTE if kind == EtimsTransmission.Kind.CREDIT_NOTE else SALE,
        confirmed_at=timezone.localtime(confirmed_at or timezone.now()),
        lines=tuple(lines),
        payment_type=payment_type,
        credit_note_reason=credit_note_reason,
        customer_pin=customer_pin,
    )
    payload = build_save_sales(
        doc,
        tin=str(getattr(settings, "ETIMS_PIN", "") or "P000000000Z"),
        branch_id=str(getattr(settings, "ETIMS_BRANCH_ID", "00") or "00"),
        user=str(getattr(actor, "pk", "") or "system"),
    )
    try:
        with transaction.atomic():
            row = EtimsTransmission.objects.create(
                facility_id=facility_id,
                kind=kind,
                source_id=source_id,
                trader_invoice_no=trader_invoice_no[:50],
                etims_invoice_no=number,
                original_invoice_no=doc.original_invoice_no,
                payload_json=dumps(payload).decode(),
                next_attempt_at=timezone.now(),
            )
    except IntegrityError:  # queued concurrently
        return EtimsTransmission.objects.get(
            facility_id=facility_id, kind=kind, source_id=source_id
        )
    record(
        "etims.document.queued",
        actor,
        row,
        facility=facility_id,
        detail={"kind": kind, "invoice_no": number},
    )
    return row


def transmit(doc: EtimsTransmission) -> EtimsTransmission:
    """Send one queued document; on no answer it stays queued with a later retry time."""
    if doc.status != EtimsTransmission.Status.QUEUED:
        return doc
    try:
        result = client().save_sales(doc.payload_json.encode(), facility_id=doc.facility_id)
    except VscuUnavailable:
        attempts = doc.attempts + 1
        delay = min(timedelta(minutes=2 ** min(attempts, 6)), MAX_BACKOFF)
        EtimsTransmission.objects.filter(pk=doc.pk).update(
            attempts=attempts, next_attempt_at=timezone.now() + delay
        )
        doc.refresh_from_db()
        return doc
    with transaction.atomic():
        current = EtimsTransmission.objects.select_for_update().get(pk=doc.pk)
        current.attempts += 1
        current.result_code = result.code
        current.result_message = result.message
        if result.code == SUCCESS:
            current.status = EtimsTransmission.Status.ACCEPTED
            current.receipt_no = result.receipt_no
            current.total_receipt_no = result.total_receipt_no
            current.internal_data = result.internal_data
            current.receipt_signature = result.receipt_signature
            current.sdc_id = result.sdc_id
            current.mrc_no = result.mrc_no
            current.signed_at = result.signed_at
            current.accepted_at = timezone.now()
        elif result.code == DUPLICATE:
            current.status = EtimsTransmission.Status.DUPLICATE
        else:
            current.status = EtimsTransmission.Status.REJECTED
        current.next_attempt_at = None
        current.save()
        record(
            "etims.document.transmitted",
            None,
            current,
            facility=current.facility_id,
            detail={"status": current.status, "result_code": result.code},
        )
    return current


def transmit_due(*, limit: int = 50) -> tuple[int, int]:
    """Send queued documents whose retry time has come; return (accepted, still queued)."""
    if not enabled():
        return 0, 0
    due = EtimsTransmission.objects.filter(
        status=EtimsTransmission.Status.QUEUED, next_attempt_at__lte=timezone.now()
    ).order_by("etims_invoice_no")[:limit]
    accepted = waiting = 0
    for doc in due:
        result = transmit(doc)
        if result.status == EtimsTransmission.Status.ACCEPTED:
            accepted += 1
        elif result.status == EtimsTransmission.Status.QUEUED:
            waiting += 1
    return accepted, waiting
