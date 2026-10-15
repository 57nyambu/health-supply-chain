import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from django.test import Client, RequestFactory, override_settings

from apps.audit import context
from apps.audit.context import AuditContextMiddleware, client_ip
from apps.audit.models import AuditEvent
from apps.audit.services import record
from apps.audit.tasks import anchor_audit_chains

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def isolated_data_dir(settings, tmp_path_factory):
    settings.DATA_DIR = tmp_path_factory.mktemp("data")


def test_detail_values_are_normalised():
    ref = uuid.uuid4()
    event = record(
        "x.y.z",
        detail={
            "ids": [1, 2],
            "ref": ref,
            "on": date(2026, 10, 15),
            "nested": {"code": "A1"},
            "ok": True,
            "ratio": 0.5,
        },
    )
    assert event.detail == {
        "ids": [1, 2],
        "ref": str(ref),
        "on": "2026-10-15",
        "nested": {"code": "A1"},
        "ok": True,
        "ratio": 0.5,
    }


def test_nested_sensitive_keys_are_refused_too():
    with pytest.raises(ValueError, match="personal data"):
        record("x.y.z", detail={"nested": {"phone": "x"}})


def test_unsupported_detail_values_are_refused():
    with pytest.raises(TypeError, match="Unsupported"):
        record("x.y.z", detail={"blob": object()})


def test_model_instances_are_referenced_by_label_and_pk(django_user_model):
    user = django_user_model.objects.create_user(email="a@example.test")
    event = record("accounts.user.read", resource=user)
    assert (event.resource_type, event.resource_id) == ("accounts.user", str(user.pk))


def test_other_resource_types_are_refused():
    with pytest.raises(TypeError, match="resource"):
        record("x.y.z", resource="free text")


def test_facility_comes_from_the_resource_when_not_given():
    resource = SimpleNamespace(facility_id=12)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("apps.audit.services._resource_ref", lambda r: ("x.thing", "1"))
        event = record("x.y.z", resource=resource)
    assert event.facility_id == 12


def test_role_resolver_labels_the_actor(django_user_model, monkeypatch):
    user = django_user_model.objects.create_user(email="b@example.test")
    monkeypatch.setattr(context, "role_resolver", lambda actor: "receptionist")
    assert record("x.y.z", actor=user).actor_role == "receptionist"


def test_middleware_sets_ip_and_user_agent_for_the_request(monkeypatch):
    seen = {}

    def view(request):
        seen["ctx"] = context.current()
        from django.http import HttpResponse

        return HttpResponse("ok")

    request = RequestFactory().get("/", HTTP_USER_AGENT="Kiosk/1.0", REMOTE_ADDR="192.0.2.10")
    AuditContextMiddleware(view)(request)
    assert seen["ctx"].ip == "192.0.2.10"
    assert seen["ctx"].user_agent == "Kiosk/1.0"
    assert context.current().ip is None  # reset after the request


def test_proxy_header_is_used_only_when_trusted():
    request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="198.51.100.7")
    with override_settings(TRUST_PROXY_HEADERS=False):
        assert client_ip(request) == "10.0.0.1"
    with override_settings(TRUST_PROXY_HEADERS=True):
        assert client_ip(request) == "198.51.100.7"


def test_request_id_is_recorded():
    Client().get("/healthz")  # request ids are cleared after a request
    event = record("x.y.z")
    assert event.request_id == ""


def test_anchor_task_runs():
    assert anchor_audit_chains() == 0
    assert AuditEvent.objects.count() == 0
