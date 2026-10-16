"""Seed step: one synthetic user per role at the synthetic facility (IMPLEMENTATION §8).

E-mail addresses are ``<role code>@seed.afyasync.test`` (a reserved test domain); the
password is ``SEED_PASSWORD``. Clinical roles get a synthetic licence the fake Health
Worker Registry recognises. Seed grants skip maker-checker: they are the bootstrap, run
only outside production.
"""

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from apps.access.models import Role, RoleAssignment
from apps.accounts.models import ProfessionalLicence, User
from apps.facilities import seed as facility_seed

DOMAIN = "seed.afyasync.test"


def email_for(role_code: str) -> str:
    return f"{role_code}@{DOMAIN}"


@transaction.atomic
def run(command: Any) -> None:
    if not settings.SEED_PASSWORD:
        raise CommandError("Set SEED_PASSWORD (see .env.example) before seeding users.")
    site = facility_seed.facility()
    today = timezone.localdate()
    created = 0
    for role in Role.objects.filter(active=True, service_account=False).order_by("code"):
        user, new = User.objects.get_or_create(
            email=email_for(role.code),
            defaults={"first_name": "Seed", "last_name": role.name, "is_approved": True},
        )
        if new:
            user.set_password(settings.SEED_PASSWORD)
            user.save()
            created += 1
        if not RoleAssignment.objects.filter(user=user, role=role, facility=site).exists():
            RoleAssignment.objects.create(
                user=user,
                role=role,
                facility=site,
                valid_from=timezone.now() - timedelta(minutes=1),
                status=RoleAssignment.Status.ACTIVE,
                reason="Synthetic seed data",
            )
        for regulator in role.licence_regulators[:1]:
            ProfessionalLicence.objects.get_or_create(
                user=user,
                regulator=regulator,
                defaults={
                    "registration_number": f"TEST-{role.code.upper()}",
                    "valid_to": today.replace(year=today.year + 2),
                },
            )
    command.stdout.write(
        f"  staff: one user per role at {site.name} ({created} new), e-mail <role>@{DOMAIN}"
    )
