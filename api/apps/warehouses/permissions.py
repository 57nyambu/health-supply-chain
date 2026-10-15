from rest_framework import permissions


class IsWarehouseManager(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.role in ["WAREHOUSE", "BRANCH_MANAGER", "ADMIN"] and (
            obj.manager == request.user or request.user.is_superuser
        )


class CanApproveTransfers(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("warehouses.approve_transfers")


class CanViewInventory(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in [
            "WAREHOUSE",
            "BRANCH_MANAGER",
            "ADMIN",
            "PROCUREMENT",
            "REPORTER",
        ]


# --- Permission catalogue (DESIGN §7.5) ----------------------------------------------------------
from apps.access.catalogue import PermissionDef as P  # noqa: E402
from apps.access.catalogue import Sensitivity as S  # noqa: E402

PERMISSIONS = [
    P("inventory.store.read", "View stores (warehouses) and bin locations"),
    P("inventory.store.manage", "Create and edit stores and bin locations"),
    P("inventory.branch.manage", "Create and edit branches (organisation units)", S.ADMIN),
    P("inventory.transfer.read", "View stock transfers"),
    P("inventory.transfer.create", "Request stock transfers"),
    P("inventory.transfer.approve", "Approve stock transfers"),
    P("inventory.transfer.receive", "Receive stock transfers at the destination store"),
]
