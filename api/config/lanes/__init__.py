"""Registrations of the parallel build lanes (ADR-024, docs/agent/lanes/README.md).

Phase 2 and Phase 3 are built at the same time on their own branches. Each lane registers
its Django apps, URL mounts, seed steps, beat jobs, settings and extra role grants in its
own module here, so neither lane edits the shared lists in settings, urls.py, the seed
command or roles.py — and merging the lanes never conflicts on them.

    phase2.py — edited only by the Phase 2 lane
    phase3.py — edited only by the Phase 3 lane

The integrator folds both into the shared files when the phases are tagged.
"""

from types import ModuleType
from typing import Any

from config.lanes import phase2, phase3

LANES: tuple[ModuleType, ...] = (phase2, phase3)


def installed_apps() -> list[str]:
    return [app for lane in LANES for app in lane.INSTALLED_APPS]


def url_mounts() -> list[tuple[str, str]]:
    return [mount for lane in LANES for mount in lane.URLS]


def seed_steps() -> list[str]:
    return [step for lane in LANES for step in lane.SEED_STEPS]


def beat_schedule() -> dict[str, dict[str, Any]]:
    schedule: dict[str, dict[str, Any]] = {}
    for lane in LANES:
        schedule.update(lane.CELERY_BEAT_SCHEDULE)
    return schedule


def settings(env: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for lane in LANES:
        values.update(lane.settings(env))
    return values


def role_grants() -> dict[str, tuple[str, ...]]:
    grants: dict[str, tuple[str, ...]] = {}
    for lane in LANES:
        for role, codes in lane.ROLE_GRANTS.items():
            grants[role] = grants.get(role, ()) + tuple(codes)
    return grants
