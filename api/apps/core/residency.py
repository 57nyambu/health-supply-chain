"""Data residency guard (DESIGN §8.3, KE-DHA-06, KE-DPA-07).

Every endpoint that can receive PHI — S3-compatible storage, backup target,
error tracker, log shipper — is checked against RESIDENCY_ALLOWED_HOSTS:

- ``strict``: a non-allowlisted endpoint stops the API from starting;
- ``warn``: the API starts, logs a warning, the integration stays disabled and
  the admin banner lists the violation;
- ``off``: no check (development only; production refuses ``off``).
"""

import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

_violations: dict[str, str] = {}


def host_of(endpoint: str) -> str:
    """Host name of a URL or DSN (``https://key@o1.ingest.example/1`` → ``o1.ingest.example``)."""
    parsed = urlsplit(endpoint if "://" in endpoint else f"//{endpoint}")
    return (parsed.hostname or "").lower()


def host_allowed(host: str) -> bool:
    """Exact match, or a suffix entry starting with a dot (``.example.ke``)."""
    host = host.lower()
    for entry in settings.RESIDENCY_ALLOWED_HOSTS:
        entry = entry.strip().lower()
        if not entry:
            continue
        if host == entry or (entry.startswith(".") and host.endswith(entry)):
            return True
    return False


def check_endpoint(endpoint: str, purpose: str) -> bool:
    """True when PHI may be sent to ``endpoint``; raises in strict mode when it may not."""
    mode = settings.DATA_RESIDENCY_MODE
    if mode == "off":
        return True
    host = host_of(endpoint)
    if host and host_allowed(host):
        _violations.pop(purpose, None)
        return True
    message = f"{purpose} endpoint host {host or '(none)'} is not in RESIDENCY_ALLOWED_HOSTS"
    if mode == "strict":
        raise ImproperlyConfigured(f"Residency guard (strict): {message}.")
    _violations[purpose] = message
    logger.warning("Residency guard (warn): %s; integration disabled.", message)
    return False


def violations() -> dict[str, str]:
    """Current warn-mode violations, for the admin banner."""
    return dict(_violations)
