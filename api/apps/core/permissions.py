"""Permission catalogue for this app (DESIGN §7.5). Legacy role checks were removed in P1-UAC-03."""

from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("admin.config.read", "View system configuration", S.ADMIN),
    P(
        "admin.config.manage",
        "Change system configuration and feature flags",
        S.ADMIN,
        privileged=True,
    ),
    P("admin.api.read_schema", "View the API schema and documentation", S.ADMIN),
]
