"""Audit rows are append-only at the database level: UPDATE and DELETE raise.

TRUNCATE is not blocked by the trigger (test isolation and reset_dev rely on it);
production revokes TRUNCATE together with UPDATE and DELETE (0003).
"""

from django.db import migrations

TABLES = ("audit_auditevent", "audit_auditanchor")

FORWARD = """
CREATE OR REPLACE FUNCTION audit_forbid_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit records are append-only (% on %)', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
""" + "".join(
    f"""
CREATE TRIGGER {table}_append_only
    BEFORE UPDATE OR DELETE ON {table}
    FOR EACH ROW EXECUTE FUNCTION audit_forbid_mutation();
"""
    for table in TABLES
)

REVERSE = "".join(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table};\n" for table in TABLES) + (
    "DROP FUNCTION IF EXISTS audit_forbid_mutation();\n"
)


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_audit_chain")]

    operations = [migrations.RunSQL(FORWARD, REVERSE)]
