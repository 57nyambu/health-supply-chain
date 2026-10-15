from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.access.services import role_matrix_csv, sync_access


class Command(BaseCommand):
    help = "Write the permission x role matrix (docs/generated/role-matrix.csv)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--output", help="file to write; prints to stdout when omitted")

    def handle(self, *args: Any, **options: Any) -> None:
        sync_access()
        content = role_matrix_csv()
        if options["output"]:
            path = Path(options["output"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            self.stdout.write(f"wrote {path}")
        else:
            self.stdout.write(content, ending="")
