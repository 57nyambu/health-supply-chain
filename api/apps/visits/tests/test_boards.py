"""P2-VIS-03: queue display boards — ticket and room only, device token scoped to the board."""

import pytest
from rest_framework.test import APIClient

from apps.visits import services

pytestmark = pytest.mark.django_db


@pytest.fixture
def board(facility, points, clinician):
    admin = clinician("facility_admin")
    return services.create_board(
        facility=facility, name="Waiting area", service_points=[points["triage"]], actor=admin
    )


@pytest.mark.req("KE-DPA-01")
def test_board_shows_numbers_and_rooms_never_names(board, patient, points, clinician):
    _board, token = board
    clerk = clinician("receptionist")
    services.open_visit(patient=patient, visit_type="opd", actor=clerk)
    services.call_next(points["triage"], actor=clinician("triage_nurse"), room="Room 2")
    device = APIClient()
    response = device.get("/api/v1/visits/board-display/", HTTP_X_BOARD_TOKEN=token)
    assert response.status_code == 200
    body = response.json()
    assert body["now_calling"][0]["room"] == "Room 2"
    text = response.content.decode()
    for value in (patient.given_name, patient.family_name, patient.mrn):
        assert value not in text
    assert set(body["now_calling"][0]) == {"number", "room", "service_point", "status", "called_at"}
    assert response["Cache-Control"] == "no-store"


def test_board_token_opens_nothing_else(board, patient):
    _board, token = board
    device = APIClient()
    assert device.get("/api/v1/visits/", HTTP_X_BOARD_TOKEN=token).status_code in (401, 403)
    assert device.get(f"/api/v1/patients/{patient.pk}/", HTTP_X_BOARD_TOKEN=token).status_code in (
        401,
        403,
    )
    assert (
        device.get("/api/v1/visits/board-display/", HTTP_X_BOARD_TOKEN="bad.token").status_code
        == 401
    )
    assert device.get("/api/v1/visits/board-display/").status_code in (401, 403)


def test_revoked_board_stops_working_and_staff_sessions_cannot_read_it(board, api_for, clinician):
    row, token = board
    nurse = api_for("triage_nurse")
    assert nurse.get("/api/v1/visits/board-display/").status_code in (401, 403)
    services.revoke_board(row, actor=clinician("facility_admin"))
    assert (
        APIClient().get("/api/v1/visits/board-display/", HTTP_X_BOARD_TOKEN=token).status_code
        == 401
    )


def test_admin_creates_board_and_sees_token_once(api_for, points):
    admin = api_for("facility_admin")
    response = admin.post(
        "/api/v1/visits/boards/",
        {"name": "Lab area", "service_points": [points["lab"].pk]},
        format="json",
    )
    assert response.status_code == 201 and "." in response.json()["token"]
    listed = admin.get("/api/v1/visits/boards/").json()
    assert "token" not in listed[0]
    assert api_for("receptionist").get("/api/v1/visits/boards/").status_code == 403
