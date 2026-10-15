"""Give every existing branch its Facility (ADR-018).

Registry identifiers (MFL code, FID, KEPH level, SHA contract…) are not known
here and stay empty for the facility administrator to complete. Idempotent;
reversing deletes only facilities that still have no MFL code and no layout.
"""

from django.db import migrations


def create_facilities(apps, schema_editor):
    Branch = apps.get_model("warehouses", "Branch")
    Facility = apps.get_model("facilities", "Facility")
    for branch in Branch.objects.all().iterator():
        Facility.objects.get_or_create(
            branch=branch, defaults={"name": branch.name, "kra_pin": branch.kra_pin or ""}
        )


def remove_untouched(apps, schema_editor):
    Facility = apps.get_model("facilities", "Facility")
    Facility.objects.filter(
        mfl_code__isnull=True, departments__isnull=True, wards__isnull=True, service_points__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("facilities", "0001_facility_layout"),
        ("warehouses", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_facilities, remove_untouched)]
