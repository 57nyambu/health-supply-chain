"""Revoke every legacy SimpleJWT refresh token (ADR-005, P1-UAC-04).

The API no longer accepts bearer tokens from browsers; blacklisting the
outstanding refresh tokens records the revocation explicitly. Irreversible on
purpose: revoked tokens must never become valid again.
"""

from django.db import migrations


def blacklist_all(apps, schema_editor):
    OutstandingToken = apps.get_model("token_blacklist", "OutstandingToken")
    BlacklistedToken = apps.get_model("token_blacklist", "BlacklistedToken")
    already = set(BlacklistedToken.objects.values_list("token_id", flat=True))
    BlacklistedToken.objects.bulk_create(
        [
            BlacklistedToken(token_id=token_id)
            for token_id in OutstandingToken.objects.values_list("pk", flat=True)
            if token_id not in already
        ],
        batch_size=1000,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_login_security"),
        ("token_blacklist", "0012_alter_outstandingtoken_user"),
    ]

    operations = [migrations.RunPython(blacklist_all, migrations.RunPython.noop)]
