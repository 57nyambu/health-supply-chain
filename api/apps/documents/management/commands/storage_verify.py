from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.documents import migration, storage


class Command(BaseCommand):
    help = (
        "Check stored objects: present, ciphertext checksum, decryption and plaintext checksum. "
        "Exits non-zero when any object fails."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--backend", choices=storage.BACKENDS)
        parser.add_argument("--facility", type=int)
        parser.add_argument("--sample", type=int, help="check N random objects instead of all")

    def handle(self, *args: Any, **options: Any) -> None:
        report = migration.verify(
            backend=options["backend"], sample=options["sample"], facility=options["facility"]
        )
        for document_id, reason in report.failed:
            self.stderr.write(f"failed {document_id}: {reason}")
        message = f"storage_verify: {report.verified} of {report.selected} objects intact"
        if not report.ok:
            raise CommandError(f"{message}; {len(report.failed)} failed")
        self.stdout.write(self.style.SUCCESS(message))
