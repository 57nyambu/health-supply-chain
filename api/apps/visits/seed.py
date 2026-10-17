"""Seed step: queue settings, default payment gates (DESIGN §6.4) and a waiting-room board.

Open visits in several states are seeded later by the clinical steps, once triage and
consultation exist (GUIDE-PHASE-2 synthetic data).
"""

from typing import Any

from django.db import transaction

from apps.facilities import seed as facility_seed
from apps.facilities.models import ServicePoint
from apps.visits import gates, services
from apps.visits.models import QueueBoard


@transaction.atomic
def run(command: Any) -> None:
    site = facility_seed.facility()
    services.queue_settings(site)
    created = gates.seed_defaults(site)
    if not QueueBoard.objects.filter(facility=site, name="OPD waiting area").exists():
        points = list(
            ServicePoint.objects.filter(
                facility=site, kind__in=["triage", "consultation", "lab", "pharmacy", "cashier"]
            )
        )
        # The token is not printed: an administrator issues a new board token in the admin UI.
        services.create_board(
            facility=site, name="OPD waiting area", service_points=points, actor=None
        )
    command.stdout.write(
        f"  visits: queue settings, {created} new gate policies, waiting-area board"
    )
