"""Phase 3 lane registrations — insurance (SHA via HIE, SMART, Slade360), banks, cards,
eTIMS, hardening and go-live readiness.

Edited only by the Phase 3 lane (docs/agent/lanes/GUIDE-PHASE-3.md). Add, never reorder;
the integrator folds this into the shared files at `phase-3-complete`.
"""

from typing import Any

# Django apps this lane creates, e.g. "apps.insurance".
INSTALLED_APPS: list[str] = [
    "apps.interop",
    "apps.banking",
]

# (URL prefix, urls module), e.g. ("api/v1/insurance/", "apps.insurance.api.urls").
URLS: list[tuple[str, str]] = [
    ("api/v1/interop/", "apps.interop.api.urls"),
]

# Seed modules exposing run(command), run after the Phase 1 and Phase 2 steps.
SEED_STEPS: list[str] = [
    "apps.insurance.seed_phase3",
]

# Celery beat entries, keyed by a name starting "p3-".
CELERY_BEAT_SCHEDULE: dict[str, dict[str, Any]] = {}

# Extra permission codes per existing role code, e.g. {"claims_officer": ("insurance.x.y",)}.
ROLE_GRANTS: dict[str, tuple[str, ...]] = {}


def settings(env: Any) -> dict[str, Any]:
    """Settings this lane adds, read from the environment (document each in .env.example
    and docs/operations/ENV.md, Phase 3 lane sections), e.g. {"SHA_MODE": env(...)}."""
    return {
        # --- SHA through the national HIE (INSURANCE.md §3; ADR-072) ---
        "SHA_MODE": env("SHA_MODE", default="fake"),
        "SHA_TRANSPORT": env("SHA_TRANSPORT", default="hie"),
        "SHA_BASE_URL": env("SHA_BASE_URL", default=""),
        "SHA_CLIENT_ID": env("SHA_CLIENT_ID", default=""),
        "SHA_CLIENT_SECRET": env("SHA_CLIENT_SECRET", default=""),
        "SHA_FACILITY_ID": env("SHA_FACILITY_ID", default=""),
        "SHA_FACILITY_ID_TYPE": env("SHA_FACILITY_ID_TYPE", default="fr-code"),
        "SHA_CREDENTIAL_SCOPE": env("SHA_CREDENTIAL_SCOPE", default="facility"),
        "SHA_CALLBACK_USER": env("SHA_CALLBACK_USER", default=""),
        "SHA_CALLBACK_PASSWORD": env("SHA_CALLBACK_PASSWORD", default=""),
        "SHA_CALLBACK_ALLOWED_IPS": env.list("SHA_CALLBACK_ALLOWED_IPS", default=[]),
        # --- Private insurance switches (INSURANCE.md §5-6; ADR-010) ---
        "SMART_MODE": env("SMART_MODE", default="fake"),
        "SLADE360_MODE": env("SLADE360_MODE", default="fake"),
        # --- Banks and cards (PAYMENTS.md §4-6; ADR-011, ADR-075) ---
        "JENGA_MODE": env("JENGA_MODE", default="fake"),
        "JENGA_BASE_URL": env("JENGA_BASE_URL", default=""),
        "JENGA_MERCHANT_CODE": env("JENGA_MERCHANT_CODE", default=""),
        "JENGA_API_KEY": env("JENGA_API_KEY", default=""),
        "JENGA_CONSUMER_SECRET": env("JENGA_CONSUMER_SECRET", default=""),
        "JENGA_PRIVATE_KEY_PATH": env("JENGA_PRIVATE_KEY_PATH", default=""),
        "JENGA_ACCOUNT_NUMBER": env("JENGA_ACCOUNT_NUMBER", default=""),
        "JENGA_IPN_TOKEN": env("JENGA_IPN_TOKEN", default=""),
        "JENGA_IPN_USER": env("JENGA_IPN_USER", default=""),
        "JENGA_IPN_PASSWORD": env("JENGA_IPN_PASSWORD", default=""),
        "BUNI_MODE": env("BUNI_MODE", default="fake"),
        "BUNI_BASE_URL": env("BUNI_BASE_URL", default=""),
        "BUNI_CONSUMER_KEY": env("BUNI_CONSUMER_KEY", default=""),
        "BUNI_CONSUMER_SECRET": env("BUNI_CONSUMER_SECRET", default=""),
        "BUNI_ACCOUNT_NUMBER": env("BUNI_ACCOUNT_NUMBER", default=""),
        "BUNI_TILL_OR_PAYBILL": env("BUNI_TILL_OR_PAYBILL", default=""),
        "BUNI_IPN_PUBLIC_KEY_PATH": env("BUNI_IPN_PUBLIC_KEY_PATH", default=""),
        "BUNI_IPN_ALLOWED_IPS": env.list("BUNI_IPN_ALLOWED_IPS", default=[]),
        "BUNI_IPN_TOKEN": env("BUNI_IPN_TOKEN", default=""),
        "PESAPAL_MODE": env("PESAPAL_MODE", default="fake"),
        "PESAPAL_BASE_URL": env("PESAPAL_BASE_URL", default=""),
        "PESAPAL_CONSUMER_KEY": env("PESAPAL_CONSUMER_KEY", default=""),
        "PESAPAL_CONSUMER_SECRET": env("PESAPAL_CONSUMER_SECRET", default=""),
        "PESAPAL_IPN_ID": env("PESAPAL_IPN_ID", default=""),
        "PESAPAL_IPN_TOKEN": env("PESAPAL_IPN_TOKEN", default=""),
    }
