"""Reads of patient data, shaped by the chart access level (DESIGN §7.7) and audited.

Every function here that returns PHI asks ``access.chart`` first and records the read.
Later phases add their sections (allergies, problems, notes, results…) to ``chart``.
"""

from typing import Any

from apps.access import chart
from apps.access.roles import ChartAccess
from apps.audit.models import AuditEvent
from apps.audit.services import record
from apps.core.problems import ApiProblem
from apps.patients.models import Patient


class ChartAccessDenied(ApiProblem):
    status_code = 403
    default_detail = "Your role does not give access to this part of the record."
    default_code = "chart_access_insufficient"

    def __init__(self, decision: chart.ChartAccessDecision, needed: ChartAccess) -> None:
        super().__init__()
        self.extra = {
            "access_level": decision.level.value,
            "needed_level": needed.value,
            "break_glass_available": decision.may_break_glass,
        }


def access_payload(decision: chart.ChartAccessDecision) -> dict[str, Any]:
    """What the UI needs for the access banner."""
    grant = decision.break_glass
    return {
        "level": decision.level.value,
        "care_team": decision.care_team,
        "break_glass": (
            {
                "id": str(grant.pk),
                "reason": grant.reason,
                "expires_at": grant.expires_at.isoformat(),
            }
            if grant is not None
            else None
        ),
        "break_glass_available": decision.may_break_glass,
    }


def open_record(
    user: Any,
    patient: Patient,
    *,
    purpose: str,
    needed: ChartAccess,
    action: str = "patients.chart.opened",
) -> chart.ChartAccessDecision:
    """Decide, audit and return the access decision; raise 403 when the level is too low."""
    purpose = purpose if purpose in chart.PURPOSES else "care"
    decision = chart.decide(user, patient, purpose=purpose)
    if not decision.allows(needed):
        record(
            "patients.chart.denied",
            user,
            patient,
            patient=patient,
            purpose=purpose,
            outcome=AuditEvent.Outcome.DENIED,
            detail={"level": decision.level.value, "needed": needed.value},
        )
        raise ChartAccessDenied(decision, needed)
    grant = decision.break_glass
    record(
        action,
        user,
        patient,
        patient=patient,
        purpose=purpose,
        severity="high" if grant is not None else "info",
        detail={
            "level": decision.level.value,
            "break_glass_id": str(grant.pk) if grant is not None else None,
        },
    )
    return decision


def chart_sections(patient: Patient, decision: chart.ChartAccessDecision) -> dict[str, Any]:
    """Clinical sections by level. Phase 2 adds notes, diagnoses and results; items flagged
    sensitive are placeholders unless the level is ``sensitive`` (P1-UAC-09)."""
    from apps.documents.selectors import for_patient as documents_for

    summary: dict[str, Any] | None = None
    record_: dict[str, Any] | None = None
    if decision.allows(ChartAccess.SUMMARY):
        summary = {
            "allergies": [],
            "alerts": [],
            "problems": [],
            "medications": [],
            "current_visit": None,
        }
    if decision.allows(ChartAccess.FULL):
        record_ = {
            "notes": [],
            "diagnoses": [],
            "results": [],
            "documents": documents_for(patient, decision),
        }
    return {"summary": summary, "record": record_}
