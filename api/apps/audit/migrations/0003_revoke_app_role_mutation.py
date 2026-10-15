"""Production: the API's database role may not UPDATE, DELETE or TRUNCATE audit tables.

Runs only when DJANGO_ENV=prod and DB_APP_ROLE names the role the API connects as
(migrations run as the table owner). Elsewhere it is a no-op, so dev and CI keep
the default grants. Irreversible by design: re-granting needs a deliberate DBA action.
"""

from django.conf import settings
from django.db import migrations

TABLES = ("audit_auditevent", "audit_auditanchor")


def revoke_statements(role: str) -> list[str]:
    quoted = '"' + role.replace('"', '""') + '"'
    return [f"REVOKE UPDATE, DELETE, TRUNCATE ON {table} FROM {quoted}" for table in TABLES]


def revoke(apps, schema_editor):
    if settings.DJANGO_ENV != "prod" or not settings.DB_APP_ROLE:
        return
    for statement in revoke_statements(settings.DB_APP_ROLE):
        schema_editor.execute(statement)


class Migration(migrations.Migration):
    dependencies = [("audit", "0002_append_only_triggers")]

    operations = [migrations.RunPython(revoke, migrations.RunPython.noop)]
