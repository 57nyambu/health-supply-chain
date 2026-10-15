from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("facilities.facility.read", "View facility registry details"),
    P(
        "facilities.facility.manage",
        "Edit facility identifiers and settings",
        S.ADMIN,
        privileged=True,
    ),
    P("facilities.location.read", "View departments, service points, wards and beds"),
    P(
        "facilities.location.manage",
        "Create and edit departments, service points, wards and beds",
        S.ADMIN,
    ),
    P("facilities.bed.update_status", "Change bed status (available, cleaning, out of service)"),
]
