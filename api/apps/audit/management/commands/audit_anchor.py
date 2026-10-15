from typing import Any

from django.core.management.base import BaseCommand

from apps.audit.services import anchor_finished_chains


class Command(BaseCommand):
    help = "Anchor every finished (previous-day) audit chain in the database and the anchor file."

    def handle(self, *args: Any, **options: Any) -> None:
        anchors = anchor_finished_chains()
        self.stdout.write(f"audit_anchor: {len(anchors)} chain(s) anchored")
