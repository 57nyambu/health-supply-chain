"""State changes for access control. Other apps call these, never the models directly."""

import csv
import io
from dataclasses import dataclass

from django.db import transaction

from apps.access.catalogue import all_permissions
from apps.access.models import Permission, Role
from apps.access.roles import ROLES


@dataclass(frozen=True)
class SyncResult:
    permissions_created: int
    permissions_deactivated: int
    roles_created: int


@transaction.atomic
def sync_access() -> SyncResult:
    """Mirror the code-defined catalogue and system roles into the database (idempotent)."""
    catalogue = all_permissions()
    existing = {p.code: p for p in Permission.objects.all()}
    created = 0
    for code, definition in catalogue.items():
        values = {
            "description": definition.description,
            "sensitivity": definition.sensitivity.value,
            "requires_licence": definition.requires_licence,
            "privileged": definition.privileged,
            "active": True,
        }
        permission = existing.get(code)
        if permission is None:
            Permission.objects.create(code=code, **values)
            created += 1
        elif any(getattr(permission, key) != value for key, value in values.items()):
            Permission.objects.filter(pk=permission.pk).update(**values)
    deactivated = (
        Permission.objects.filter(active=True).exclude(code__in=catalogue).update(active=False)
    )

    by_code = {p.code: p for p in Permission.objects.filter(active=True)}
    roles_created = 0
    for role_def in ROLES:
        role, was_created = Role.objects.update_or_create(
            code=role_def.code,
            defaults={
                "name": role_def.name,
                "description": role_def.description,
                "chart_baseline": role_def.chart_baseline.value,
                "chart_care_team": role_def.chart_care_team.value,
                "privileged": role_def.privileged,
                "mfa_required": role_def.mfa_required,
                "addon": role_def.addon,
                "requires_cosign": role_def.requires_cosign,
                "service_account": role_def.service_account,
                "is_system": True,
                "active": True,
            },
        )
        roles_created += int(was_created)
        role.permissions.set([by_code[code] for code in sorted(role_def.permission_codes())])
    return SyncResult(created, deactivated, roles_created)


def role_matrix_csv() -> str:
    """Permission x role grid (Y = granted) for docs/generated/role-matrix.csv."""
    roles = list(Role.objects.filter(active=True).order_by("code").prefetch_related("permissions"))
    granted = {role.code: {p.code for p in role.permissions.all()} for role in roles}
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["permission", "sensitivity", "requires_licence", "privileged", *[r.code for r in roles]]
    )
    for permission in Permission.objects.filter(active=True).order_by("code"):
        writer.writerow(
            [
                permission.code,
                permission.sensitivity,
                "Y" if permission.requires_licence else "",
                "Y" if permission.privileged else "",
                *["Y" if permission.code in granted[r.code] else "" for r in roles],
            ]
        )
    return buffer.getvalue()
