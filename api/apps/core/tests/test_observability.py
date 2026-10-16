import io
import json
import logging

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, RequestFactory

from apps.core import error_tracking, health, residency
from apps.core.logs import JsonFormatter, PhiScrubbingFilter, RequestIdFilter
from apps.core.request_id import _current_request_id
from apps.core.scrubbing import scrub_text, scrub_value

PHONE = "+254712345678"
NATIONAL_ID = "00012345"
EMAIL = "wanjiku.kamau@example.com"
NAME = "Wanjiku Kamau"


# --- health -------------------------------------------------------------------------------------


def test_healthz_is_ok_without_touching_the_database():
    response = Client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "no-cache" in response["Cache-Control"]


@pytest.mark.django_db
def test_readyz_reports_each_component(monkeypatch, settings, tmp_path_factory):
    settings.DATA_DIR = tmp_path_factory.mktemp("data")
    monkeypatch.setitem(health.CHECKS, "redis", lambda: None)
    response = Client().get("/readyz")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "ok", "storage": "ok"},
    }


@pytest.mark.django_db
def test_readyz_is_503_when_a_dependency_fails(monkeypatch, settings, tmp_path_factory):
    settings.DATA_DIR = tmp_path_factory.mktemp("data")

    def broken():
        raise ConnectionError("redis down")

    monkeypatch.setitem(health.CHECKS, "redis", broken)
    response = Client().get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "fail"
    assert "redis down" not in response.content.decode()


def test_storage_check_fails_when_data_dir_is_not_writable(settings, tmp_path_factory):
    blocker = tmp_path_factory.mktemp("x") / "file"
    blocker.write_text("not a directory")
    settings.DATA_DIR = blocker
    with pytest.raises(OSError):
        health.check_storage()


def test_redis_check_pings(monkeypatch):
    calls = []

    class FakeRedis:
        def ping(self):
            calls.append("ping")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(
        health.redis.Redis, "from_url", classmethod(lambda cls, url, **kw: FakeRedis())
    )
    health.check_redis()
    assert calls == ["ping", "close"]


# --- scrubbing ---------------------------------------------------------------------------------


@pytest.mark.req("KE-DPA-01")
@pytest.mark.parametrize(
    "value",
    [
        PHONE,
        "0712 345 678",
        "254712345678",
        NATIONAL_ID,
        EMAIL,
        "CR1234567890",
        "99999-26-000123",
        "A1234567",
    ],
)
def test_scrub_text_removes_identifiers(value):
    assert value not in scrub_text(f"patient {value} arrived")


def test_scrub_text_keeps_ordinary_text():
    text = "Visit closed on 2026-10-15 after 42 minutes"
    assert scrub_text(text) == text


def test_scrub_value_redacts_sensitive_keys_recursively():
    data = {
        "first_name": NAME,
        "nested": {"phone": PHONE, "count": 3},
        "items": [{"id_number": NATIONAL_ID}],
    }
    assert scrub_value(data) == {
        "first_name": "[redacted]",
        "nested": {"phone": "[redacted]", "count": 3},
        "items": [{"id_number": "[redacted]"}],
    }


# --- JSON logs ------------------------------------------------------------------------------------


def _capture_logger():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    handler.addFilter(PhiScrubbingFilter())
    logger = logging.getLogger("afyasync.test.capture")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger, stream


@pytest.mark.req("KE-DPA-01")
def test_log_records_are_json_with_request_id_and_no_phi():
    logger, stream = _capture_logger()
    token = _current_request_id.set("req-12345678")
    try:
        logger.info(
            "Registered %s with phone %s",
            NATIONAL_ID,
            PHONE,
            extra={"patient_name": NAME, "facility_id": 7},
        )
    finally:
        _current_request_id.reset(token)
    line = stream.getvalue().strip()
    record = json.loads(line)
    assert record["request_id"] == "req-12345678"
    assert record["level"] == "INFO"
    assert record["facility_id"] == 7
    assert record["patient_name"] == "[redacted]"
    for secret in (NATIONAL_ID, PHONE, "Wanjiku"):
        assert secret not in line


@pytest.mark.req("KE-DPA-01")
def test_logged_requests_keep_method_and_path_but_never_the_query_string():
    """django.request records carry the request; its repr includes the query string."""
    logger, stream = _capture_logger()
    request = RequestFactory().get("/api/v1/patients/search/", {"q": NAME, "phone": PHONE})
    logger.warning("Forbidden: %s", request.path, extra={"status_code": 403, "request": request})
    record = json.loads(stream.getvalue().strip())
    assert record["request"] == "GET /api/v1/patients/search/"
    for secret in ("Wanjiku", PHONE, "q="):
        assert secret not in stream.getvalue()


def test_exception_text_is_scrubbed():
    logger, stream = _capture_logger()
    try:
        raise ValueError(f"duplicate key (phone)=({PHONE})")
    except ValueError:
        logger.exception("insert failed")
    record = json.loads(stream.getvalue().strip())
    assert "ValueError" in record["exception"]
    assert PHONE not in stream.getvalue()


def test_project_logging_uses_the_scrubbing_json_handler(settings):
    handler = settings.LOGGING["handlers"]["console"]
    assert handler["formatter"] == "json"
    assert handler["filters"] == ["request_id", "scrub_phi"]


# --- error tracker + residency -------------------------------------------------------------------


def test_scrub_event_drops_bodies_cookies_headers_and_locals():
    event = {
        "request": {
            "url": f"https://hmis/api/v1/x?phone={PHONE}",
            "data": {"name": NAME},
            "cookies": "s=1",
            "headers": {"Cookie": "s=1"},
            "query_string": f"q={NAME}",
        },
        "user": {"id": 5, "email": EMAIL},
        "exception": {
            "values": [
                {"value": f"bad {PHONE}", "stacktrace": {"frames": [{"vars": {"patient": NAME}}]}}
            ]
        },
        "breadcrumbs": {"values": [{"message": f"sql {NATIONAL_ID}", "data": {"params": [NAME]}}]},
        "extra": {"first_name": NAME},
    }
    scrubbed = error_tracking.scrub_event(event)
    dumped = json.dumps(scrubbed)
    for secret in (PHONE, NAME, EMAIL, NATIONAL_ID, "s=1"):
        assert secret not in dumped
    assert scrubbed["user"] == {"id": 5}
    assert set(scrubbed["request"]) == {"url"}


def test_error_tracker_is_off_without_dsn(settings):
    settings.ERROR_TRACKER_DSN = ""
    assert error_tracking.init_error_tracking() is False


def test_error_tracker_disabled_when_host_not_allowed_in_warn_mode(settings, monkeypatch):
    settings.ERROR_TRACKER_DSN = "https://key@o1.ingest.example.com/1"
    settings.DATA_RESIDENCY_MODE = "warn"
    settings.RESIDENCY_ALLOWED_HOSTS = ["errors.hmis.co.ke"]
    monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: pytest.fail("must not initialise"))
    assert error_tracking.init_error_tracking() is False
    assert "Error tracker" in residency.violations()


def test_error_tracker_refuses_to_start_in_strict_mode(settings):
    settings.ERROR_TRACKER_DSN = "https://key@o1.ingest.example.com/1"
    settings.DATA_RESIDENCY_MODE = "strict"
    settings.RESIDENCY_ALLOWED_HOSTS = []
    with pytest.raises(ImproperlyConfigured, match="Residency guard"):
        error_tracking.init_error_tracking()


def test_error_tracker_enabled_with_scrubbing_when_host_allowed(settings, monkeypatch):
    settings.ERROR_TRACKER_DSN = "https://key@errors.hmis.co.ke/1"
    settings.DATA_RESIDENCY_MODE = "strict"
    settings.RESIDENCY_ALLOWED_HOSTS = [".hmis.co.ke"]
    captured = {}
    monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: captured.update(kwargs))
    assert error_tracking.init_error_tracking() is True
    assert captured["send_default_pii"] is False
    assert captured["max_request_body_size"] == "never"
    assert captured["include_local_variables"] is False
    assert captured["before_send"] is error_tracking.scrub_event


def test_residency_host_matching(settings):
    settings.RESIDENCY_ALLOWED_HOSTS = ["s3.hmis.co.ke", ".backup.co.ke"]
    assert residency.host_of("https://user@s3.hmis.co.ke:9000/bucket") == "s3.hmis.co.ke"
    assert residency.host_allowed("s3.hmis.co.ke")
    assert residency.host_allowed("nbo1.backup.co.ke")
    assert not residency.host_allowed("eu2.contabostorage.com")


def test_residency_off_allows_everything(settings):
    settings.DATA_RESIDENCY_MODE = "off"
    settings.RESIDENCY_ALLOWED_HOSTS = []
    assert residency.check_endpoint("https://eu2.contabostorage.com", "Storage") is True
