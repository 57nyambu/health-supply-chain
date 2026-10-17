"""The Phase 2 facts claims are built from (docs/agent/lanes/SEAMS.md §3; ADR-071).

Phase 3 reads visits, diagnoses, practitioners and billable lines only through three
selectors that Phase 2 publishes::

    apps.visits.selectors.visit_for_claim(visit_id) -> VisitForClaim
    apps.billing.selectors.claimable_lines(visit_id, coverage_id) -> list[ClaimableLine]
    apps.billing.selectors.invoice_for_party(visit_id, coverage_id) -> InvoiceSummary | None

Until they are on ``main``, ``facts()`` returns ``FakeClinicalFacts`` — an in-memory source
that tests (and the fake-mode demo) fill with synthetic visits. When Phase 2's modules exist
``facts()`` switches to them without any change to the claims code (stage B replaces the
fake with the real selectors; the Protocol below is the contract both must satisfy).
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol, cast


@dataclass(frozen=True)
class AttendingPractitioner:
    user_id: int
    regulator: str
    registration_number: str
    puid: str


@dataclass(frozen=True)
class VisitDiagnosis:
    icd11_code: str
    title: str
    primary: bool


@dataclass(frozen=True)
class VisitForClaim:
    visit_id: str
    number: str
    patient_id: str
    facility_id: int
    visit_type: str  # opd | emergency | inpatient
    opened_at: datetime
    closed_at: datetime | None
    coverage_id: str | None
    practitioners: tuple[AttendingPractitioner, ...] = ()
    diagnoses: tuple[VisitDiagnosis, ...] = ()
    admission_id: str | None = None


@dataclass(frozen=True)
class ClaimableLine:
    charge_id: str
    service_code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    serviced_on: date
    sha_interventions: tuple[str, ...] = ()
    preauth_required: bool = False


@dataclass(frozen=True)
class InvoiceSummary:
    number: str
    total: Decimal
    status: str


class ClinicalFacts(Protocol):
    def visit_for_claim(self, visit_id: str) -> VisitForClaim: ...

    def claimable_lines(self, visit_id: str, coverage_id: str) -> list[ClaimableLine]: ...

    def invoice_for_party(self, visit_id: str, coverage_id: str) -> InvoiceSummary | None: ...


class VisitNotFound(LookupError):
    pass


@dataclass
class FakeClinicalFacts:
    """In-memory ``ClinicalFacts`` for tests and fake-mode demos (synthetic data only)."""

    visits: dict[str, VisitForClaim] = field(default_factory=dict)
    lines: dict[tuple[str, str], list[ClaimableLine]] = field(default_factory=dict)
    invoices: dict[tuple[str, str], InvoiceSummary] = field(default_factory=dict)

    def add_visit(
        self,
        visit: VisitForClaim,
        *,
        lines: list[ClaimableLine] | None = None,
        invoice: InvoiceSummary | None = None,
    ) -> VisitForClaim:
        self.visits[visit.visit_id] = visit
        if visit.coverage_id and lines is not None:
            self.lines[(visit.visit_id, visit.coverage_id)] = list(lines)
        if visit.coverage_id and invoice is not None:
            self.invoices[(visit.visit_id, visit.coverage_id)] = invoice
        return visit

    def visit_for_claim(self, visit_id: str) -> VisitForClaim:
        try:
            return self.visits[str(visit_id)]
        except KeyError as exc:
            raise VisitNotFound(str(visit_id)) from exc

    def claimable_lines(self, visit_id: str, coverage_id: str) -> list[ClaimableLine]:
        return list(self.lines.get((str(visit_id), str(coverage_id)), []))

    def invoice_for_party(self, visit_id: str, coverage_id: str) -> InvoiceSummary | None:
        return self.invoices.get((str(visit_id), str(coverage_id)))


class _PhaseTwoFacts:
    """The real selectors once Phase 2 delivers them (SEAMS §3)."""

    def __init__(self, visits: Any, billing: Any) -> None:
        self._visits = visits
        self._billing = billing

    def visit_for_claim(self, visit_id: str) -> VisitForClaim:
        return cast(VisitForClaim, self._visits.visit_for_claim(visit_id))

    def claimable_lines(self, visit_id: str, coverage_id: str) -> list[ClaimableLine]:
        return list(self._billing.claimable_lines(visit_id, coverage_id))

    def invoice_for_party(self, visit_id: str, coverage_id: str) -> InvoiceSummary | None:
        return cast(InvoiceSummary | None, self._billing.invoice_for_party(visit_id, coverage_id))


_fake = FakeClinicalFacts()
_override: ClinicalFacts | None = None


def _phase_two() -> ClinicalFacts | None:
    try:
        visits = importlib.import_module("apps.visits.selectors")
        billing = importlib.import_module("apps.billing.selectors")
    except ImportError:
        return None
    needed = (
        hasattr(visits, "visit_for_claim")
        and hasattr(billing, "claimable_lines")
        and hasattr(billing, "invoice_for_party")
    )
    return _PhaseTwoFacts(visits, billing) if needed else None


def facts() -> ClinicalFacts:
    """The source claims are built from: an override (tests), Phase 2's selectors, or the fake."""
    if _override is not None:
        return _override
    return _phase_two() or _fake


def fake_facts() -> FakeClinicalFacts:
    return _fake


def use(source: ClinicalFacts | None) -> None:
    """Point ``facts()`` at ``source`` (tests); ``None`` restores the default."""
    global _override
    _override = source
