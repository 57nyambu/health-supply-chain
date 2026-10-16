from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("documents.document.read", "View patient documents through the audited stream", S.PHI),
    P("documents.document.upload", "Upload patient documents", S.PHI),
    P(
        "documents.storage.manage",
        "Run storage migration and verification",
        S.ADMIN,
        privileged=True,
    ),
]
