"""Payment-gate policy engine (DESIGN §6.4, P2-VIS-02; KE-HLT-01, KE-HLT-02, ADR-013).

``evaluate(visit, context)`` answers "may this service start now?". Two rules are code, not
data, so no configuration can break them:

- an emergency visit passes every gate, at every service point;
- discharge is never a gate context: ``evaluate_discharge`` always clears.

Gate checks are pluggable: billing registers ``pay_before_service``, ``deposit`` and
``credit_limit``; the insurance lane may replace the cover checks and register the
pre-authorisation flag. Until a checker exists for a gate, the gate is *not* cleared and the
reason says so (fail closed for money, never for emergencies or discharge).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.access import approvals, policies
from apps.access.models import ApprovalRequest
from apps.audit.services import record
from apps.core.problems import Conflict
from apps.insurance import selectors as insurance
from apps.visits.models import GateContext, GateOverride, GatePolicy, GateType, PayerType, Visit

G, C, P = GateType, GateContext, PayerType
IF_FLAGGED = GatePolicy.Condition.IF_FLAGGED

# DESIGN §6.4 defaults: (context, payer type) -> (gate, condition). Emergency and discharge
# rows are not data (see module docstring). Pharmacy for SHA: covered items are not gated;
# uncovered items are paid by the patient — billing's responsibility split decides which.
DEFAULTS: dict[tuple[str, str], tuple[str, str]] = {
    (C.CONSULTATION, P.CASH): (G.PAY_BEFORE_SERVICE, "always"),
    (C.CONSULTATION, P.SHA): (G.ELIGIBILITY_VERIFIED, "always"),
    (C.CONSULTATION, P.INSURER): (G.MEMBER_VERIFIED, "always"),
    (C.CONSULTATION, P.CORPORATE): (G.CREDIT_LIMIT, "always"),
    (C.CONSULTATION, P.WAIVER): (G.NONE, "always"),
    **{
        (ctx, payer): gate
        for ctx in (C.LAB, C.IMAGING, C.PROCEDURE)
        for payer, gate in (
            (P.CASH, (G.PAY_BEFORE_SERVICE, "always")),
            (P.SHA, (G.PREAUTH_APPROVED, IF_FLAGGED)),
            (P.INSURER, (G.PREAUTH_APPROVED, IF_FLAGGED)),
            (P.CORPORATE, (G.CREDIT_LIMIT, "always")),
            (P.WAIVER, (G.NONE, "always")),
        )
    },
    (C.PHARMACY, P.CASH): (G.PAY_BEFORE_SERVICE, "always"),
    (C.PHARMACY, P.SHA): (G.PAY_BEFORE_SERVICE, IF_FLAGGED),
    (C.PHARMACY, P.INSURER): (G.PAY_BEFORE_SERVICE, IF_FLAGGED),
    (C.PHARMACY, P.CORPORATE): (G.CREDIT_LIMIT, "always"),
    (C.PHARMACY, P.WAIVER): (G.NONE, "always"),
    (C.ELECTIVE_ADMISSION, P.CASH): (G.DEPOSIT, "always"),
    (C.ELECTIVE_ADMISSION, P.SHA): (G.ELIGIBILITY_VERIFIED, "always"),
    (C.ELECTIVE_ADMISSION, P.INSURER): (G.PREAUTH_APPROVED, "always"),
    (C.ELECTIVE_ADMISSION, P.CORPORATE): (G.CREDIT_LIMIT, "always"),
    (C.ELECTIVE_ADMISSION, P.WAIVER): (G.NONE, "always"),
}

POLICY_CHANGE = "visits.gate_policy.set"


@dataclass(frozen=True)
class GateDecision:
    cleared: bool
    gate: str
    reason: str
    context: str
    override_id: Any = None
    details: dict[str, Any] = field(default_factory=dict)


# fn(visit, context, subject) -> (cleared, PHI-free reason, details)
Checker = Callable[[Visit, str, Any], tuple[bool, str, dict[str, Any]]]
# fn(visit, context, subject) -> does the scheme/intervention flag this service?
Flagger = Callable[[Visit, str, Any], bool]
_checkers: dict[str, Checker] = {}
_flaggers: dict[str, Flagger] = {}


def register_checker(gate: str, fn: Checker) -> None:
    _checkers[gate] = fn


def register_flagger(name: str, fn: Flagger) -> None:
    """Phase 3 registers SHA/insurer pre-authorisation flags; pharmacy coverage flags too."""
    _flaggers[name] = fn


def _flagged(visit: Visit, context: str, subject: Any) -> bool:
    return any(fn(visit, context, subject) for fn in _flaggers.values())


def _cover_verified(visit: Visit, context: str, subject: Any) -> tuple[bool, str, dict[str, Any]]:
    coverage = visit.coverage
    if coverage is None:
        return False, "No cover is attached to this visit.", {}
    if not insurance.is_current(coverage):
        return False, "The cover is not current.", {}
    if coverage.verification != "verified":
        return False, "The cover has not been verified with the payer yet.", {}
    return True, "Cover verified.", {}


register_checker(G.ELIGIBILITY_VERIFIED, _cover_verified)
register_checker(G.MEMBER_VERIFIED, _cover_verified)


def policy_for(visit: Visit, context: str) -> GatePolicy | None:
    return GatePolicy.objects.filter(
        facility_id=visit.facility_id, context=context, payer_type=visit.payer_type
    ).first()


def active_override(visit: Visit, context: str) -> GateOverride | None:
    return GateOverride.objects.filter(visit=visit, context=context).order_by("-created_at").first()


def evaluate(visit: Visit, context: str, *, subject: Any = None) -> GateDecision:
    """May the service in ``context`` start for ``visit``? ``subject`` is the order, charge or
    prescription item being gated (checkers use it to find what must be paid)."""
    if context not in GateContext.values:
        raise ValidationError({"context": "Unknown gate context."})
    if visit.is_emergency:
        return GateDecision(True, G.NONE, "Emergency care is never held for payment.", context)
    override = active_override(visit, context)
    if override is not None:
        return GateDecision(True, override.gate, "Gate overridden.", context, override.pk)
    policy = policy_for(visit, context)
    gate, condition = (
        (policy.gate, policy.condition)
        if policy
        else DEFAULTS.get((context, visit.payer_type), (G.NONE, "always"))
    )
    if gate == G.NONE or (condition == IF_FLAGGED and not _flagged(visit, context, subject)):
        return GateDecision(True, G.NONE, "No gate applies.", context)
    checker = _checkers.get(gate)
    if checker is None:
        return GateDecision(False, gate, "This check is not available yet.", context)
    cleared, reason, details = checker(visit, context, subject)
    return GateDecision(cleared, gate, reason, context, details=details)


class GateBlocked(Conflict):
    default_detail = "Payment or cover is needed before this service starts."
    default_code = "gate_not_cleared"

    def __init__(self, decision: GateDecision) -> None:
        super().__init__(decision.reason)
        self.extra = {"gate": decision.gate, "context": decision.context, **decision.details}


def enforce(visit: Visit, context: str, *, actor: Any, subject: Any = None) -> GateDecision:
    """Evaluate and refuse (409 ``gate_not_cleared``) when the gate holds. Emergency bypasses
    and overrides used are audited so the record shows why no payment was asked (E2E-04)."""
    decision = evaluate(visit, context, subject=subject)
    if visit.is_emergency:
        record(
            "visits.gate.emergency_bypass",
            actor,
            visit,
            patient=visit.patient_id,
            detail={"context": context},
        )
    elif decision.override_id is not None:
        record(
            "visits.gate.override_used",
            actor,
            visit,
            patient=visit.patient_id,
            detail={"context": context, "override_id": str(decision.override_id)},
        )
    if not decision.cleared:
        raise GateBlocked(decision)
    return decision


def evaluate_discharge(visit: Visit) -> GateDecision:
    """Discharge is never gated, for any payer (DESIGN §6.4, ADR-013, KE-HLT-02)."""
    return GateDecision(True, G.NONE, "Discharge is never held for payment.", "discharge")


@transaction.atomic
def override(
    visit: Visit, context: str, *, actor: Any, reason_code: str, reason: str
) -> GateOverride:
    if not policies.has_permission(actor, "visits.gate.override", facility=visit.facility_id):
        raise PermissionDenied("You do not have permission to override payment gates.")
    if reason_code not in GateOverride.ReasonCode.values:
        raise ValidationError({"reason_code": "Choose a reason."})
    if not reason.strip():
        raise ValidationError({"reason": "Explain the override."})
    decision = evaluate(visit, context)
    row = GateOverride.objects.create(
        facility_id=visit.facility_id,
        visit=visit,
        context=context,
        gate=decision.gate,
        reason_code=reason_code,
        reason=reason.strip()[:255],
        created_by=actor,
        updated_by=actor,
    )
    record(
        "visits.gate.overridden",
        actor,
        row,
        patient=visit.patient_id,
        severity="notice",
        detail={"context": context, "gate": decision.gate, "reason_code": reason_code},
    )
    return row


# --- Policies (maker-checker) ---------------------------------------------------------------------


def seed_defaults(facility: Any) -> int:
    created = 0
    for (context, payer), (gate, condition) in DEFAULTS.items():
        _, new = GatePolicy.objects.get_or_create(
            facility_id=getattr(facility, "pk", facility),
            context=context,
            payer_type=payer,
            defaults={"gate": gate, "condition": condition},
        )
        created += int(new)
    return created


@transaction.atomic
def request_policy_change(
    *,
    facility: Any,
    context: str,
    payer_type: str,
    gate: str,
    condition: str,
    actor: Any,
    reason: str,
) -> ApprovalRequest:
    facility_id = getattr(facility, "pk", facility)
    if not policies.has_permission(actor, "visits.gate.manage", facility=facility_id):
        raise PermissionDenied("You do not have permission to change payment gates.")
    if context not in GateContext.values or payer_type not in PayerType.values:
        raise ValidationError({"context": "Choose a context and payer type."})
    if gate not in GateType.values or condition not in GatePolicy.Condition.values:
        raise ValidationError({"gate": "Choose a gate and condition."})
    return approvals.request_approval(
        action=POLICY_CHANGE,
        facility=facility_id,
        requested_by=actor,
        payload={
            "context": context,
            "payer_type": payer_type,
            "gate": gate,
            "condition": condition,
        },
        required_permissions=["visits.gate.manage"],
        reason=reason,
        resource=("visits.gatepolicy", f"{context}/{payer_type}"),
    )


def _execute_policy_change(request: ApprovalRequest, approver: Any) -> None:
    data = request.payload
    policy, _ = GatePolicy.objects.select_for_update().get_or_create(
        facility_id=request.facility_id,
        context=data["context"],
        payer_type=data["payer_type"],
        defaults={"gate": data["gate"], "condition": data["condition"]},
    )
    previous = policy.gate
    policy.gate, policy.condition, policy.approval = data["gate"], data["condition"], request
    policy.save()
    record(
        "visits.gate_policy.changed",
        approver,
        policy,
        facility=request.facility_id,
        detail={**data, "previous": previous, "approval_id": str(request.pk)},
    )


def register_executors() -> None:
    approvals.register_executor(POLICY_CHANGE, _execute_policy_change)
