"""P2-VIS-01: visits, state machine and queues."""

from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.access import care_team
from apps.audit.models import AuditEvent
from apps.core.models import OutboxEvent
from apps.core.problems import Conflict
from apps.insurance import services as insurance_services
from apps.insurance.seed import payers_and_schemes
from apps.patients.tests.factories import PatientFactory
from apps.visits import services
from apps.visits.models import QueueTicket, Visit, VisitStatus, VisitTransition
from apps.visits.services import TRANSITIONS, TransitionRefused

pytestmark = pytest.mark.django_db
S = VisitStatus
URL = "/api/v1/visits/"


@pytest.fixture
def clerk(clinician):
    return clinician("receptionist")


def open_opd(patient, clerk, **kw):
    return services.open_visit(patient=patient, visit_type="opd", actor=clerk, **kw)


def test_opening_numbers_queues_audits_and_emits(patient, clerk, points, facility):
    visit = open_opd(patient, clerk)
    today = timezone.localtime().strftime("%y%m%d")
    assert visit.number == f"OP-{facility.mfl_code}-{today}-001"
    assert visit.status == S.AWAITING_TRIAGE
    assert visit.payer_type == "cash"
    ticket = visit.tickets.get()
    assert ticket.service_point == points["triage"]
    assert ticket.number == f"{points['triage'].code}-001"
    assert [t.to_status for t in visit.transitions.all()] == [S.REGISTERED, S.AWAITING_TRIAGE]
    event = OutboxEvent.objects.get(topic="visits.visit.opened")
    assert event.payload == {
        "visit_id": str(visit.pk),
        "patient_id": str(patient.pk),
        "visit_type": "opd",
        "coverage_id": None,
    }
    assert AuditEvent.objects.filter(action="visits.visit.opened", patient_id=patient.pk).exists()


def test_one_open_visit_per_patient_but_emergencies_never_refused(patient, clerk, points):
    first = open_opd(patient, clerk)
    with pytest.raises(services.OpenVisitExists) as raised:
        open_opd(patient, clerk)
    assert raised.value.extra == {"visit_id": str(first.pk)}
    emergency = services.open_visit(patient=patient, visit_type="emergency", actor=clerk)
    assert emergency.number.startswith("EM-")
    assert emergency.status == S.IN_TRIAGE
    assert emergency.tickets.get().service_point == points["emergency"]


def test_emergency_ignores_invalid_cover_but_opd_refuses_it(patient, clerk, points, facility):
    schemes = payers_and_schemes()
    other = PatientFactory.create(facility=facility)
    cover = insurance_services.add_coverage(
        patient=other, scheme=schemes["sha/shif"], member_number="SHA-SYN-1", actor=None
    )
    with pytest.raises(ValidationError):
        open_opd(patient, clerk, coverage=cover)
    visit = services.open_visit(
        patient=patient, visit_type="emergency", actor=clerk, coverage=cover
    )
    assert visit.coverage is None


def test_sha_cover_sets_payer_type(patient, clerk, points):
    schemes = payers_and_schemes()
    cover = insurance_services.add_coverage(
        patient=patient, scheme=schemes["sha/shif"], member_number="SHA-SYN-2", actor=None
    )
    visit = open_opd(patient, clerk, coverage=cover)
    assert visit.payer_type == "sha"
    assert OutboxEvent.objects.get(topic="visits.visit.opened").payload["coverage_id"] == str(
        cover.pk
    )


def test_walk_in_visits_go_to_services(patient, clerk, points):
    visit = services.open_visit(patient=patient, visit_type="walk_in_pharmacy", actor=clerk)
    assert visit.status == S.AWAITING_SERVICES
    assert visit.tickets.get().service_point == points["pharmacy"]


def test_only_services_change_status_and_invalid_transitions_are_refused(patient, clerk, points):
    visit = open_opd(patient, clerk)
    with pytest.raises(TransitionRefused):
        services.transition(visit, S.CLOSED, actor=None)
    with pytest.raises(TransitionRefused):
        services.transition(visit, S.AWAITING_SERVICES, actor=None)  # not a walk-in
    visit = services.transition(visit, S.IN_TRIAGE, actor=None)
    visit = services.transition(visit, S.AWAITING_CONSULTATION, actor=None)
    with pytest.raises(Conflict):
        services.transition(visit, S.IN_CONSULTATION, actor=None, expected_version=1)
    history = list(VisitTransition.objects.filter(visit=visit).values_list("to_status", flat=True))
    assert history == [S.REGISTERED, S.AWAITING_TRIAGE, S.IN_TRIAGE, S.AWAITING_CONSULTATION]


def test_every_state_is_in_the_machine_and_terminal_states_are_final():
    assert set(TRANSITIONS) == set(VisitStatus.values)
    for terminal in (S.CLOSED, S.CANCELLED, S.LEFT_BEFORE_SEEN):
        assert TRANSITIONS[terminal] == set()


def test_cancel_needs_reason_and_permission(patient, clerk, points, clinician):
    visit = open_opd(patient, clerk)
    nurse = clinician("triage_nurse")
    with pytest.raises(PermissionDenied):
        services.transition(visit, S.CANCELLED, actor=nurse, reason="x", check_permission=True)
    with pytest.raises(ValidationError):
        services.transition(visit, S.CANCELLED, actor=clerk, reason=" ", check_permission=True)
    visit = services.transition(
        visit, S.CANCELLED, actor=clerk, reason="Registered in error", check_permission=True
    )
    assert visit.closed_at is not None
    assert visit.tickets.get().status == QueueTicket.Status.CANCELLED
    event = OutboxEvent.objects.get(topic="visits.visit.closed")
    assert event.payload == {"visit_id": str(visit.pk), "outcome": "cancelled"}


def test_registered_requirements_block_completion(patient, clerk, points):
    visit = open_opd(patient, clerk)
    for status in (S.IN_TRIAGE, S.AWAITING_CONSULTATION, S.IN_CONSULTATION):
        visit = services.transition(visit, status, actor=None)
    services.register_requirement(S.CLINICALLY_COMPLETE, "test.always", lambda v: ["Needs X."])
    try:
        with pytest.raises(TransitionRefused) as refused:
            services.transition(visit, S.CLINICALLY_COMPLETE, actor=None)
        assert refused.value.extra == {"unmet": ["Needs X."]}
    finally:
        services._requirements[S.CLINICALLY_COMPLETE].pop("test.always")


def test_queue_order_is_triage_then_priority_then_arrival(facility, clerk, points):
    def arrive(minutes_ago):
        visit = open_opd(PatientFactory.create(facility=facility), clerk)
        ticket = visit.tickets.get()
        QueueTicket.objects.filter(pk=ticket.pk).update(
            arrived_at=timezone.now() - timedelta(minutes=minutes_ago)
        )
        return visit, ticket

    (green_early, t1), (yellow_late, t2), (green_late, t3), (_untriaged, t4) = (
        arrive(50),
        arrive(10),
        arrive(5),
        arrive(60),
    )
    services.set_triage_category(green_early, "green", actor=None)
    services.set_triage_category(yellow_late, "yellow", actor=None)
    services.set_triage_category(green_late, "green", actor=None)
    services.prioritise(t3, actor=clerk, reason_code="elderly")
    order = [t.pk for t in services.waiting(points["triage"])]
    assert order == [t2.pk, t3.pk, t1.pk, t4.pk]
    assert AuditEvent.objects.filter(action="visits.ticket.prioritised").exists()


def test_call_next_skip_recall_transfer_and_care_team(patient, clerk, points, clinician):
    visit = open_opd(patient, clerk)
    nurse = clinician("triage_nurse")
    ticket = services.call_next(points["triage"], actor=nurse, room="Triage room A")
    assert ticket.status == QueueTicket.Status.CALLED and ticket.room == "Triage room A"
    assert care_team.is_member(nurse, patient)
    assert services.call_next(points["triage"], actor=nurse) is None  # nobody else waiting
    ticket = services.skip(ticket, actor=nurse)
    assert ticket.status == QueueTicket.Status.WAITING and ticket.requeued_at
    ticket = services.call(ticket, actor=nurse)
    assert ticket.call_count == 2
    ticket = services.start_serving(ticket, actor=nurse)
    new = services.transfer(ticket, points["consultation"], actor=nurse)
    assert new.service_point == points["consultation"] and new.status == QueueTicket.Status.WAITING
    with pytest.raises(ValidationError):
        services.transfer(new, points["triage"], actor=nurse, send_back=True)
    back = services.transfer(new, points["triage"], actor=nurse, note="Repeat BP", send_back=True)
    assert back.note == "Repeat BP"
    assert visit.tickets.filter(status=QueueTicket.Status.TRANSFERRED).count() == 2


def test_left_before_seen_after_n_calls_needs_confirmation(patient, clerk, points, clinician):
    visit = open_opd(patient, clerk)
    nurse = clinician("triage_nurse")
    services.queue_settings(visit.facility)  # defaults: 3 calls
    ticket = visit.tickets.get()
    for _ in range(3):
        ticket = services.call(ticket, actor=nurse)
        ticket = services.skip(ticket, actor=nurse)
    assert ticket.lwbs_flagged_at is not None
    assert list(services.lwbs_work_queue(visit.facility)) == [ticket]
    visit = services.confirm_left_before_seen(ticket, actor=nurse)
    assert visit.status == S.LEFT_BEFORE_SEEN
    assert visit.tickets.get().status == QueueTicket.Status.LEFT
    assert (
        OutboxEvent.objects.get(topic="visits.visit.closed").payload["outcome"]
        == "left_before_seen"
    )


def test_idle_tickets_are_flagged_by_the_job_and_can_be_dismissed(
    patient, clerk, points, clinician
):
    visit = open_opd(patient, clerk)
    services.queue_settings(visit.facility)
    QueueTicket.objects.filter(visit=visit).update(arrived_at=timezone.now() - timedelta(hours=5))
    assert services.flag_idle_tickets() == 1
    assert services.flag_idle_tickets() == 0  # idempotent
    ticket = services.dismiss_left_before_seen(visit.tickets.get(), actor=clinician("triage_nurse"))
    assert ticket.lwbs_flagged_at is None
    with pytest.raises(TransitionRefused):
        services.confirm_left_before_seen(ticket, actor=clerk)


def test_api_open_list_detail_and_queue(api_for, facility, patient, points):
    reception = api_for("receptionist")
    response = reception.post(URL, {"patient": str(patient.pk), "visit_type": "opd"}, format="json")
    assert response.status_code == 201, response.json()
    visit_id = response.json()["id"]
    again = reception.post(URL, {"patient": str(patient.pk), "visit_type": "opd"}, format="json")
    assert again.status_code == 409 and again.json()["visit_id"] == visit_id
    rows = reception.get(URL + "?open=true").json()["results"]
    assert [r["id"] for r in rows] == [visit_id]
    assert rows[0]["patient"]["display_name"] == patient.display_name
    detail = reception.get(URL + f"{visit_id}/?purpose=registration").json()
    assert [t["to_status"] for t in detail["transitions"]] == [S.REGISTERED, S.AWAITING_TRIAGE]
    assert AuditEvent.objects.filter(action="visits.visit.viewed", patient_id=patient.pk).exists()
    nurse = api_for("triage_nurse")
    queues = {q["code"]: q for q in nurse.get(URL + "queues/").json()}
    assert queues[points["triage"].code]["waiting"] == 1
    called = nurse.post(URL + f"queues/{points['triage'].pk}/call-next/", {}, format="json")
    assert called.status_code == 200 and called.json()["visit"]["id"] == visit_id
    assert (
        nurse.post(URL + f"queues/{points['triage'].pk}/call-next/", {}, format="json").status_code
        == 204
    )
    started = nurse.post(URL + f"tickets/{called.json()['id']}/start/")
    assert started.json()["status"] == "serving"
    moved = nurse.post(URL + f"{visit_id}/transition/", {"to": "in_triage"}, format="json")
    assert moved.status_code == 200 and moved.json()["status"] == "in_triage"
    refused = reception.post(
        URL + f"{visit_id}/transition/", {"to": "in_consultation"}, format="json"
    )
    assert refused.status_code == 403


def test_api_transition_refusal_is_problem_json(api_for, patient, points):
    reception = api_for("receptionist")
    visit_id = reception.post(
        URL, {"patient": str(patient.pk), "visit_type": "opd"}, format="json"
    ).json()["id"]
    response = reception.post(URL + f"{visit_id}/transition/", {"to": "closed"}, format="json")
    assert response.status_code == 403  # closing needs billing permission first
    billing = api_for("billing_officer")
    response = billing.post(URL + f"{visit_id}/transition/", {"to": "closed"}, format="json")
    assert response.status_code == 409
    assert response.json()["code"] == "visit_transition_refused"


def test_visits_of_other_facilities_are_invisible(api_for, patient, points):
    other = PatientFactory.create()
    visit = Visit.objects.create(
        facility=other.facility,
        number="OP-X-1",
        patient=other,
        visit_type="opd",
        opened_at=timezone.now(),
        status_changed_at=timezone.now(),
    )
    reception = api_for("receptionist")
    assert reception.get(URL + f"{visit.pk}/").status_code == 404
