from datetime import timedelta

import pytest
import time_machine
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.access import breakglass, care_team, chart
from apps.access.models import BreakGlassGrant, CareTeamMember, Role
from apps.access.roles import ChartAccess as C
from apps.audit.models import AuditEvent
from apps.integrations.models import Notification
from apps.integrations.notify import deliver_pending
from apps.patients import selectors
from apps.patients.tests.factories import PatientFactory

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DPA-06")]

REASON = "Patient collapsed in the corridor"


@pytest.fixture
def patient(facility):
    return PatientFactory.create(facility=facility)


def on_team(patient, user, source_id="visit-1"):
    return care_team.add_member(patient=patient, user=user, source="visit", source_id=source_id)


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("receptionist", C.DEMOGRAPHICS),
        ("cashier", C.DEMOGRAPHICS),
        ("billing_officer", C.DEMOGRAPHICS),
        ("hrio", C.SUMMARY),
        ("triage_nurse", C.SUMMARY),
        ("pharmacist", C.SUMMARY),
        ("nurse", C.SUMMARY),
        ("clinical_officer", C.SUMMARY),
        ("medical_superintendent", C.FULL),
        ("system_admin", C.NONE),
        ("finance_manager", C.NONE),
        ("store_keeper", C.NONE),
        ("dpo", C.NONE),
    ],
)
def test_levels_without_a_care_relationship(staff, patient, role, expected):
    assert chart.check_chart_access(staff(role), patient) == expected


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("receptionist", C.DEMOGRAPHICS),
        ("triage_nurse", C.SUMMARY),
        ("nurse", C.FULL),
        ("clinical_officer", C.FULL),
        ("medical_officer", C.FULL),
        ("medical_superintendent", C.SENSITIVE),
    ],
)
def test_levels_on_the_care_team(staff, patient, role, expected):
    user = staff(role)
    on_team(patient, user)
    decision = chart.decide(user, patient)
    assert (decision.level, decision.care_team) == (expected, True)


def test_no_licence_no_full_record(staff, patient):
    clinician = staff("clinical_officer", licensed=False)
    on_team(patient, clinician)
    assert chart.check_chart_access(clinician, patient) == C.SUMMARY


def test_other_facilities_and_anonymous_users_get_nothing(staff, patient, make_user):
    from apps.facilities.tests.factories import FacilityFactory

    elsewhere = PatientFactory.create(facility=FacilityFactory.create())
    assert chart.check_chart_access(staff("medical_superintendent"), elsewhere) == C.NONE
    assert chart.check_chart_access(None, patient) == C.NONE
    assert chart.check_chart_access(make_user(), patient) == C.NONE


def test_registration_and_billing_purposes_see_demographics_only(staff, patient):
    clinician = staff("clinical_officer")
    on_team(patient, clinician)
    assert chart.check_chart_access(clinician, patient, "billing") == C.DEMOGRAPHICS
    assert chart.check_chart_access(clinician, patient, "registration") == C.DEMOGRAPHICS
    assert chart.check_chart_access(clinician, patient, "records") == C.FULL


def test_care_team_membership_expires_72_hours_after_the_episode_closes(staff, patient):
    clinician = staff("clinical_officer")
    on_team(patient, clinician)
    closed = timezone.now()
    assert care_team.close_episode(source="visit", source_id="visit-1", closed_at=closed) == 1
    assert chart.check_chart_access(clinician, patient) == C.FULL
    with time_machine.travel(closed + timedelta(hours=71)):
        assert chart.check_chart_access(clinician, patient) == C.FULL
    with time_machine.travel(closed + timedelta(hours=73)):
        assert chart.check_chart_access(clinician, patient) == C.SUMMARY
    assert AuditEvent.objects.filter(
        action="access.care_team.episode_closed", patient_id=patient.pk
    ).exists()


def test_the_expiry_window_is_a_facility_setting(staff, patient, facility):
    facility.care_team_expiry_hours = 24
    facility.save()
    clinician = staff("nurse")
    on_team(patient, clinician)
    closed = timezone.now()
    care_team.close_episode(source="visit", source_id="visit-1", closed_at=closed)
    with time_machine.travel(closed + timedelta(hours=25)):
        assert chart.check_chart_access(clinician, patient) == C.SUMMARY


def test_membership_is_idempotent_reopens_and_can_end_early(staff, patient):
    clinician = staff("clinical_officer")
    first = on_team(patient, clinician)
    assert on_team(patient, clinician).pk == first.pk
    care_team.close_episode(
        source="visit", source_id="visit-1", closed_at=timezone.now() - timedelta(days=5)
    )
    assert chart.check_chart_access(clinician, patient) == C.SUMMARY
    on_team(patient, clinician)  # the visit is reopened
    assert chart.check_chart_access(clinician, patient) == C.FULL
    care_team.remove_member(CareTeamMember.objects.get(pk=first.pk), removed_by=None)
    assert chart.check_chart_access(clinician, patient) == C.SUMMARY
    with pytest.raises(ValidationError):
        care_team.add_member(patient=patient, user=clinician, source="telepathy", source_id="x")


# --- break-glass ------------------------------------------------------------------------------------


def test_break_glass_grants_full_access_for_60_minutes(
    staff, patient, django_capture_on_commit_callbacks
):
    clinician = staff("clinical_officer")
    supt, dpo = staff("medical_superintendent"), staff("dpo")
    assert chart.decide(clinician, patient).may_break_glass
    with django_capture_on_commit_callbacks(execute=True):
        grant = breakglass.request_access(
            user=clinician, patient=patient, reason="emergency", justification=REASON
        )
    assert grant.expires_at - grant.granted_at == timedelta(minutes=60)
    decision = chart.decide(clinician, patient)
    assert (decision.level, decision.break_glass) == (C.FULL, grant)
    event = AuditEvent.objects.get(action="access.breakglass.granted")
    assert (event.severity, str(event.patient_id)) == ("high", str(patient.pk))
    assert REASON not in str(event.detail)
    with time_machine.travel(grant.expires_at + timedelta(minutes=1)):
        assert chart.check_chart_access(clinician, patient) == C.SUMMARY
    # Repeating the request inside the window returns the same grant.
    assert (
        breakglass.request_access(
            user=clinician, patient=patient, reason="emergency", justification=REASON
        )
        == grant
    )
    notified = Notification.objects.filter(subject="Break-glass access needs review")
    assert {n.user_id for n in notified} == {supt.pk, dpo.pk}
    for notice in notified:
        assert patient.family_name not in notice.message and patient.mrn not in notice.message
    # Stored with the grant; the outbox job e-mails them (no request waits on SMTP).
    assert not any(n.sent_at for n in notified) and not mail.outbox
    assert deliver_pending() == (2, 0)
    assert all(n.sent_at for n in notified.all())
    sent = [m for m in mail.outbox if m.subject == "Break-glass access needs review"]
    assert sorted(m.to[0] for m in sent) == sorted([supt.email, dpo.email])


def test_break_glass_never_reveals_sensitive_items_without_the_permission(staff, patient):
    nurse = staff("nurse")
    breakglass.request_access(user=nurse, patient=patient, reason="emergency", justification=REASON)
    assert chart.check_chart_access(nurse, patient) == C.FULL


def test_break_glass_needs_the_permission_a_reason_and_a_justification(staff, patient):
    with pytest.raises(PermissionDenied):
        breakglass.request_access(
            user=staff("receptionist"), patient=patient, reason="emergency", justification=REASON
        )
    clinician = staff("clinical_officer")
    with pytest.raises(ValidationError):
        breakglass.request_access(
            user=clinician, patient=patient, reason="curiosity", justification=REASON
        )
    with pytest.raises(ValidationError):
        breakglass.request_access(
            user=clinician, patient=patient, reason="emergency", justification="because"
        )
    on_team(patient, clinician)
    with pytest.raises(ValidationError):  # already has full access
        breakglass.request_access(
            user=clinician, patient=patient, reason="emergency", justification=REASON
        )
    unlicensed = staff("clinical_officer", licensed=False)
    with pytest.raises(PermissionDenied):
        breakglass.request_access(
            user=unlicensed, patient=patient, reason="emergency", justification=REASON
        )


def test_break_glass_can_be_ended_early(staff, patient):
    clinician = staff("clinical_officer")
    grant = breakglass.request_access(
        user=clinician, patient=patient, reason="clinical_review", justification=REASON
    )
    with pytest.raises(PermissionDenied):
        breakglass.end_access(grant, user=staff("clinical_officer"))
    breakglass.end_access(grant, user=clinician)
    assert chart.check_chart_access(clinician, patient) == C.SUMMARY
    assert AuditEvent.objects.filter(action="access.breakglass.ended").count() == 1
    breakglass.end_access(grant, user=clinician)  # already ended: nothing more
    assert AuditEvent.objects.filter(action="access.breakglass.ended").count() == 1


def test_review_justified_or_escalated(staff, patient):
    clinician = staff("clinical_officer")
    supt = staff("medical_superintendent")
    grant = breakglass.request_access(
        user=clinician, patient=patient, reason="emergency", justification=REASON
    )
    with pytest.raises(PermissionDenied):
        breakglass.review(grant, reviewer=staff("nurse"), outcome="justified")
    with pytest.raises(ValidationError):
        breakglass.review(grant, reviewer=supt, outcome="escalated")  # needs a note
    with pytest.raises(ValidationError):
        breakglass.review(grant, reviewer=supt, outcome="pending")
    reviewed = breakglass.review(grant, reviewer=supt, outcome="justified")
    assert (reviewed.review_status, reviewed.reviewed_by) == ("justified", supt)
    with pytest.raises(ValidationError):
        breakglass.review(grant, reviewer=staff("dpo"), outcome="escalated", note="Second look")


def test_nobody_reviews_their_own_break_glass(staff, patient, make_user, grant):
    both = staff("nurse")
    grant(both, "dpo", patient.facility)
    own = breakglass.request_access(
        user=both, patient=patient, reason="emergency", justification=REASON
    )
    with pytest.raises(PermissionDenied):
        breakglass.review(own, reviewer=both, outcome="justified")
    escalated = breakglass.review(
        own, reviewer=staff("dpo"), outcome="escalated", note="No visit found"
    )
    assert escalated.review_status == "escalated"
    assert AuditEvent.objects.get(action="access.breakglass.escalated").severity == "high"


def test_justification_is_encrypted_at_rest(staff, patient):
    from django.db import connection

    breakglass.request_access(
        user=staff("nurse"), patient=patient, reason="emergency", justification=REASON
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT justification FROM access_breakglassgrant")
        (stored,) = cursor.fetchone()
    assert stored.startswith("v1.") and "corridor" not in stored


# --- every PHI read goes through the chart decision -----------------------------------------------


def test_selectors_audit_denied_and_allowed_opens(staff, patient):
    clinician = staff("clinical_officer")
    with pytest.raises(selectors.ChartAccessDenied):
        selectors.open_record(clinician, patient, purpose="billing", needed=C.SUMMARY)
    denied = AuditEvent.objects.get(action="patients.chart.denied")
    assert (denied.outcome, denied.detail) == (
        "denied",
        {"level": "demographics", "needed": "summary"},
    )
    selectors.open_record(clinician, patient, purpose="nonsense", needed=C.SUMMARY)
    opened = AuditEvent.objects.get(action="patients.chart.opened")
    assert (opened.purpose, opened.detail["level"]) == ("care", "summary")


def test_a_custom_role_without_chart_access_cannot_search(api_as, facility):
    role = Role.objects.create(code="lookup_only", name="Lookup only")
    role.permissions.set(
        Role.objects.get(code="receptionist").permissions.filter(code="patients.patient.search")
    )
    client = api_as("lookup_only", facility=facility)
    response = client.post("/api/v1/patients/search/", {"q": "Synthetic"}, format="json")
    assert response.status_code == 403


@pytest.mark.req("KE-DPA-06")
def test_refused_requests_are_audited_for_the_dpo(api_as, facility, patient):
    """Reception asking for the clinical record is refused and the attempt is on record."""
    reception = api_as("receptionist", facility=facility)
    assert reception.get(f"/api/v1/patients/{patient.pk}/chart/").status_code == 403
    event = AuditEvent.objects.get(action="access.denied")
    assert (event.outcome, event.patient_id, event.actor_id, event.facility_id) == (
        "denied",
        patient.pk,
        reception.user.pk,
        facility.pk,
    )
    assert event.detail == {
        "permission": "clinical.record.read_summary",
        "endpoint": "PatientViewSet.chart",
    }
    # A malformed id in the URL is still refused and audited, without a patient.
    assert reception.get("/api/v1/patients/not-a-uuid/chart/").status_code == 403
    assert AuditEvent.objects.filter(action="access.denied", patient_id=None).count() == 1


def test_every_patient_read_endpoint_asks_the_chart_policy(api_as, facility, patient, monkeypatch):
    client = api_as("receptionist", "clinical_officer", facility=facility)
    monkeypatch.setattr(chart, "decide", lambda *args, **kwargs: chart.NO_ACCESS)
    base = f"/api/v1/patients/{patient.pk}/"
    assert client.get(base).status_code == 403
    assert client.get(f"{base}chart/").status_code == 403
    assert client.patch(base, {"version": 1, "middle_name": "X"}, format="json").status_code == 403
    assert (
        client.post(
            f"{base}contacts/", {"kind": "email", "value": "x@example.test"}, format="json"
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{base}identifiers/", {"type": "passport", "value": "AB1234567"}, format="json"
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{base}next-of-kin/",
            {"name": "Synthetic Kin", "relationship": "sister"},
            format="json",
        ).status_code
        == 403
    )


# --- API ------------------------------------------------------------------------------------------


def test_receptionist_cannot_open_the_clinical_record(api_as, facility, patient):
    reception = api_as("receptionist", facility=facility)
    assert reception.get(f"/api/v1/patients/{patient.pk}/chart/").status_code == 403
    demographics = reception.get(f"/api/v1/patients/{patient.pk}/").json()
    assert demographics["access"] == {
        "level": "demographics",
        "care_team": False,
        "break_glass": None,
        "break_glass_available": False,
    }


def test_clinician_sees_summary_then_full_after_break_glass(api_as, staff, facility, patient):
    clinician = staff("clinical_officer")
    client = api_as(facility=facility, user=clinician)
    url = f"/api/v1/patients/{patient.pk}/"
    before = client.get(f"{url}chart/").json()
    assert (
        before["access"]["level"] == "summary" and before["access"]["break_glass_available"] is True
    )
    assert before["summary"] is not None and before["record"] is None
    requested = client.post(
        f"{url}break-glass/", {"reason": "emergency", "justification": REASON}, format="json"
    )
    assert requested.status_code == 201
    after = client.get(f"{url}chart/").json()
    assert after["access"]["level"] == "full" and after["record"] is not None
    assert after["access"]["break_glass"]["id"] == requested.json()["id"]
    opened = AuditEvent.objects.filter(action="patients.chart.opened").order_by("-ts").first()
    assert opened is not None
    assert opened.severity == "high" and opened.detail["break_glass_id"] == requested.json()["id"]
    assert (
        client.post(
            f"{url}break-glass/", {"reason": "emergency", "justification": "x"}, format="json"
        ).status_code
        == 400
    )
    ended = client.post(f"/api/v1/access/break-glass/{requested.json()['id']}/end/")
    assert ended.status_code == 200 and ended.json()["ended_at"]
    assert client.get(f"{url}chart/").json()["record"] is None


def test_billing_purpose_is_refused_the_clinical_record(api_as, staff, facility, patient):
    client = api_as(facility=facility, user=staff("clinical_officer"))
    response = client.get(f"/api/v1/patients/{patient.pk}/chart/", {"purpose": "billing"})
    assert response.status_code == 403
    assert response.json()["code"] == "chart_access_insufficient"
    assert response.json()["access_level"] == "demographics"


def test_review_queue_api(api_as, staff, facility, patient):
    clinician = staff("clinical_officer")
    grant = breakglass.request_access(
        user=clinician, patient=patient, reason="emergency", justification=REASON
    )
    supt = api_as(facility=facility, user=staff("medical_superintendent"))
    queue = supt.get("/api/v1/access/break-glass/", {"review_status": "pending"}).json()["results"]
    assert [row["id"] for row in queue] == [str(grant.pk)]
    assert queue[0]["justification"] == REASON and queue[0]["user_name"]
    assert supt.get(f"/api/v1/access/break-glass/{grant.pk}/").status_code == 200
    reviewed = supt.post(
        f"/api/v1/access/break-glass/{grant.pk}/review/", {"outcome": "justified"}, format="json"
    )
    assert reviewed.json()["review_status"] == "justified"
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {
        "access.breakglass.queue_viewed",
        "access.breakglass.viewed",
        "access.breakglass.justified",
    } <= actions
    nurse = api_as(facility=facility, user=staff("nurse"))
    assert nurse.get("/api/v1/access/break-glass/").status_code == 403
    assert nurse.post(f"/api/v1/access/break-glass/{grant.pk}/end/").status_code == 404
    assert BreakGlassGrant.objects.get(pk=grant.pk).ended_at is None


def test_role_levels_are_capped_by_the_permissions_the_user_holds(
    api_as, make_user, grant, patient
):
    # A misconfigured custom role promising "sensitive" without any clinical permission.
    Role.objects.create(
        code="careless", name="Careless", chart_baseline="summary", chart_care_team="sensitive"
    )
    user = make_user()
    grant(user, "careless", patient.facility)
    assert chart.check_chart_access(user, patient) == C.DEMOGRAPHICS
    on_team(patient, user)
    assert chart.check_chart_access(user, patient) == C.DEMOGRAPHICS
    assert care_team.is_member(None, patient) is False


def test_the_superintendent_on_the_care_team_sees_sensitive_items(staff, patient):
    supt = staff("medical_superintendent")
    assert not chart.decide(supt, patient).sensitive
    on_team(patient, supt)
    assert chart.decide(supt, patient).sensitive
