"""Load synthetic development data (IMPLEMENTATION §8). Never real people; refuses in production."""

from importlib import import_module

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Ordered seed steps; each module exposes run(command). Steps are idempotent.
SEED_STEPS = [
    "apps.facility_ops.seed",
    "apps.facilities.seed",
    "apps.facility_ops.synthetic",
    "apps.accounts.seed",
    "apps.patients.seed",
]


class Command(BaseCommand):
    help = "Load synthetic data for development, demos and end-to-end tests."

    def handle(self, *args, **options):
        if settings.DJANGO_ENV == "prod":
            raise CommandError("seed refuses to run with DJANGO_ENV=prod.")
        for dotted in SEED_STEPS:
            self.stdout.write(f"seed: {dotted}")
            import_module(dotted).run(self)
        self.stdout.write(self.style.SUCCESS("seed: done"))
