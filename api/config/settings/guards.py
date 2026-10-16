"""Production safety checks: the API refuses to start on unsafe configuration.

prod.py calls check_production_settings(globals()) at import time, so a
misconfigured deployment fails before it serves a single request.
"""

import json
from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ImproperlyConfigured

INSECURE_SECRET_KEYS = {"", "unsafe-dev-secret", "change-me", "changeme", "secret"}
MIN_SECRET_KEY_LENGTH = 50


def _has_keys(raw: str) -> bool:
    """True when raw is a non-empty JSON object of key id -> key material."""
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        return False
    return isinstance(parsed, dict) and bool(parsed) and all(parsed.values())


def production_problems(settings: Mapping[str, Any]) -> list[str]:
    """Return a description of every unsafe production setting (empty when safe)."""
    problems = []
    if settings.get("DEBUG"):
        problems.append("DEBUG must be off in production (DJANGO_DEBUG).")

    secret = settings.get("SECRET_KEY") or ""
    if (
        secret in INSECURE_SECRET_KEYS
        or secret.startswith("django-insecure")
        or len(secret) < MIN_SECRET_KEY_LENGTH
    ):
        problems.append(
            f"DJANGO_SECRET_KEY must be a random value of at least {MIN_SECRET_KEY_LENGTH} characters."
        )

    engine = settings.get("DATABASES", {}).get("default", {}).get("ENGINE", "")
    if "sqlite" in engine:
        problems.append("SQLite is not allowed in production; set DATABASE_URL to PostgreSQL.")

    if not _has_keys(settings.get("FIELD_ENCRYPTION_KEYS", "")):
        problems.append("FIELD_ENCRYPTION_KEYS must be a non-empty JSON object of key id -> key.")
    if not settings.get("FIELD_BLIND_INDEX_KEY"):
        problems.append("FIELD_BLIND_INDEX_KEY must be set.")
    if not _has_keys(settings.get("STORAGE_MASTER_KEYS", "")):
        problems.append("STORAGE_MASTER_KEYS must be a non-empty JSON object of key id -> key.")

    if settings.get("MFA_DEV_BYPASS"):
        problems.append("MFA_DEV_BYPASS must be off in production.")
    if not settings.get("STORAGE_ENCRYPTION", True):
        problems.append("STORAGE_ENCRYPTION must be on in production.")
    backend = settings.get("STORAGE_BACKEND", "local")
    if backend not in ("local", "s3"):
        problems.append("STORAGE_BACKEND must be 'local' or 's3'.")
    if backend == "s3" and not (settings.get("S3_BUCKET") and settings.get("S3_ENDPOINT_URL")):
        problems.append("STORAGE_BACKEND=s3 needs S3_BUCKET and S3_ENDPOINT_URL.")

    if settings.get("DATA_RESIDENCY_MODE") not in ("strict", "warn"):
        problems.append(
            "DATA_RESIDENCY_MODE must be 'strict' (or 'warn') in production, never 'off'."
        )

    if not settings.get("ALLOWED_HOSTS") or "*" in settings.get("ALLOWED_HOSTS", []):
        problems.append("DJANGO_ALLOWED_HOSTS must list the real host names (no '*').")
    return problems


def check_production_settings(settings: Mapping[str, Any]) -> None:
    problems = production_problems(settings)
    if problems:
        raise ImproperlyConfigured(
            "Refusing to start with unsafe production settings:\n- " + "\n- ".join(problems)
        )
