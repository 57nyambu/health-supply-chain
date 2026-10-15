from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.access.authentication import issue_key
from apps.access.models import Role
from apps.audit.services import record


class Command(BaseCommand):
    help = "Create a service-account API client and print its key once."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--name", required=True)
        parser.add_argument("--role", default="public_api_client")
        parser.add_argument("--allow-ip", action="append", default=[], dest="allowed_ips")

    def handle(self, *args: Any, **options: Any) -> None:
        role = Role.objects.filter(code=options["role"], service_account=True).first()
        if role is None:
            raise CommandError(f"{options['role']!r} is not a service-account role.")
        client, key = issue_key(name=options["name"], role=role, allowed_ips=options["allowed_ips"])
        record("access.api_client.created", None, client, detail={"role": role.code})
        self.stdout.write(f"API client {client.name} created. Key (shown once): {key}")
