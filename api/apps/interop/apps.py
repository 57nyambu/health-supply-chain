import logging

from django.apps import AppConfig


class InteropConfig(AppConfig):
    """FHIR mapping and the national HIE client (DESIGN §15). Mappers only: no models."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.interop"
    label = "interop"

    def ready(self) -> None:
        # httpx logs every request line (URL with query string) at INFO; HIE URLs carry
        # identification numbers and, on reject, a consent token. Keep them out of logs.
        # (Requested from the integrator: set this in LOGGING — PROGRESS-PHASE-3.)
        for name in ("httpx", "httpcore"):
            logging.getLogger(name).setLevel(logging.WARNING)
