"""Password policy (DESIGN §7.2): argon2id, ≥ 12 characters, no breached passwords.

The bundled breached list is Django's common-password list (20,000 passwords taken
from breach corpora). Deployments may add a larger offline list with
BREACHED_PASSWORDS_FILE (one password per line, optionally gzipped).
"""

import gzip
from functools import cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError


@cache
def _extra_breached() -> frozenset[str]:
    path = settings.BREACHED_PASSWORDS_FILE
    if not path:
        return frozenset()
    file = Path(path)
    opener = gzip.open if file.suffix == ".gz" else open
    with opener(file, "rt", encoding="utf-8", errors="ignore") as handle:
        return frozenset(line.strip().lower() for line in handle if line.strip())


class BreachedPasswordValidator(CommonPasswordValidator):
    """Reject passwords found in the bundled breach list or the optional extra list."""

    def validate(self, password: str, user: Any = None) -> None:
        super().validate(password, user)
        if password.lower().strip() in _extra_breached():
            raise ValidationError(
                "This password appears in a list of breached passwords.",
                code="password_breached",
            )

    def get_help_text(self) -> str:
        return "Your password must not be one that appears in breach lists."
