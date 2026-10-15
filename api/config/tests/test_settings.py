import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.env import configure_settings_module
from config.settings.guards import check_production_settings, production_problems

API_DIR = Path(__file__).resolve().parents[2]
KEYS = json.dumps({"k1": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="})


def safe_settings(**overrides):
    values = {
        "DEBUG": False,
        "SECRET_KEY": "x" * 64,
        "DATABASES": {"default": {"ENGINE": "django.db.backends.postgresql"}},
        "FIELD_ENCRYPTION_KEYS": KEYS,
        "FIELD_BLIND_INDEX_KEY": "blind-index-key",
        "STORAGE_MASTER_KEYS": KEYS,
        "DATA_RESIDENCY_MODE": "strict",
        "ALLOWED_HOSTS": ["hmis.example.ke"],
    }
    values.update(overrides)
    return values


def test_safe_production_settings_pass():
    assert production_problems(safe_settings()) == []
    check_production_settings(safe_settings())


@pytest.mark.req("KE-DPA-06")
@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"DEBUG": True}, "DEBUG"),
        ({"SECRET_KEY": "unsafe-dev-secret"}, "DJANGO_SECRET_KEY"),
        ({"SECRET_KEY": "django-insecure-" + "x" * 60}, "DJANGO_SECRET_KEY"),
        ({"SECRET_KEY": "short"}, "DJANGO_SECRET_KEY"),
        ({"DATABASES": {"default": {"ENGINE": "django.db.backends.sqlite3"}}}, "SQLite"),
        ({"FIELD_ENCRYPTION_KEYS": ""}, "FIELD_ENCRYPTION_KEYS"),
        ({"FIELD_ENCRYPTION_KEYS": "{}"}, "FIELD_ENCRYPTION_KEYS"),
        ({"FIELD_ENCRYPTION_KEYS": "not json"}, "FIELD_ENCRYPTION_KEYS"),
        ({"FIELD_BLIND_INDEX_KEY": ""}, "FIELD_BLIND_INDEX_KEY"),
        ({"STORAGE_MASTER_KEYS": ""}, "STORAGE_MASTER_KEYS"),
        ({"DATA_RESIDENCY_MODE": "off"}, "DATA_RESIDENCY_MODE"),
        ({"ALLOWED_HOSTS": ["*"]}, "DJANGO_ALLOWED_HOSTS"),
    ],
)
def test_each_production_guard_fires(override, message):
    with pytest.raises(ImproperlyConfigured, match=message):
        check_production_settings(safe_settings(**override))


def _import_prod(extra_env):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "FIELD_", "STORAGE_"))}
    env.pop("DATA_RESIDENCY_MODE", None)
    env.update(extra_env)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
    code = (
        "import django; django.setup(); from django.conf import settings as s; "
        "print(s.SECURE_HSTS_SECONDS, s.SESSION_COOKIE_SECURE, s.SECURE_CONTENT_TYPE_NOSNIFF, "
        "s.SECURE_REFERRER_POLICY, s.DATA_RESIDENCY_MODE)"
    )
    return subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, "-c", code], cwd=API_DIR, env=env, capture_output=True, text=True, check=False
    )


def test_prod_module_refuses_to_start_with_defaults():
    result = _import_prod({})
    assert result.returncode != 0
    assert "Refusing to start with unsafe production settings" in result.stderr


def test_prod_module_starts_with_safe_env_and_sets_security_headers():
    result = _import_prod(
        {
            "DJANGO_SECRET_KEY": "s" * 64,
            "DJANGO_ALLOWED_HOSTS": "hmis.example.ke",
            "FIELD_ENCRYPTION_KEYS": KEYS,
            "FIELD_BLIND_INDEX_KEY": "blind-index-key",
            "STORAGE_MASTER_KEYS": KEYS,
        }
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["31536000", "True", "True", "no-referrer", "strict"]


def test_locale_is_nairobi_with_timezone_support():
    assert settings.TIME_ZONE == "Africa/Nairobi"
    assert settings.USE_TZ is True


def test_unknown_django_env_is_rejected(monkeypatch):
    monkeypatch.setenv("DJANGO_ENV", "staging")
    with pytest.raises(RuntimeError, match="DJANGO_ENV"):
        configure_settings_module(default="dev")


def test_django_env_selects_the_settings_module(monkeypatch):
    monkeypatch.setenv("DJANGO_ENV", "prod")
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE")
    assert configure_settings_module(default="dev") == "config.settings.prod"
