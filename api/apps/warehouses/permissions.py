"""Permission catalogue for this app (DESIGN §7.5). Legacy role checks were removed in P1-UAC-03."""

from apps.access.catalogue import PermissionDef as P
from apps.access.catalogue import Sensitivity as S

PERMISSIONS = [
    P("inventory.store.read", "View stores (warehouses) and bin locations"),
    P("inventory.store.manage", "Create and edit stores and bin locations"),
    P("inventory.branch.manage", "Create and edit branches (organisation units)", S.ADMIN),
    P("inventory.transfer.read", "View stock transfers"),
    P("inventory.transfer.create", "Request stock transfers"),
    P("inventory.transfer.approve", "Approve stock transfers"),
    P("inventory.transfer.receive", "Receive stock transfers at the destination store"),
]
