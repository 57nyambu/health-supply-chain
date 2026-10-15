from rest_framework import permissions

class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in ['ADMIN', 'BRANCH_MANAGER'] or
            request.user.is_superuser
        )

class IsProfileOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class CanManageWorkers(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('accounts.manage_workers')

class CanApproveWorkers(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('accounts.approve_workers')