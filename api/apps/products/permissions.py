from rest_framework import permissions


class IsInventoryManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["WAREHOUSE", "BRANCH_MANAGER", "ADMIN", "PROCUREMENT"]


class CanEditProducts(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["ADMIN", "PROCUREMENT", "BRANCH_MANAGER"]


# --- Permission catalogue (DESIGN §7.5) ----------------------------------------------------------
from apps.access.catalogue import PermissionDef as P  # noqa: E402

PERMISSIONS = [
    P("inventory.product.read", "View the product and medicines catalogue"),
    P("inventory.product.manage", "Create and edit products and categories"),
    P("inventory.stock.read", "View stock levels"),
    P("inventory.stock.adjust", "Adjust stock levels"),
    P("inventory.batch.read", "View stock batches and expiries"),
    P("inventory.batch.manage", "Receive, adjust and expire stock batches"),
]
