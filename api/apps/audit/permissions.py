from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("audit.log.read", "View the audit log (viewing is itself audited)", S.SENSITIVE),
]
