"""Import an SHA benefits-and-tariffs file as a new version (DESIGN §9; P3-SHA-01).

    manage.py import_sha_tariffs <file.csv> --tariff-version 2026-10 [--synthetic] [--no-activate]

The file uses the documented CSV layout (``apps.insurance.tariffs.COLUMNS``); the whole
file is validated before anything is written. Re-importing the same file is a no-op.
(DESIGN §9 writes ``--version``; Django reserves that flag for its own version.)
"""

from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.insurance import tariffs


class Command(BaseCommand):
    help = "Import an SHA benefits and tariffs CSV as a new tariff version."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("file")
        parser.add_argument(
            "--tariff-version", required=True, dest="label", help="Version label, e.g. 2026-10"
        )
        parser.add_argument(
            "--synthetic", action="store_true", help="Mark as synthetic (not SHA's)"
        )
        parser.add_argument(
            "--no-activate", action="store_true", help="Import without making it active"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        path = Path(options["file"])
        if not path.is_file():
            raise CommandError(f"No such file: {path}")
        try:
            result = tariffs.import_file(
                path.read_bytes(),
                label=options["label"],
                synthetic=options["synthetic"],
                activate=not options["no_activate"],
            )
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        state = "imported" if result.created else "already imported"
        self.stdout.write(
            f"Tariff version {result.version.label}: {state}, {result.rows} interventions."
        )
