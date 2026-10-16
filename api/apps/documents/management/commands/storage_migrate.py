from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.documents import migration, storage
from apps.documents.models import Document


class Command(BaseCommand):
    help = (
        "Move document objects between storage backends (docs/integrations/STORAGE.md §6). "
        "Copies ciphertext, verifies its checksum, then flips each row; safe to re-run after an "
        "interruption. --purge-source is a separate, later run that deletes source copies of "
        "objects already moved, after re-verifying the destination."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--from", dest="source", required=True, choices=storage.BACKENDS)
        parser.add_argument("--to", dest="destination", required=True, choices=storage.BACKENDS)
        parser.add_argument("--category", choices=Document.Category.values)
        parser.add_argument("--facility", type=int)
        parser.add_argument("--batch", type=int, default=500)
        parser.add_argument("--dry-run", action="store_true", help="report what would happen")
        parser.add_argument("--verify", action="store_true", help="read each copy back")
        parser.add_argument("--purge-source", action="store_true", help="delete migrated sources")

    def handle(self, *args: Any, **options: Any) -> None:
        common = {
            "category": options["category"],
            "facility": options["facility"],
            "batch": options["batch"],
            "dry_run": options["dry_run"],
        }
        try:
            if options["purge_source"]:
                report = migration.purge_source(options["source"], options["destination"], **common)
            else:
                report = migration.migrate(
                    options["source"], options["destination"], verify=options["verify"], **common
                )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        mode = "dry run: " if options["dry_run"] else ""
        counts = ", ".join(f"{name} {value}" for name, value in report.summary().items())
        for document_id, reason in report.failed:
            self.stderr.write(f"failed {document_id}: {reason}")
        if not report.ok:
            raise CommandError(f"storage_migrate: {mode}{counts}")
        self.stdout.write(self.style.SUCCESS(f"storage_migrate: {mode}{counts}"))
