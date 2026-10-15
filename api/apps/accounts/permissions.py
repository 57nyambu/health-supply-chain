from rest_framework import permissions


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in ["ADMIN", "BRANCH_MANAGER"] or request.user.is_superuser
        )


class IsProfileOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanManageWorkers(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("accounts.manage_workers")


class CanApproveWorkers(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("accounts.approve_workers")


# --- Permission catalogue (DESIGN §7.5) ----------------------------------------------------------
from apps.access.catalogue import PermissionDef as P  # noqa: E402
from apps.access.catalogue import Sensitivity as S  # noqa: E402

PERMISSIONS = [
    P("admin.user.read", "View staff user accounts", S.ADMIN),
    P("admin.user.create", "Create staff user accounts", S.ADMIN),
    P("admin.user.update", "Edit staff user accounts", S.ADMIN),
    P("admin.user.deactivate", "Deactivate staff accounts (revokes sessions)", S.ADMIN),
    P(
        "admin.user.reset_credentials",
        "Reset a user's password, PIN or MFA enrolment",
        S.ADMIN,
        privileged=True,
    ),
    P("admin.user.unlock", "Unlock a locked account", S.ADMIN),
]
