from rest_framework import permissions

class IsWarehouseManager(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.role in ['WAREHOUSE', 'BRANCH_MANAGER', 'ADMIN'] and
            (obj.manager == request.user or request.user.is_superuser)
        )

class CanApproveTransfers(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('warehouses.approve_transfers')

class CanViewInventory(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in [
            'WAREHOUSE', 
            'BRANCH_MANAGER', 
            'ADMIN', 
            'PROCUREMENT', 
            'REPORTER'
        ]