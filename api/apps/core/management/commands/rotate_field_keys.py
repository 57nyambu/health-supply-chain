"""Re-encrypt every encrypted field with the newest FIELD_ENCRYPTION_KEYS key (DESIGN §8.2).

Runs in primary-key batches. Each row is updated only if its stored token is still the
one that was read (compare-and-swap), so concurrent writes are never overwritten. Rows
already on the newest key are skipped, which makes an interrupted run resumable: just
run it again. Keep the old key listed until the command reports nothing left to rotate.
"""

from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandParser
from django.db import connection, transaction

from apps.core import crypto
from apps.core.fields import EncryptedBinaryField, EncryptedTextField


def encrypted_columns() -> list[tuple[Any, Any]]:
    found = []
    for model in apps.get_models():
        for field in model._meta.concrete_fields:
            if isinstance(field, EncryptedTextField | EncryptedBinaryField):
                found.append((model, field))
    return found


def rotate_column(model: Any, field: Any, batch_size: int) -> int:
    table = connection.ops.quote_name(model._meta.db_table)
    column = connection.ops.quote_name(field.column)
    pk = connection.ops.quote_name(model._meta.pk.column)
    rotated = 0
    last = None
    while True:
        with connection.cursor() as cursor:
            if last is None:
                cursor.execute(
                    f"SELECT {pk}, {column} FROM {table} WHERE {column} IS NOT NULL AND {column} <> '' "  # noqa: S608
                    f"ORDER BY {pk} LIMIT %s",
                    [batch_size],
                )
            else:
                cursor.execute(
                    f"SELECT {pk}, {column} FROM {table} WHERE {pk} > %s AND {column} IS NOT NULL "  # noqa: S608
                    f"AND {column} <> '' ORDER BY {pk} LIMIT %s",
                    [last, batch_size],
                )
            rows = cursor.fetchall()
        if not rows:
            return rotated
        with transaction.atomic(), connection.cursor() as cursor:
            for row_pk, token in rows:
                if crypto.needs_rotation(token):
                    fresh = crypto.encrypt(crypto.decrypt(token))
                    cursor.execute(
                        f"UPDATE {table} SET {column} = %s WHERE {pk} = %s AND {column} = %s",  # noqa: S608
                        [fresh, row_pk, token],
                    )
                    rotated += cursor.rowcount
        last = rows[-1][0]


class Command(BaseCommand):
    help = "Re-encrypt encrypted fields with the newest key, in resumable batches."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--batch-size", type=int, default=500)

    def handle(self, *args: Any, **options: Any) -> None:
        crypto.reset_key_cache()
        total = 0
        for model, field in encrypted_columns():
            count = rotate_column(model, field, options["batch_size"])
            total += count
            self.stdout.write(f"{model._meta.label}.{field.name}: {count} re-encrypted")
        self.stdout.write(self.style.SUCCESS(f"rotate_field_keys: {total} value(s) re-encrypted"))
