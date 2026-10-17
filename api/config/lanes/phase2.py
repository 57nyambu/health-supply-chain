"""Phase 2 lane registrations — clinical journey, billing core, cash and M-Pesa.

Edited only by the Phase 2 lane (docs/agent/lanes/GUIDE-PHASE-2.md). Add, never reorder;
the integrator folds this into the shared files at `phase-2-complete`.
"""

from typing import Any

from celery.schedules import crontab

# Django apps this lane creates, e.g. "apps.visits".
INSTALLED_APPS: list[str] = [
    "apps.billing",
    "apps.visits",
]

# (URL prefix, urls module), e.g. ("api/v1/visits/", "apps.visits.api.urls").
URLS: list[tuple[str, str]] = [
    ("api/v1/billing/", "apps.billing.api.urls"),
    ("api/v1/visits/", "apps.visits.api.urls"),
]

# Seed modules exposing run(command), run after the Phase 1 steps, e.g. "apps.billing.seed".
SEED_STEPS: list[str] = [
    "apps.billing.seed",
    "apps.visits.seed",
]

# Celery beat entries, keyed by a name starting "p2-".
CELERY_BEAT_SCHEDULE: dict[str, dict[str, Any]] = {
    "p2-flag-idle-tickets": {
        "task": "apps.visits.tasks.flag_idle_tickets",
        "schedule": crontab(minute="*/5"),
    },
}

# Extra permission codes per existing role code, e.g. {"cashier": ("payments.shift.own",)}.
_CATALOGUE = ("billing.service.read",)
_CLINICAL = (
    "clinical_officer",
    "medical_officer",
    "specialist",
    "intern",
    "medical_superintendent",
)
_SERVICE: tuple[str, ...] = (
    "triage_nurse",
    "nurse",
    "lab_technologist",
    "lab_supervisor",
    "radiographer",
)
_SERVICE += ("radiologist", "pharmacist", "pharm_tech")
_FRONT = ("receptionist", "cashier", "billing_officer", "claims_officer", "finance_manager")

_GRANTS: dict[str, list[str]] = {
    role: list(_CATALOGUE) for role in (*_CLINICAL, *_SERVICE, *_FRONT)
}
# Gate policies: a facility administrator proposes, a second one approves (maker-checker).
_GRANTS.setdefault("facility_admin", []).extend(["visits.gate.manage", "visits.board.manage"])

ROLE_GRANTS: dict[str, tuple[str, ...]] = {role: tuple(codes) for role, codes in _GRANTS.items()}


def settings(env: Any) -> dict[str, Any]:
    """Settings this lane adds, read from the environment (document each in .env.example
    and docs/operations/ENV.md, Phase 2 lane sections), e.g. {"MPESA_MODE": env(...)}."""
    return {}
