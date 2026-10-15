from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.audit.verify import verify_chains


class Command(BaseCommand):
    help = "Verify the audit hash chains and anchors; exits non-zero when tampering is found."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--from", dest="date_from", type=date.fromisoformat, help="YYYY-MM-DD")
        parser.add_argument("--to", dest="date_to", type=date.fromisoformat, help="YYYY-MM-DD")
        parser.add_argument("--facility", type=int, help="facility id (0 = system events)")

    def handle(self, *args: Any, **options: Any) -> None:
        checked, problems = verify_chains(
            options["date_from"], options["date_to"], options["facility"]
        )
        for problem in problems:
            self.stderr.write(str(problem))
        if problems:
            raise CommandError(f"audit_verify: {len(problems)} problem(s) in {checked} events")
        self.stdout.write(
            self.style.SUCCESS(f"audit_verify: {checked} events verified, chains intact")
        )
