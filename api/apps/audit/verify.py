"""Verify the audit hash chains: modified, deleted or reordered events are reported."""

import json
from dataclasses import dataclass
from datetime import date

from apps.audit.models import AuditAnchor, AuditChainHead, AuditEvent
from apps.audit.services import GENESIS_HASH, anchor_file_path, compute_hash

ChainKey = tuple[int, date]


@dataclass(frozen=True)
class Problem:
    facility_id: int
    chain_date: date
    seq: int | None
    kind: str
    message: str

    def __str__(self) -> str:
        position = f" seq {self.seq}" if self.seq is not None else ""
        return (
            f"[{self.kind}] facility {self.facility_id} {self.chain_date}{position}: {self.message}"
        )


def _file_anchors() -> dict[ChainKey, dict[str, object]]:
    path = anchor_file_path()
    anchors: dict[ChainKey, dict[str, object]] = {}
    if not path.exists():
        return anchors
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            anchors[(int(entry["facility_id"]), date.fromisoformat(entry["chain_date"]))] = entry
    return anchors


def _chain_keys(
    date_from: date | None, date_to: date | None, facility_id: int | None
) -> list[ChainKey]:
    keys: set[ChainKey] = set()
    for model in (AuditEvent, AuditChainHead, AuditAnchor):
        queryset = model.objects.all()
        if date_from:
            queryset = queryset.filter(chain_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(chain_date__lte=date_to)
        if facility_id is not None:
            queryset = queryset.filter(facility_id=facility_id)
        keys.update(queryset.values_list("facility_id", "chain_date").distinct())
    return sorted(keys, key=lambda key: (key[0], key[1]))


def _expected_first_prev(facility_id: int, chain_date: date) -> str:
    """Last hash of the facility's previous chain, from events, else its anchor, else genesis."""
    previous_event = (
        AuditEvent.objects.filter(facility_id=facility_id, chain_date__lt=chain_date)
        .order_by("-chain_date", "-seq")
        .values_list("hash", flat=True)
        .first()
    )
    if previous_event:
        return str(previous_event)
    previous_anchor = (
        AuditAnchor.objects.filter(facility_id=facility_id, chain_date__lt=chain_date)
        .order_by("-chain_date")
        .values_list("last_hash", flat=True)
        .first()
    )
    return str(previous_anchor) if previous_anchor else GENESIS_HASH


def verify_chains(
    date_from: date | None = None, date_to: date | None = None, facility_id: int | None = None
) -> tuple[int, list[Problem]]:
    """Return (events checked, problems)."""
    problems: list[Problem] = []
    checked = 0
    file_anchors = _file_anchors()
    for fac, day in _chain_keys(date_from, date_to, facility_id):

        def problem(
            kind: str, message: str, seq: int | None = None, f: int = fac, d: date = day
        ) -> None:
            problems.append(Problem(f, d, seq, kind, message))

        events = list(AuditEvent.objects.filter(facility_id=fac, chain_date=day).order_by("seq"))
        expected_prev = _expected_first_prev(fac, day)
        expected_seq = 1
        for event in events:
            checked += 1
            if event.seq != expected_seq:
                problem("missing", f"expected seq {expected_seq}, found {event.seq}", event.seq)
                expected_seq = event.seq
            if event.prev_hash != expected_prev:
                problem(
                    "broken-link", "previous-hash does not match the preceding event", event.seq
                )
            if compute_hash(event.prev_hash, event) != event.hash:
                problem("modified", "content does not match its hash", event.seq)
            expected_prev = event.hash
            expected_seq += 1

        last_hash = events[-1].hash if events else None
        count = events[-1].seq if events else 0
        head = AuditChainHead.objects.filter(facility_id=fac, chain_date=day).first()
        if head and (head.last_seq != count or head.last_hash != last_hash):
            problem("head-mismatch", f"head says {head.last_seq} events, chain has {count}")
        anchor = AuditAnchor.objects.filter(facility_id=fac, chain_date=day).first()
        if anchor and (anchor.event_count != count or anchor.last_hash != last_hash):
            problem(
                "anchor-mismatch", f"anchor says {anchor.event_count} events, chain has {count}"
            )
        file_entry = file_anchors.get((fac, day))
        if anchor and not file_entry:
            problem("anchor-file", "anchor missing from the anchor file")
        if file_entry and (
            file_entry["event_count"] != count or file_entry["last_hash"] != last_hash
        ):
            problem(
                "anchor-file",
                f"anchor file says {file_entry['event_count']} events, chain has {count}",
            )
    return checked, problems
