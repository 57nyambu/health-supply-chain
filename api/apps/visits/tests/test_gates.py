"""P2-VIS-02: payment gates. Emergency visits pass every gate; discharge is never gated
(Constitution Art. 43(2), Health Act; ADR-013; KE-HLT-01, KE-HLT-02). Never remove these."""

import pytest
from django.core.exceptions import PermissionDenied

from apps.access import approvals
from apps.audit.models import AuditEvent
from apps.insurance import services as insurance_services
from apps.insurance.seed import payers_and_schemes
from apps.visits import gates, services
from apps.visits.models import GateContext, GatePolicy, GateType, PayerType

pytestmark = pytest.mark.django_db


@pytest.fixture
def clerk(clinician):
    return clinician("receptionist")


@pytest.fixture
def defaults(facility):
    gates.seed_defaults(facility)


def test_defaults_cover_every_context_and_payer(facility, defaults):
    cells = set(GatePolicy.objects.filter(facility=facility).values_list("context", "payer_type"))
    assert cells == {(c, p) for c in GateContext.values for p in PayerType.values}
    assert gates.seed_defaults(facility) == 0  # idempotent
    assert "discharge" not in GateContext.values  # discharge can never be configured as a gate


@pytest.mark.req("KE-HLT-01")
@pytest.mark.parametrize("context", GateContext.values)
@pytest.mark.parametrize("payer", ["cash", "sha", "insurer", "corporate", "waiver"])
def test_emergency_visits_pass_every_gate(patient, clerk, points, facility, context, payer):
    GatePolicy.objects.create(
        facility=facility, context=context, payer_type=payer, gate=GateType.PAY_BEFORE_SERVICE
    )
    visit = services.open_visit(patient=patient, visit_type="emergency", actor=clerk)
    visit.payer_type = payer
    decision = gates.evaluate(visit, context)
    assert decision.cleared, decision


@pytest.mark.req("KE-HLT-02")
@pytest.mark.parametrize("visit_type", ["opd", "emergency", "inpatient"])
def test_discharge_is_never_gated(patient, clerk, points, facility, defaults, visit_type):
    visit = services.open_visit(patient=patient, visit_type=visit_type, actor=clerk)
    for payer in PayerType.values:
        visit.payer_type = payer
        assert gates.evaluate_discharge(visit).cleared


def test_cash_consultation_is_held_until_paid(patient, clerk, points, defaults):
    visit = services.open_visit(patient=patient, visit_type="opd", actor=clerk)
    decision = gates.evaluate(visit, "consultation")
    assert not decision.cleared and decision.gate == "pay_before_service"
    gates.register_checker("pay_before_service", lambda v, c, s: (True, "Paid.", {}))
    try:
        assert gates.evaluate(visit, "consultation").cleared
    finally:
        gates._checkers.pop("pay_before_service")


def test_sha_consultation_needs_verified_cover(patient, clerk, points, defaults):
    schemes = payers_and_schemes()
    cover = insurance_services.add_coverage(
        patient=patient, scheme=schemes["sha/shif"], member_number="SHA-SYN-9", actor=None
    )
    visit = services.open_visit(patient=patient, visit_type="opd", actor=clerk, coverage=cover)
    decision = gates.evaluate(visit, "consultation")
    assert not decision.cleared and decision.gate == "eligibility_verified"
    cover.verification = "verified"
    cover.save()
    visit.refresh_from_db()
    assert gates.evaluate(visit, "consultation").cleared


def test_preauth_applies_only_when_flagged(patient, clerk, points, defaults):
    visit = services.open_visit(patient=patient, visit_type="opd", actor=clerk)
    visit.payer_type = "sha"
    assert gates.evaluate(visit, "imaging").cleared  # nothing flags it
    gates.register_flagger("test", lambda v, c, s: c == "imaging")
    try:
        decision = gates.evaluate(visit, "imaging")
        assert not decision.cleared and decision.gate == "preauth_approved"
    finally:
        gates._flaggers.pop("test")


def test_waiver_visits_are_not_gated(patient, clerk, points, defaults):
    visit = services.open_visit(patient=patient, visit_type="opd", actor=clerk, waiver=True)
    assert visit.payer_type == "waiver"
    assert all(gates.evaluate(visit, c).cleared for c in GateContext.values)


def test_override_by_permitted_roles_is_audited_and_clears(
    patient, clerk, points, defaults, clinician
):
    visit = services.open_visit(patient=patient, visit_type="opd", actor=clerk)
    with pytest.raises(PermissionDenied):
        gates.override(
            visit, "consultation", actor=clerk, reason_code="payment_promised", reason="x"
        )
    superintendent = clinician("medical_superintendent")
    row = gates.override(
        visit,
        "consultation",
        actor=superintendent,
        reason_code="clinical_urgency",
        reason="Severe pain",
    )
    assert row.gate == "pay_before_service"
    decision = gates.evaluate(visit, "consultation")
    assert decision.cleared and decision.override_id == row.pk
    event = AuditEvent.objects.get(action="visits.gate.overridden")
    assert event.detail == {
        "context": "consultation",
        "gate": "pay_before_service",
        "reason_code": "clinical_urgency",
    }
    assert "Severe" not in str(event.detail)


def test_policy_change_needs_a_second_administrator(facility, defaults, clinician):
    admin_a, admin_b = clinician("facility_admin"), clinician("facility_admin")
    request = gates.request_policy_change(
        facility=facility,
        context="lab",
        payer_type="cash",
        gate="none",
        condition="always",
        actor=admin_a,
        reason="Free lab week",
    )
    with pytest.raises(PermissionDenied):
        approvals.approve(request, approver=admin_a)
    approvals.approve(request, approver=admin_b)
    policy = GatePolicy.objects.get(facility=facility, context="lab", payer_type="cash")
    assert policy.gate == "none" and policy.approval_id == request.pk
    with pytest.raises(PermissionDenied):
        gates.request_policy_change(
            facility=facility,
            context="lab",
            payer_type="cash",
            gate="none",
            condition="always",
            actor=clinician("receptionist"),
            reason="x",
        )


def test_api_gate_status_and_override(api_for, patient, points, defaults):
    reception = api_for("receptionist")
    visit_id = reception.post(
        "/api/v1/visits/", {"patient": str(patient.pk), "visit_type": "opd"}, format="json"
    ).json()["id"]
    decision = reception.get(f"/api/v1/visits/{visit_id}/gate/?context=consultation").json()
    assert decision["cleared"] is False and decision["gate"] == "pay_before_service"
    assert (
        reception.post(
            f"/api/v1/visits/{visit_id}/gate-override/",
            {"context": "consultation", "reason_code": "other", "reason": "x"},
            format="json",
        ).status_code
        == 403
    )
    nic = api_for("nurse", "nurse_in_charge")
    response = nic.post(
        f"/api/v1/visits/{visit_id}/gate-override/",
        {
            "context": "consultation",
            "reason_code": "payment_promised",
            "reason": "Relative bringing cash",
        },
        format="json",
    )
    assert response.status_code == 201
    detail = reception.get(f"/api/v1/visits/{visit_id}/").json()
    assert detail["gate_overrides"][0]["reason_code"] == "payment_promised"  # shown on the bill
    policies = api_for("facility_admin").get("/api/v1/visits/gate-policies/").json()
    assert len(policies) == len(GateContext.values) * len(PayerType.values)


def test_enforce_refuses_held_gates_and_audits_emergency_bypass(
    patient, clerk, points, defaults, facility
):
    from apps.patients.tests.factories import PatientFactory

    visit = services.open_visit(patient=patient, visit_type="opd", actor=clerk)
    with pytest.raises(gates.GateBlocked) as blocked:
        gates.enforce(visit, "consultation", actor=clerk)
    assert blocked.value.extra["gate"] == "pay_before_service"
    emergency = services.open_visit(
        patient=PatientFactory.create(facility=facility), visit_type="emergency", actor=clerk
    )
    for context in GateContext.values:
        assert gates.enforce(emergency, context, actor=clerk).cleared
    bypasses = AuditEvent.objects.filter(action="visits.gate.emergency_bypass")
    assert sorted(e.detail["context"] for e in bypasses) == sorted(GateContext.values)


def test_visit_hooks_run_in_the_same_transaction(patient, clerk, points):
    seen = []
    services.register_hook("opened", "test.opened", lambda v, a: seen.append(("opened", v.pk)))
    services.register_hook("ended", "test.ended", lambda v, a: seen.append(("ended", v.status)))
    try:
        visit = services.open_visit(patient=patient, visit_type="opd", actor=clerk)
        services.transition(visit, "cancelled", actor=clerk, reason="Registered in error")
    finally:
        services._hooks["opened"].pop("test.opened")
        services._hooks["ended"].pop("test.ended")
    assert seen == [("opened", visit.pk), ("ended", "cancelled")]
    with pytest.raises(ValueError):
        services.register_hook("nope", "x", lambda v, a: None)
