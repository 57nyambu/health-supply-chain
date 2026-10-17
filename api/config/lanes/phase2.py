"""Phase 2 lane registrations — clinical journey, billing core, cash and M-Pesa.

Edited only by the Phase 2 lane (docs/agent/lanes/GUIDE-PHASE-2.md). Add, never reorder;
the integrator folds this into the shared files at `phase-2-complete`.
"""

from typing import Any

# Django apps this lane creates, e.g. "apps.visits".
INSTALLED_APPS: list[str] = []

# (URL prefix, urls module), e.g. ("api/v1/visits/", "apps.visits.api.urls").
URLS: list[tuple[str, str]] = []

# Seed modules exposing run(command), run after the Phase 1 steps, e.g. "apps.billing.seed".
SEED_STEPS: list[str] = []

# Celery beat entries, keyed by a name starting "p2-".
CELERY_BEAT_SCHEDULE: dict[str, dict[str, Any]] = {}

# Extra permission codes per existing role code, e.g. {"cashier": ("payments.shift.own",)}.
ROLE_GRANTS: dict[str, tuple[str, ...]] = {}


def settings(env: Any) -> dict[str, Any]:
    """Settings this lane adds, read from the environment (document each in .env.example
    and docs/operations/ENV.md, Phase 2 lane sections), e.g. {"MPESA_MODE": env(...)}."""
    return {}
