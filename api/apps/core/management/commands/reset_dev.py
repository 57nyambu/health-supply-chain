"""Wipe the development database and local object store. Development only."""

import shutil

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

WIPED_DIRS = ("objects", "audit-anchors")


class Command(BaseCommand):
    help = "Flush the dev database and delete data/objects and data/audit-anchors (DJANGO_ENV=dev only)."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="confirm the wipe")

    def handle(self, *args, **options):
        if settings.DJANGO_ENV != "dev" or not settings.DEBUG:
            raise CommandError("reset_dev runs only with DJANGO_ENV=dev and DEBUG on.")
        if not options["yes"]:
            raise CommandError("Refusing to wipe without --yes.")
        data_dir = settings.DATA_DIR.resolve()
        if settings.REPO_ROOT.resolve() not in data_dir.parents:
            raise CommandError(f"DATA_DIR {data_dir} is outside the repository; wipe it by hand.")
        call_command("flush", interactive=False, verbosity=0)
        for name in WIPED_DIRS:
            target = data_dir / name
            if target.is_dir():
                shutil.rmtree(target)
        self.stdout.write(
            self.style.SUCCESS("reset_dev: database flushed and data/ objects removed")
        )
