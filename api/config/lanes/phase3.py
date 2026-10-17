"""Phase 3 lane registrations — insurance (SHA via HIE, SMART, Slade360), banks, cards,
eTIMS, hardening and go-live readiness.

Edited only by the Phase 3 lane (docs/agent/lanes/GUIDE-PHASE-3.md). Add, never reorder;
the integrator folds this into the shared files at `phase-3-complete`.
"""

from typing import Any

# Django apps this lane creates, e.g. "apps.insurance".
INSTALLED_APPS: list[str] = []

# (URL prefix, urls module), e.g. ("api/v1/insurance/", "apps.insurance.api.urls").
URLS: list[tuple[str, str]] = []

# Seed modules exposing run(command), run after the Phase 1 and Phase 2 steps.
SEED_STEPS: list[str] = []

# Celery beat entries, keyed by a name starting "p3-".
CELERY_BEAT_SCHEDULE: dict[str, dict[str, Any]] = {}

# Extra permission codes per existing role code, e.g. {"claims_officer": ("insurance.x.y",)}.
ROLE_GRANTS: dict[str, tuple[str, ...]] = {}


def settings(env: Any) -> dict[str, Any]:
    """Settings this lane adds, read from the environment (document each in .env.example
    and docs/operations/ENV.md, Phase 3 lane sections), e.g. {"SHA_MODE": env(...)}."""
    return {}
