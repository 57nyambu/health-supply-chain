"""Permission catalogue for this app (DESIGN §7.5). Legacy role checks were removed in P1-UAC-03."""

from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("admin.user.read", "View staff user accounts", S.ADMIN),
    P("admin.user.create", "Create staff user accounts", S.ADMIN),
    P("admin.user.update", "Edit staff user accounts", S.ADMIN),
    P("admin.user.deactivate", "Deactivate staff accounts (revokes sessions)", S.ADMIN),
    P(
        "admin.user.reset_credentials",
        "Reset a user's password, PIN or MFA enrolment",
        S.ADMIN,
        privileged=True,
    ),
    P("admin.user.unlock", "Unlock a locked account", S.ADMIN),
]
