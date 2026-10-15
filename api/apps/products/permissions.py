"""Permission catalogue for this app (DESIGN §7.5). Legacy role checks were removed in P1-UAC-03."""

from apps.access.catalogue import PermissionDef as P

PERMISSIONS = [
    P("inventory.product.read", "View the product and medicines catalogue"),
    P("inventory.product.manage", "Create and edit products and categories"),
    P("inventory.stock.read", "View stock levels"),
    P("inventory.stock.adjust", "Adjust stock levels"),
    P("inventory.batch.read", "View stock batches and expiries"),
    P("inventory.batch.manage", "Receive, adjust and expire stock batches"),
]
