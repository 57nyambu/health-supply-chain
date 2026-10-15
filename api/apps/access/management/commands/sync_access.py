from typing import Any

from django.core.management.base import BaseCommand

from apps.access.services import sync_access


class Command(BaseCommand):
    help = "Sync the code-defined permission catalogue and system roles to the database."

    def handle(self, *args: Any, **options: Any) -> None:
        result = sync_access()
        self.stdout.write(
            f"permissions created {result.permissions_created}, "
            f"deactivated {result.permissions_deactivated}; roles created {result.roles_created}"
        )
