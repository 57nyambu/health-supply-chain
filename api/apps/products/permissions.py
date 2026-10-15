from rest_framework import permissions

class IsInventoryManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in [
            'WAREHOUSE', 
            'BRANCH_MANAGER', 
            'ADMIN', 
            'PROCUREMENT'
        ]

class CanEditProducts(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in [
            'ADMIN',
            'PROCUREMENT',
            'BRANCH_MANAGER'
        ]