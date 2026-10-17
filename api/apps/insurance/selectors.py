"""Reads of payers, schemes and coverage — the API Phase 2 uses (docs/agent/lanes/SEAMS.md)."""

from datetime import date
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone

from apps.insurance.models import Coverage, Scheme
from apps.patients.identifiers import mask


def active_schemes() -> QuerySet[Scheme]:
    """Schemes a visit can be billed to (cash / self-pay is "no scheme")."""
    return Scheme.objects.filter(active=True, payer__active=True).select_related("payer")


def coverages_for(patient: Any, *, include_ended: bool = False) -> QuerySet[Coverage]:
    rows = Coverage.objects.filter(patient=patient).select_related("scheme__payer")
    return rows if include_ended else rows.filter(active=True)


def is_current(coverage: Coverage, on: date | None = None) -> bool:
    """Active and inside its validity window on ``on`` (default today)."""
    day = on or timezone.localdate()
    return (
        coverage.active
        and (coverage.valid_from is None or coverage.valid_from <= day)
        and (coverage.valid_to is None or day <= coverage.valid_to)
    )


def masked_member_number(coverage: Coverage) -> str:
    return mask(coverage.member_number)
