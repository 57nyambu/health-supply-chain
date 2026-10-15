from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("access.role.read", "View roles and their permissions", S.ADMIN),
    P("access.role.manage", "Clone and adjust facility roles", S.ADMIN, privileged=True),
    P("access.assignment.read", "View role assignments", S.ADMIN),
    P("access.assignment.manage", "Grant and revoke non-privileged role assignments", S.ADMIN),
    P(
        "access.assignment.grant_privileged",
        "Request privileged role grants (second approver required)",
        S.ADMIN,
        privileged=True,
    ),
    P("access.approval.read", "View approval requests awaiting one's decision", S.ADMIN),
    P("access.licence.read", "View professional licences", S.ADMIN),
    P("access.licence.manage", "Record and verify professional licences", S.ADMIN),
    P(
        "access.breakglass.request",
        "Request emergency (break-glass) chart access",
        S.PHI,
        requires_licence=True,
    ),
    P("access.breakglass.review", "Review break-glass grants", S.SENSITIVE),
    P("access.review.read", "View periodic access reviews", S.ADMIN),
]
