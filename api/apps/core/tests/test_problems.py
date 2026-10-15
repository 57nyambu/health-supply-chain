import json

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.urls("apps.core.tests.probe_urls")

PATIENT_NAME = "Wanjiku Kamau Njeri"


@pytest.fixture
def client():
    return APIClient(raise_request_exception=False)


def test_validation_error_is_problem_json_without_echoing_input(client):
    response = client.post(
        "/api/test/validation/",
        {"full_name": PATIENT_NAME, "category": PATIENT_NAME, "when": PATIENT_NAME},
        format="json",
    )
    assert response.status_code == 400
    assert response["Content-Type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "urn:afyasync:problem:validation_error"
    assert body["code"] == "validation_error"
    assert body["status"] == 400
    assert body["request_id"] == response["X-Request-ID"]
    assert {e["field"] for e in body["errors"]} == {"full_name", "category", "when"}
    assert {e["code"] for e in body["errors"]} == {"max_length", "invalid_choice", "invalid"}
    raw = response.content.decode().lower()
    for part in PATIENT_NAME.lower().split():
        assert part not in raw


def test_message_echoing_submitted_value_is_replaced(client):
    response = client.post(
        "/api/test/validation/",
        {"full_name": "abc", "category": "Kamau", "when": "2026-01-01"},
        format="json",
    )
    errors = {e["field"]: e for e in response.json()["errors"]}
    assert errors["category"]["message"] == "Not a valid choice."
    assert "kamau" not in response.content.decode().lower()


def test_missing_fields_are_listed(client):
    body = client.post("/api/test/validation/", {}, format="json").json()
    assert sorted(e["field"] for e in body["errors"]) == ["category", "full_name", "when"]
    assert {e["code"] for e in body["errors"]} == {"required"}


def test_malformed_json_is_a_parse_error(client):
    response = client.post(
        "/api/test/validation/", data="{not json", content_type="application/json"
    )
    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "parse_error"
    assert body["detail"] == "Malformed request body."


def test_unhandled_exception_is_generic_500(client):
    response = client.get("/api/test/crash/")
    assert response.status_code == 500
    assert response["Content-Type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "server_error"
    assert "boom" not in json.dumps(body)
    assert body["request_id"] == response["X-Request-ID"]


def test_unknown_api_path_is_problem_json(client):
    response = client.get("/api/v1/does-not-exist/")
    assert response.status_code == 404
    assert response["Content-Type"] == "application/problem+json"
    assert response.json()["code"] == "not_found"


def test_not_authenticated_is_problem_json(client):
    response = client.get("/api/v1/analytics/inventory-alerts/")
    assert response.status_code in (401, 403)
    assert response["Content-Type"] == "application/problem+json"
    assert response.json()["code"] in ("not_authenticated", "permission_denied")


def test_wellformed_incoming_request_id_is_kept(client):
    response = client.get("/api/v1/does-not-exist/", HTTP_X_REQUEST_ID="abc12345-trace")
    assert response["X-Request-ID"] == "abc12345-trace"
    assert response.json()["request_id"] == "abc12345-trace"


def test_malformed_incoming_request_id_is_replaced(client):
    response = client.get("/api/v1/does-not-exist/", HTTP_X_REQUEST_ID="<script>")
    assert response["X-Request-ID"] != "<script>"
    assert len(response["X-Request-ID"]) == 32
