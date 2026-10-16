"""Stored idempotent responses become encrypted at rest (DESIGN §8.2, P1-DATA-01).

Idempotency records only live 24 hours and exist to replay a response to a retry.
Existing records are deleted rather than converted (bytea cannot be cast to the
encrypted text format); the cost is that a client retrying a request from before
the deploy executes it again only if it is not otherwise guarded. Irreversible.
"""

from django.db import migrations

import apps.core.fields


def drop_transient_records(apps, schema_editor):
    apps.get_model("core", "IdempotencyRecord").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0002_idempotency_record")]

    operations = [
        migrations.RunPython(drop_transient_records, migrations.RunPython.noop),
        migrations.RemoveField(model_name="idempotencyrecord", name="response_body"),
        migrations.AddField(
            model_name="idempotencyrecord",
            name="response_body",
            field=apps.core.fields.EncryptedBinaryField(blank=True, default=b""),
        ),
    ]
