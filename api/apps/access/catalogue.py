"""Permission catalogue: code-defined permissions collected from every app (DESIGN §7.5).

Each app declares ``PERMISSIONS: list[PermissionDef]`` in ``apps/<app>/permissions.py``.
Codes are ``<domain>.<resource>.<action>``, lowercase. ``sync_access`` writes them to
the database; views may only reference codes that exist here.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import import_module

from django.apps import apps

CODE_PATTERN = re.compile(r"^[a-z][a-z_]*\.[a-z][a-z_]*\.[a-z][a-z_]*$")


class Sensitivity(StrEnum):
    """How much harm misuse can cause; drives review and logging emphasis."""

    LOW = "low"
    PHI = "phi"
    SENSITIVE = "sensitive"
    FINANCIAL = "financial"
    ADMIN = "admin"


@dataclass(frozen=True)
class PermissionDef:
    code: str
    description: str
    sensitivity: Sensitivity = Sensitivity.LOW
    requires_licence: bool = False
    privileged: bool = False

    def __post_init__(self) -> None:
        if not CODE_PATTERN.match(self.code):
            raise ValueError(f"Permission code {self.code!r} must look like domain.resource.action")

    @property
    def domain(self) -> str:
        return self.code.split(".", 1)[0]


def _module_permissions(module_path: str) -> list[PermissionDef]:
    try:
        module = import_module(module_path)
    except ModuleNotFoundError as exc:
        if exc.name == module_path:
            return []
        raise
    return list(getattr(module, "PERMISSIONS", []))


@cache
def all_permissions() -> dict[str, PermissionDef]:
    """Every PermissionDef from installed apps plus reserved codes of domains not built yet."""
    found: dict[str, PermissionDef] = {}
    sources = [f"{config.name}.permissions" for config in apps.get_app_configs()]
    sources.append("apps.access.reserved")
    for source in sources:
        for definition in _module_permissions(source):
            if definition.code in found:
                raise ValueError(f"Permission {definition.code} is declared twice ({source})")
            found[definition.code] = definition
    return found


def is_known(code: str) -> bool:
    return code in all_permissions()


def expand(pattern: str) -> set[str]:
    """Expand ``domain.*`` / ``domain.resource.*`` patterns used in role definitions."""
    codes = all_permissions()
    if not pattern.endswith("*"):
        if pattern not in codes:
            raise KeyError(f"Unknown permission code {pattern!r}")
        return {pattern}
    prefix = pattern[:-1]
    matched = {code for code in codes if code.startswith(prefix)}
    if not matched:
        raise KeyError(f"Pattern {pattern!r} matches no permission")
    return matched
