import uuid

import pytest

from apps.audit.models import AuditEvent
from apps.audit.services import record
from apps.facilities.tests.factories import FacilityFactory

pytestmark = [pytest.mark.django_db, pytest.mark.req("KE-DPA-06")]
URL = "/api/v1/audit/events/"


@pytest.fixture(autouse=True)
def isolated_data_dir(settings, tmp_path_factory):
    settings.DATA_DIR = tmp_path_factory.mktemp("data")


def test_dpo_and_auditor_can_read_others_cannot(api_as, facility):
    assert api_as("dpo", facility=facility).get(URL).status_code == 200
    assert api_as("auditor", facility=facility).get(URL).status_code == 200
    assert api_as("facility_admin", facility=facility).get(URL).status_code == 403
    assert api_as("medical_superintendent", facility=facility).get(URL).status_code == 403


def test_viewer_shows_own_facility_and_system_events(api_as, facility):
    record("x.mine", facility=facility)
    record("x.system")
    record("x.elsewhere", facility=FacilityFactory.create())
    dpo = api_as("dpo", facility=facility)
    actions = {row["action"] for row in dpo.get(URL).json()["results"]}
    assert {"x.mine", "x.system"} <= actions
    assert "x.elsewhere" not in actions


def test_filters(api_as, facility, make_user):
    clerk = make_user()
    patient = uuid.uuid4()
    record("patients.chart.opened", actor=clerk, patient=patient, facility=facility)
    record("patients.chart.opened", facility=facility)
    record("auth.login.failed", outcome="denied", facility=facility)
    dpo = api_as("dpo", facility=facility)

    def actions(**params):
        return [row["action"] for row in dpo.get(URL, params).json()["results"]]

    assert actions(actor=clerk.pk) == ["patients.chart.opened"]
    assert actions(patient=str(patient)) == ["patients.chart.opened"]
    assert actions(action="auth.*") == ["auth.login.failed"]
    assert actions(outcome="denied") == ["auth.login.failed"]
    assert len(actions(action="patients.chart.opened")) == 2
    assert dpo.get(URL, {"patient": "not-a-uuid"}).status_code == 400


def test_viewing_the_audit_log_is_audited(api_as, facility):
    target = record("x.thing", facility=facility)
    dpo = api_as("dpo", facility=facility)
    dpo.get(URL, {"action": "x.thing"})
    viewed = AuditEvent.objects.get(action="audit.log.viewed")
    assert viewed.actor_id == dpo.user.pk
    assert viewed.detail == {"filters": {"action": "x.thing"}}
    assert dpo.get(f"{URL}{target.pk}/").json()["action"] == "x.thing"
    assert AuditEvent.objects.filter(action="audit.log.viewed").count() == 2


def test_cursor_pagination_newest_first(api_as, facility):
    for index in range(3):
        record("x.page", facility=facility, detail={"i": index})
    dpo = api_as("dpo", facility=facility)
    page = dpo.get(URL, {"page_size": 2, "action": "x.page"}).json()
    assert [row["detail"]["i"] for row in page["results"]] == [2, 1]
    assert page["next"] is not None
