"""Give existing staff role assignments that match their legacy ``User.role`` (ADR-019).

The assignment is made in the facility of the user's WorkerProfile branch. Users
without a profile get nothing and must be assigned by a facility administrator.
Idempotent; reversing removes only assignments this migration created.
"""

from django.db import migrations
from django.utils import timezone

LEGACY_MAP = {
    "ADMIN": ["system_admin", "facility_admin"],
    "BRANCH_MANAGER": ["store_keeper", "report_viewer"],
    "PROCUREMENT": ["store_keeper"],
    "WAREHOUSE": ["store_keeper"],
    "CASHIER": ["cashier"],
    "REPORTER": ["report_viewer"],
}
REASON = "Migrated from legacy role (ADR-019)"


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    WorkerProfile = apps.get_model("accounts", "WorkerProfile")
    Facility = apps.get_model("facilities", "Facility")
    Role = apps.get_model("access", "Role")
    RoleAssignment = apps.get_model("access", "RoleAssignment")
    # Role rows are completed (name, permissions, flags) by sync_access after migrate.
    roles = {
        code: Role.objects.get_or_create(code=code, defaults={"name": code})[0]
        for codes in LEGACY_MAP.values()
        for code in codes
    }
    facility_by_branch = {f.branch_id: f for f in Facility.objects.all()}
    now = timezone.now()
    for user in User.objects.filter(is_active=True).iterator():
        profile = WorkerProfile.objects.filter(user=user).first()
        facility = facility_by_branch.get(profile.branch_id) if profile else None
        if facility is None:
            continue
        for code in LEGACY_MAP.get(user.role, []):
            RoleAssignment.objects.get_or_create(
                user=user,
                role=roles[code],
                facility=facility,
                reason=REASON,
                defaults={"valid_from": now, "status": "active"},
            )


def backwards(apps, schema_editor):
    RoleAssignment = apps.get_model("access", "RoleAssignment")
    RoleAssignment.objects.filter(reason=REASON).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0002_assignments_and_approvals"),
        ("accounts", "0004_user_sessions"),
        ("facilities", "0002_facility_per_branch"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
