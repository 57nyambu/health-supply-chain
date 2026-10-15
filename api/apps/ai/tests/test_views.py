import io
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image
from rest_framework.test import APIClient

from apps.access.authentication import issue_key
from apps.access.models import ApiClient, Role
from apps.ai import views
from apps.ai.gemma_client import GemmaClientError
from apps.facilities.tests.factories import FacilityFactory
from apps.facility_ops.models import FacilityAlert, FacilityDailyStats
from apps.warehouses.tests.factories import InventoryFactory, ProductFactory, WarehouseFactory

pytestmark = pytest.mark.django_db


def png_upload():
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return SimpleUploadedFile("stock-card.png", buffer.getvalue(), content_type="image/png")


class FakeGemma:
    def __init__(self, model=None):
        pass

    def generate_text(self, prompt):
        return "Move stock from the main store."

    def generate_vision_json(self, image, prompt):
        raise GemmaClientError("offline")


@pytest.fixture
def setup(facility):
    store = WarehouseFactory.create(branch=facility.branch)
    second = WarehouseFactory.create(branch=facility.branch)
    product = ProductFactory.create(reorder_level=20)
    InventoryFactory.create(product=product, warehouse=store, quantity=2)
    InventoryFactory.create(product=product, warehouse=second, quantity=80)
    FacilityDailyStats.objects.create(warehouse=store, date=date(2026, 10, 14), patient_footfall=50)
    return store, second, product


@pytest.mark.req("KE-DPA-07")
def test_ai_endpoints_are_off_by_default(api_as, facility, setup):
    client = api_as("store_keeper", facility=facility)
    store, _second, product = setup
    for method, url in [
        ("post", "/api/v1/ai/assistant/"),
        ("post", "/api/v1/ai/ocr-intake/"),
        ("get", f"/api/v1/ai/forecast/{store.pk}/{product.pk}/"),
        ("get", "/api/v1/ai/redistribution-suggestions/"),
    ]:
        response = getattr(client, method)(url)
        assert response.status_code == 404
        assert response.json()["code"] == "feature_disabled"


def test_ai_endpoints_when_enabled_stay_in_the_facility(
    api_as, facility, setup, settings, monkeypatch
):
    settings.AI_FEATURES_ENABLED = True
    monkeypatch.setattr(views, "GemmaClient", FakeGemma)
    store, second, product = setup
    other = WarehouseFactory.create(branch=FacilityFactory.create().branch)
    client = api_as("store_keeper", facility=facility)
    answer = client.post(
        "/api/v1/ai/assistant/", {"query": "low stock transfer facility"}, format="json"
    ).json()
    assert answer["answer"] == "Move stock from the main store."
    assert set(answer["tools_called"]) == {
        "get_low_stock_alerts",
        "get_facility_stats",
        "get_transfer_candidates",
    }
    ocr = client.post("/api/v1/ai/ocr-intake/", {"image": png_upload()})
    assert ocr.json()["requires_confirmation"] is True
    forecast = client.get(f"/api/v1/ai/forecast/{store.pk}/{product.pk}/").json()
    assert forecast["current_stock"] == 2
    assert client.get(f"/api/v1/ai/forecast/{store.pk}/{product.pk}/").json() == forecast  # cached
    assert client.get(f"/api/v1/ai/forecast/{other.pk}/{product.pk}/").status_code == 404
    assert client.get(f"/api/v1/ai/forecast/{second.pk}/999999/").status_code == 404
    suggestions = client.get("/api/v1/ai/redistribution-suggestions/").json()
    assert (
        suggestions[0]["from_warehouse"] == second.pk and suggestions[0]["to_warehouse"] == store.pk
    )


@pytest.fixture
def api_key():
    _client, key = issue_key(
        name="county-dashboard", role=Role.objects.get(code="public_api_client")
    )
    return key


def test_public_api_needs_a_valid_key(setup):
    store = setup[0]
    FacilityAlert.objects.create(
        warehouse=store, alert_type="understaffed", message="Short", severity="high"
    )
    anonymous = APIClient()
    assert anonymous.get("/api/v1/public/facilities/").status_code in (401, 403)
    bad = APIClient(HTTP_X_API_KEY="deadbeef.not-the-key")
    assert bad.get("/api/v1/public/facilities/").status_code == 401


def test_public_api_with_a_key(setup, api_key):
    store = setup[0]
    FacilityAlert.objects.create(
        warehouse=store, alert_type="understaffed", message="Short", severity="high"
    )
    client = APIClient(HTTP_X_API_KEY=api_key)
    assert {row["id"] for row in client.get("/api/v1/public/facilities/").json()} >= {store.pk}
    assert client.get("/api/v1/public/alerts/").json()[0]["source"] in {
        "facility_alert",
        "inventory_alert",
    }
    assert client.get(f"/api/v1/public/facility-stats/{store.pk}/").json()["days_observed"] == 1
    assert client.get("/api/v1/public/facility-stats/999999/").status_code == 404
    assert ApiClient.objects.get().last_used_at is not None


def test_api_key_principal_cannot_use_staff_endpoints(setup, api_key):
    client = APIClient(HTTP_X_API_KEY=api_key)
    assert client.get("/api/v1/warehouses/warehouses/").status_code == 403


def test_api_key_ip_allowlist_and_deactivation(setup):
    role = Role.objects.get(code="public_api_client")
    _c, key = issue_key(name="locked", role=role, allowed_ips=["10.9.9.9"])
    assert APIClient(HTTP_X_API_KEY=key).get("/api/v1/public/facilities/").status_code == 401
    ApiClient.objects.filter(name="locked").update(allowed_ips=[], active=False)
    assert APIClient(HTTP_X_API_KEY=key).get("/api/v1/public/facilities/").status_code == 401


def test_staff_roles_cannot_get_api_keys():
    with pytest.raises(ValueError, match="service-account"):
        issue_key(name="x", role=Role.objects.get(code="cashier"))


def test_create_api_client_command(capsys):
    call_command("create_api_client", "--name", "integrator")
    assert "shown once" in capsys.readouterr().out
    assert ApiClient.objects.filter(name="integrator").exists()
    with pytest.raises(Exception, match="service-account"):
        call_command("create_api_client", "--name", "x", "--role", "cashier")
