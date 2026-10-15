"""Writing to and anchoring the audit chain. Call ``record`` inside the service transaction."""

import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.audit import context
from apps.audit.models import AuditAnchor, AuditChainHead, AuditEvent
from apps.core.scrubbing import is_sensitive_key, scrub_text

GENESIS_HASH = "0" * 64
ANCHOR_FILE = "anchors.jsonl"

Scalar = str | int | float | bool | None


def canonical_payload(event: AuditEvent) -> str:
    """The exact bytes the hash covers; the verifier recomputes it from stored rows."""
    payload = {
        "action": event.action,
        "actor_id": event.actor_id,
        "actor_role": event.actor_role,
        "chain_date": event.chain_date.isoformat(),
        "detail": event.detail,
        "facility_id": event.facility_id,
        "id": str(event.id),
        "ip": event.ip,
        "outcome": event.outcome,
        "patient_id": str(event.patient_id) if event.patient_id else None,
        "purpose": event.purpose,
        "request_id": event.request_id,
        "resource_id": event.resource_id,
        "resource_type": event.resource_type,
        "seq": event.seq,
        "severity": event.severity,
        "ts": event.ts.astimezone(UTC).isoformat(),
        "user_agent": event.user_agent,
        "workstation_id": event.workstation_id,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: str, event: AuditEvent) -> str:
    return hashlib.sha256((prev_hash + canonical_payload(event)).encode("utf-8")).hexdigest()


def _clean_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Detail holds IDs and codes only (api/CLAUDE.md): sensitive keys are refused."""
    cleaned: dict[str, Any] = {}
    for key, value in (detail or {}).items():
        if is_sensitive_key(key):
            raise ValueError(
                f"Audit detail key {key!r} looks like personal data; store IDs and codes only"
            )
        cleaned[key] = _clean_value(value)
    return cleaned


def _clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, bool | int | float) or value is None:
        return value
    if isinstance(value, uuid.UUID | date | datetime):
        return str(value)
    if isinstance(value, list | tuple):
        return [_clean_value(item) for item in value]
    if isinstance(value, dict):
        return _clean_detail(value)
    raise TypeError(f"Unsupported audit detail value of type {type(value).__name__}")


def _resource_ref(resource: Any) -> tuple[str, str]:
    if resource is None:
        return "", ""
    if isinstance(resource, tuple):
        resource_type, resource_id = resource
        return str(resource_type), str(resource_id)
    if isinstance(resource, models.Model):
        return resource._meta.label_lower, str(resource.pk)
    raise TypeError("resource must be a model instance or a (type, id) tuple")


def _facility_id(facility: Any, resource: Any) -> int:
    if facility is not None:
        return int(getattr(facility, "pk", facility))
    candidate = getattr(resource, "facility_id", None)
    if candidate:
        return int(candidate)
    return context.current().facility_id or 0


def _previous_chain_hash(facility_id: int, chain_date: date) -> str:
    previous = (
        AuditChainHead.objects.filter(facility_id=facility_id, chain_date__lt=chain_date)
        .order_by("-chain_date")
        .values_list("last_hash", flat=True)
        .first()
    )
    return previous or GENESIS_HASH


def record(
    action: str,
    actor: Any = None,
    resource: Any = None,
    *,
    patient: Any = None,
    purpose: str = "",
    outcome: str = AuditEvent.Outcome.SUCCESS,
    detail: dict[str, Any] | None = None,
    facility: Any = None,
    severity: str = "info",
) -> AuditEvent:
    """Append one event to the facility's chain for today and return it."""
    ctx = context.current()
    ts = timezone.now()
    chain_date = timezone.localdate(ts)
    facility_id = _facility_id(facility, resource)
    resource_type, resource_id = _resource_ref(resource)
    patient_id = getattr(patient, "pk", patient)
    actor_id = getattr(actor, "pk", None) if actor is not None else None

    with transaction.atomic():
        head, _created = AuditChainHead.objects.select_for_update().get_or_create(
            facility_id=facility_id,
            chain_date=chain_date,
            defaults={"last_hash": _previous_chain_hash(facility_id, chain_date), "last_seq": 0},
        )
        event = AuditEvent(
            id=uuid.uuid4(),
            ts=ts,
            facility_id=facility_id,
            chain_date=chain_date,
            seq=head.last_seq + 1,
            actor_id=actor_id,
            actor_role=context.role_resolver(actor) if actor is not None else "",
            workstation_id=ctx.workstation_id,
            ip=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=context.request_id(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            purpose=purpose,
            outcome=outcome,
            severity=severity,
            detail=_clean_detail(detail),
            prev_hash=head.last_hash,
        )
        event.hash = compute_hash(event.prev_hash, event)
        event.save(force_insert=True)
        AuditChainHead.objects.filter(pk=head.pk).update(last_seq=event.seq, last_hash=event.hash)
    return event


def anchor_file_path() -> Path:
    return Path(settings.DATA_DIR) / "audit-anchors" / ANCHOR_FILE


def anchor_finished_chains(today: date | None = None) -> list[AuditAnchor]:
    """Anchor every chain before ``today`` that has no anchor yet (DB + append-only file)."""
    today = today or timezone.localdate()
    created: list[AuditAnchor] = []
    pending = AuditChainHead.objects.filter(chain_date__lt=today)
    anchored = set(AuditAnchor.objects.values_list("facility_id", "chain_date"))
    path = anchor_file_path()
    for head in pending.order_by("chain_date", "facility_id"):
        if (head.facility_id, head.chain_date) in anchored:
            continue
        anchor = AuditAnchor.objects.create(
            facility_id=head.facility_id,
            chain_date=head.chain_date,
            last_hash=head.last_hash,
            event_count=head.last_seq,
            anchored_at=timezone.now(),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(anchor_line(anchor), sort_keys=True) + "\n")
        created.append(anchor)
    return created


def anchor_line(anchor: AuditAnchor) -> dict[str, Any]:
    return {
        "chain_date": anchor.chain_date.isoformat(),
        "event_count": anchor.event_count,
        "facility_id": anchor.facility_id,
        "last_hash": anchor.last_hash,
    }
