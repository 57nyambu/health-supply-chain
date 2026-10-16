"""Create a fresh synthetic user for one end-to-end test run (dev and test only).

    python manage.py e2e_user --role receptionist [--role nurse] [--name ward-sister]

Prints the new e-mail address. The password is SEED_PASSWORD; roles are granted at the
synthetic seed facility (run `make seed` first); clinical roles get a synthetic licence.
"""

import json
import secrets
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from apps.access.models import Role, RoleAssignment
from apps.accounts.models import ProfessionalLicence, User
from apps.accounts.seed import DOMAIN
from apps.facilities import seed as facility_seed


class Command(BaseCommand):
    help = (
        "Create a fresh synthetic user with the given roles for an end-to-end test (dev/test only)."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--role", action="append", required=True, help="role code; repeatable")
        parser.add_argument("--name", default="e2e", help="label used in the e-mail address")

    def handle(self, *args: Any, **options: Any) -> None:
        if settings.DJANGO_ENV not in ("dev", "test"):
            raise CommandError("e2e_user runs only with DJANGO_ENV=dev or test.")
        if not settings.SEED_PASSWORD:
            raise CommandError("Set SEED_PASSWORD first.")
        roles = list(Role.objects.filter(code__in=options["role"], active=True))
        if len(roles) != len(set(options["role"])):
            raise CommandError("Unknown role code.")
        site = facility_seed.facility()
        email = f"{options['name']}-{secrets.token_hex(4)}@{DOMAIN}"
        user = User.objects.create_user(
            email=email,
            password=settings.SEED_PASSWORD,
            first_name="E2E",
            last_name=options["name"].replace("-", " ").title(),
            is_approved=True,
        )
        today = timezone.localdate()
        for role in roles:
            RoleAssignment.objects.create(
                user=user,
                role=role,
                facility=site,
                status=RoleAssignment.Status.ACTIVE,
                valid_from=timezone.now() - timedelta(minutes=1),
                reason="End-to-end test user",
            )
            for regulator in role.licence_regulators[:1]:
                ProfessionalLicence.objects.create(
                    user=user,
                    regulator=regulator,
                    registration_number=f"TEST-{secrets.token_hex(4).upper()}",
                    valid_to=today.replace(year=today.year + 1),
                )
        self.stdout.write(json.dumps({"email": email, "id": user.pk}))
