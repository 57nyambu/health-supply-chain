"""Fuzzy name search: pg_trgm and a GIN trigram index on the normalised name (DESIGN §16).

pg_trgm is a trusted extension (PostgreSQL 13+), so the database owner can create it.
"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("patients", "0001_patient_registry")]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name="patient",
            index=GinIndex(fields=["search_name"], name="patients_name_trgm", opclasses=["gin_trgm_ops"]),
        ),
    ]
